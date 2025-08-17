# backend/craw_data.py

import ccxt
import pandas as pd
import numpy as np # Import numpy để xử lý kiểu dữ liệu

def get_binance_usdt_pairs():
    """
    Lấy danh sách tất cả các cặp giao dịch Spot có đuôi /USDT trên Binance.
    """
    try:
        binance = ccxt.binance()
        binance.load_markets()
        symbols = binance.symbols
        # Lọc các cặp giao dịch Spot, có đuôi /USDT và không phải là các cặp đặc biệt (chứa ':')
        usdt_pairs = [s for s in symbols if s.endswith('/USDT') and ':' not in s]
        print(f"Đã tìm thấy {len(usdt_pairs)} cặp /USDT trên Binance.")
        return sorted(usdt_pairs) # Sắp xếp theo alphabet
    except Exception as e:
        print(f"Lỗi khi lấy danh sách token: {e}")
        return ['ETH/USDT', 'BTC/USDT'] # Trả về danh sách mặc định nếu có lỗi

def fetch_ohlcv(exchange_name, symbol, timeframe, limit):
    """
    Lấy dữ liệu OHLCV từ một sàn giao dịch cụ thể.
    """
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu cho {symbol} - {timeframe}: {e}")
        return None

def calculate_indicators(df_display, df_calc):
    """Tính toán tất cả các chỉ báo và trả về dưới dạng JSON."""
    
    # 1. Tính FVG
    df_calc['is_bullish_fvg'] = df_calc['high'].shift(2) < df_calc['low']
    df_calc['bullish_fvg_top'] = df_calc['low']
    df_calc['bullish_fvg_bottom'] = df_calc['high'].shift(2)
    df_calc['is_bearish_fvg'] = df_calc['low'].shift(2) > df_calc['high']
    df_calc['bearish_fvg_top'] = df_calc['low'].shift(2)
    df_calc['bearish_fvg_bottom'] = df_calc['high']

    # 2. Tính Market Structure
    structure_high, structure_low, breaks, fibo_levels, sh_idx, sl_idx = calculate_market_structure(df_calc)
    if structure_high is None:
        return {}

    # 3. Chuẩn bị dữ liệu để gửi về Frontend
    df_display_reset = df_display.reset_index()
    # SỬA LỖI: Chuyển đổi timestamp sang kiểu int tiêu chuẩn của Python
    df_display_reset['time'] = (df_display_reset['timestamp'].astype(np.int64) // 10**9).astype(int)

    ohlc_data = df_display_reset[['time', 'open', 'high', 'low', 'close']].to_dict(orient='records')

    df_display_reset['color'] = ['rgba(0, 150, 136, 0.8)' if row['close'] >= row['open'] else 'rgba(255, 82, 82, 0.8)' for _, row in df_display_reset.iterrows()]
    volume_data = df_display_reset[['time', 'volume', 'color']].rename(columns={'volume': 'value'}).to_dict(orient='records')
    
    candle_duration_sec = (df_calc.index[1] - df_calc.index[0]).total_seconds() if len(df_calc.index) > 1 else 3600
    last_time_sec = int(df_display_reset['time'].iloc[-1])
    
    fvgs = []
    bullish_fvgs = df_calc[df_calc['is_bullish_fvg']]
    for i, fvg in bullish_fvgs.iterrows():
        start_time = int(i.value // 10**9) + int(candle_duration_sec)
        fvgs.append({'startTime': start_time, 'endTime': last_time_sec, 'bottom': fvg['bullish_fvg_bottom'], 'top': fvg['bullish_fvg_top'], 'color': 'rgba(0, 255, 0, 0.15)'})

    bearish_fvgs = df_calc[df_calc['is_bearish_fvg']]
    for i, fvg in bearish_fvgs.iterrows():
        start_time = int(i.value // 10**9) + int(candle_duration_sec)
        fvgs.append({'startTime': start_time, 'endTime': last_time_sec, 'bottom': fvg['bearish_fvg_bottom'], 'top': fvg['bearish_fvg_top'], 'color': 'rgba(255, 0, 0, 0.15)'})

    # SỬA LỖI: Chuyển đổi timestamp sang kiểu int tiêu chuẩn
    formatted_breaks = [{'price': b['price'], 'startTime': int(b['start_idx'].value // 10**9), 'endTime': int(b['end_idx'].value // 10**9), 'type': b['type'], 'color': 'green' if 'BOS' in b['type'] and b['color'] == 'lime' else 'red' if 'BOS' in b['type'] else 'orange'} for b in breaks]

    if fibo_levels:
        fibo_start_time = int(min(sh_idx.value, sl_idx.value) // 10**9)
        fibo_colors = {0.382: 'rgba(255, 255, 0, 0.5)', 0.5: 'rgba(255, 165, 0, 0.5)', 0.618: 'rgba(255, 105, 180, 0.5)', 0.705: 'rgba(230, 230, 250, 0.8)', 0.786: 'rgba(135, 206, 250, 0.7)'}
        for level in fibo_levels:
            level['startTime'] = fibo_start_time
            level['endTime'] = last_time_sec
            level['color'] = fibo_colors.get(level['ratio'], 'gray')
            
    last_candle = df_display.iloc[-1]
    current_price_line = {
        'price': last_candle['close'],
        'color': 'green' if last_candle['close'] >= last_candle['open'] else 'red'
    }

    return {
        "ohlc": ohlc_data,
        "volume": volume_data,
        "fvgs": fvgs,
        "breaks": formatted_breaks,
        "fibos": fibo_levels,
        "currentPrice": current_price_line
    }


def calculate_market_structure(df):
    if df is None or df.empty or len(df) < 10:
        return None, None, [], [], None, None
    structure_high, structure_low = df.iloc[0]['high'], df.iloc[0]['low']
    sh_idx, sl_idx = df.index[0], df.index[0]
    direction, breaks, fibo_levels = 0, [], []
    for i in range(1, len(df)):
        current_candle = df.iloc[i]
        window = df.iloc[max(0, i-10):i]
        swing_high, swing_low = window['high'].max(), window['low'].min()
        swing_high_idx, swing_low_idx = window['high'].idxmax(), window['low'].idxmin()
        is_high_broken, is_low_broken = current_candle['close'] > structure_high, current_candle['close'] < structure_low
        if direction in [0, 2] and is_high_broken:
            break_type = 'BOS' if direction == 2 else 'CHoCH'
            breaks.append({'price': structure_high, 'start_idx': sh_idx, 'end_idx': current_candle.name, 'type': break_type, 'color': 'lime'})
            direction, structure_high, sh_idx, structure_low, sl_idx = 2, current_candle['high'], current_candle.name, swing_low, swing_low_idx
        elif direction in [0, 1] and is_low_broken:
            break_type = 'BOS' if direction == 1 else 'CHoCH'
            breaks.append({'price': structure_low, 'start_idx': sl_idx, 'end_idx': current_candle.name, 'type': break_type, 'color': 'red'})
            direction, structure_low, sl_idx, structure_high, sh_idx = 1, current_candle['low'], current_candle.name, swing_high, swing_high_idx
        else:
            if direction in [0, 2] and current_candle['high'] > structure_high:
                structure_high, sh_idx = current_candle['high'], current_candle.name
            elif direction in [0, 1] and current_candle['low'] < structure_low:
                structure_low, sl_idx = current_candle['low'], current_candle.name
    structure_range = structure_high - structure_low
    if structure_range > 0:
        fibo_ratios = [0.382, 0.5, 0.618, 0.705, 0.786]
        for ratio in fibo_ratios:
            price = (structure_high - structure_range * ratio) if direction == 2 else (structure_low + structure_range * ratio)
            fibo_levels.append({'ratio': ratio, 'price': price})
    return structure_high, structure_low, breaks, fibo_levels, sh_idx, sl_idx

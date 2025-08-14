# craw_data.py

import ccxt
import pandas as pd


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
        print(f"Lấy dữ liệu thành công cho {symbol} khung {timeframe}")
        return df
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu cho {timeframe}: {e}")
        return None


def calculate_market_structure(df):
    """
    Tính toán các chỉ báo Market Structure (BOS/CHoCH) và Fibonacci.
    Hàm này chứa logic lặp để xác định cấu trúc.
    """
    if df is None or df.empty:
        return None, None, [], [], None, None

    # Khởi tạo các biến trạng thái
    structure_high = df.iloc[0]['high']
    structure_low = df.iloc[0]['low']
    structure_high_idx = df.index[0]
    structure_low_idx = df.index[0]
    direction = 0
    breaks = []

    # Vòng lặp để xác định cấu trúc
    for i in range(1, len(df)):
        current_candle = df.iloc[i]
        window = df.iloc[max(0, i - 10):i]
        swing_high = window['high'].max()
        swing_low = window['low'].min()
        swing_high_idx = window['high'].idxmax()
        swing_low_idx = window['low'].idxmin()

        is_high_broken = current_candle['close'] > structure_high
        is_low_broken = current_candle['close'] < structure_low

        if direction in [0, 2] and is_high_broken:
            break_type = 'BOS' if direction == 2 else 'CHoCH'
            breaks.append({'price': structure_high, 'start_idx': structure_high_idx, 'end_idx': current_candle.name,
                           'type': break_type, 'color': 'lime'})
            direction, structure_high, structure_high_idx, structure_low, structure_low_idx = 2, current_candle[
                'high'], current_candle.name, swing_low, swing_low_idx
        elif direction in [0, 1] and is_low_broken:
            break_type = 'BOS' if direction == 1 else 'CHoCH'
            breaks.append({'price': structure_low, 'start_idx': structure_low_idx, 'end_idx': current_candle.name,
                           'type': break_type, 'color': 'red'})
            direction, structure_low, structure_low_idx, structure_high, structure_high_idx = 1, current_candle[
                'low'], current_candle.name, swing_high, swing_high_idx
        else:
            if direction in [0, 2] and current_candle['high'] > structure_high:
                structure_high, structure_high_idx = current_candle['high'], current_candle.name
            elif direction in [0, 1] and current_candle['low'] < structure_low:
                structure_low, structure_low_idx = current_candle['low'], current_candle.name

    # Tính toán Fibonacci
    fibo_levels = []
    fibo_ratios = [0.382, 0.5, 0.618, 0.705, 0.786]
    structure_range = structure_high - structure_low
    if structure_range > 0:
        for ratio in fibo_ratios:
            price = (structure_high - structure_range * ratio) if direction == 2 else (
                        structure_low + structure_range * ratio)
            fibo_levels.append({'ratio': ratio, 'price': price})

    return structure_high, structure_low, breaks, fibo_levels, structure_high_idx, structure_low_idx
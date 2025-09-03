# src/core/data_fetcher.py
import ccxt
import pandas as pd
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)

def fetch_ohlcv(exchange_name, symbol, timeframe, limit):
    """Lấy dữ liệu OHLCV từ sàn giao dịch được chỉ định."""
    try:
        exchange = getattr(ccxt, exchange_name)({
            'timeout': 30000,
            'enableRateLimit': True,
        })
        logger.info(f"Đang lấy {limit} nến {symbol} {timeframe} từ {exchange_name}...")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            raise ccxt.NetworkError("Không có dữ liệu OHLCV được trả về")
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logger.info(f"Đã lấy thành công {len(df)} nến.")
        return df
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu cho {symbol}: {e}")
        return None

def calculate_rsi(prices, period=14):
    """Tính RSI."""
    if len(prices) < period:
        return pd.Series([np.nan] * len(prices))
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# SỬA LỖI Ở HÀM DƯỚI ĐÂY
def calculate_indicators(df_display, df_calc):
    """
    Tính toán các chỉ báo kỹ thuật.
    Hàm này giờ nhận 2 tham số để tương thích với analysis.py.
    """
    try:
        indicators = {}
        
        # Tính toán dựa trên df_calc (thường là 200 nến cuối)
        if len(df_calc) > 14:
            rsi_values = calculate_rsi(df_calc['close'])
            indicators['rsi'] = float(rsi_values.iloc[-1]) if not pd.isna(rsi_values.iloc[-1]) else 50.0
        
        if len(df_calc['close']) > 1:
            price_change = float(df_calc['close'].iloc[-1] - df_calc['close'].iloc[-2])
            indicators['price_change_pct'] = float((price_change / df_calc['close'].iloc[-2]) * 100) if df_calc['close'].iloc[-2] != 0 else 0.0
        else:
            indicators['price_change_pct'] = 0.0
            
        indicators['current_price'] = float(df_calc['close'].iloc[-1])
        
        # Volume được tính trên toàn bộ dataframe được truyền vào (df_display)
        indicators['volume_24h'] = float(df_display['volume'].sum())

        # Thêm SMA và EMA 20 để formatters.py có thể sử dụng
        indicators['sma_20'] = float(df_calc['close'].rolling(window=20).mean().iloc[-1])
        indicators['ema_20'] = float(df_calc['close'].ewm(span=20).mean().iloc[-1])
        
        return indicators
        
    except Exception as e:
        logger.error(f"Lỗi khi tính toán indicators: {e}")
        return {}
    
def get_top_symbols_by_volume(exchange_name: str, limit: int = 100) -> list[str]:
    logger.info(f"Đang lấy {limit} token có thanh khoản cao nhất từ {exchange_name}...")
    try:
        exchange = getattr(ccxt, exchange_name)()
        all_tickers = exchange.fetch_tickers()
        
        usdt_pairs = {
            symbol: ticker for symbol, ticker in all_tickers.items()
            if symbol.endswith('/USDT') and 
                'USDC' not in symbol and 'BUSD' not in symbol and
                'UP/' not in symbol and 'DOWN/' not in symbol
        }
        
        sorted_pairs = sorted(usdt_pairs.values(), key=lambda t: t.get('quoteVolume', 0), reverse=True)
        
        top_symbols = [ticker['symbol'] for ticker in sorted_pairs[:limit]]
        logger.info(f"Đã lấy được {len(top_symbols)} token hàng đầu.")
        return top_symbols
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách token hàng đầu: {e}")
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

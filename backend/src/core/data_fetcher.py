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
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_indicators(df):
    """Tính toán các chỉ báo kỹ thuật."""
    try:
        indicators = {}
        close_prices = df['close']
        
        # RSI
        rsi_values = calculate_rsi(close_prices)
        indicators['rsi'] = float(rsi_values.iloc[-1]) if not pd.isna(rsi_values.iloc[-1]) else 50.0

        # Price info
        indicators['current_price'] = float(close_prices.iloc[-1])
        if len(close_prices) > 1:
            price_change = float(close_prices.iloc[-1] - close_prices.iloc[-2])
            indicators['price_change_pct'] = float((price_change / close_prices.iloc[-2]) * 100)
        else:
            indicators['price_change_pct'] = 0.0

        # Volume (lấy tổng volume của df)
        indicators['volume_24h'] = float(df['volume'].sum()) # Đây là ước tính, không chính xác
        
        return indicators
    except Exception as e:
        logger.error(f"Lỗi khi tính toán indicators: {e}")
        return { 'rsi': 50.0, 'current_price': 0.0, 'price_change_pct': 0.0, 'volume_24h': 0.0 }
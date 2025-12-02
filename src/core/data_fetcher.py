# src/core/data_fetcher.py
import ccxt
import yfinance as yf
import pandas as pd
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)

def fetch_ohlcv(exchange_name, symbol, timeframe, limit):
    """Fetch OHLCV data from specified exchange."""
    try:
        exchange_class = getattr(ccxt, exchange_name)

        config = {
            'timeout': 30000,
            'enableRateLimit': True,
        }

        if exchange_name == 'okx':
            config['options'] = {'defaultType': 'spot'}

        exchange = exchange_class(config)

        logger.info(f"Fetching {limit} candles of {symbol} {timeframe} from {exchange_name}...")
        exchange.load_markets()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            raise ccxt.NetworkError("No OHLCV data returned")
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logger.info(f"Successfully fetched {len(df)} candles.")
        return df
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None

def map_timeframe_to_yfinance(timeframe: str) -> dict:
    """
    Map our timeframe string to yfinance 'period' and 'interval'.
    yfinance has limitations on interval data.
    """
    tf_map = {
        # interval: period
        "5m": ("7d", "5m"),
        "15m": ("60d", "15m"),
        "30m": ("60d", "30m"),
        "1h": ("730d", "1h"),
        "1d": ("max", "1d"),
        "1w": ("max", "1wk"),
    }
    # Mặc định về 1d nếu không khớp
    return tf_map.get(timeframe, ("max", "1d"))


def fetch_ohlcv_yfinance(symbol: str, timeframe: str, limit: int) -> pd.DataFrame | None:
    """Fetch OHLCV data from Yahoo Finance (FOR STOCKS, FOREX, COMMODITIES)."""
    logger.info(f"Fetching {limit} candles of {symbol} {timeframe} from Yahoo Finance...")
    try:
        period, interval = map_timeframe_to_yfinance(timeframe)

        if timeframe == "4h":
            logger.warning(f"Yahoo Finance không hỗ trợ timeframe 4h. Đang lấy 1d cho {symbol}.")

        df = yf.download(tickers=symbol, period=period, interval=interval, auto_adjust=True)

        if df.empty:
            logger.error(f"Không có dữ liệu yfinance trả về cho {symbol}.")
            return None

        df = df.reset_index()
        df_flat = pd.DataFrame()

        if 'Datetime' in df.columns:
            df_flat['timestamp'] = pd.to_datetime(df['Datetime'])
        elif 'Date' in df.columns:
            df_flat['timestamp'] = pd.to_datetime(df['Date'])
        else:
            logger.error(f"Không tìm thấy cột 'Date' hay 'Datetime' cho {symbol}.")
            return None

        col_map = {
            'open': ['Open', ('Price', 'Open')],
            'high': ['High', ('Price', 'High')],
            'low': ['Low', ('Price', 'Low')],
            'close': ['Close', ('Price', 'Close')],
            'volume': ['Volume', ('Price', 'Volume')]
        }

        for col_name, potential_keys in col_map.items():
            found = False
            for key in potential_keys:
                if key in df.columns:
                    df_flat[col_name] = df[key]
                    found = True
                    break
            if not found:
                df_flat[col_name] = np.nan


        if df_flat['timestamp'].dt.tz is not None:
            df_flat['timestamp'] = df_flat['timestamp'].dt.tz_localize(None)

        df_final = df_flat.tail(limit).copy()

        cols_to_numeric = ['open', 'high', 'low', 'close', 'volume']
        df_final[cols_to_numeric] = df_final[cols_to_numeric].apply(pd.to_numeric, errors='coerce')

        if df_final.empty or df_final['close'].isnull().all():
            logger.error(f"Dữ liệu cho {symbol} rỗng hoặc toàn NaN sau khi xử lý.")
            return None

        logger.info(f"Successfully fetched {len(df_final)} candles from yfinance.")
        return df_final

    except Exception as e:
        logger.error(f"Error fetching data from yfinance for {symbol}: {e}",
                     exc_info=True)  # Thêm exc_info=True để debug
        return None

def calculate_rsi(prices, period=14):
    """Calculate RSI."""
    if len(prices) < period:
        return pd.Series([np.nan] * len(prices))
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_indicators(df_display, df_calc):
    """
    Calculate technical indicators.
    """
    try:
        indicators = {}
        if len(df_calc) > 14:
            rsi_values = calculate_rsi(df_calc['close'])
            indicators['rsi'] = float(rsi_values.iloc[-1]) if not pd.isna(rsi_values.iloc[-1]) else 50.0
        if len(df_calc['close']) > 1:
            price_change = float(df_calc['close'].iloc[-1] - df_calc['close'].iloc[-2])
            indicators['price_change_pct'] = float((price_change / df_calc['close'].iloc[-2]) * 100) if df_calc['close'].iloc[-2] != 0 else 0.0
        else:
            indicators['price_change_pct'] = 0.0
        indicators['current_price'] = float(df_calc['close'].iloc[-1])
        indicators['volume_24h'] = float(df_display['volume'].sum())
        indicators['sma_20'] = float(df_calc['close'].rolling(window=20).mean().iloc[-1])
        indicators['ema_20'] = float(df_calc['close'].ewm(span=20).mean().iloc[-1])
        return indicators
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return {}

def get_top_symbols_by_volume(exchange_name: str, limit: int = 100) -> list[str]:
    """
    Get list of trading pairs with highest 24h volume, filtered by USDT.
    """
    logger.info(f"Fetching top {limit} tokens by liquidity from {exchange_name}...")
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
        logger.info(f"Successfully fetched {len(top_symbols)} top tokens.")
        return top_symbols
        
    except Exception as e:
        logger.error(f"Error fetching top tokens list: {e}")
        # Return fallback list if API fails
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
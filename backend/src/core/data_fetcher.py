# src/core/data_fetcher.py
import ccxt
import pandas as pd
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)

def fetch_ohlcv(exchange_name, symbol, timeframe, limit):
    """Fetch OHLCV data from specified exchange."""
    try:
        exchange = getattr(ccxt, exchange_name)({
            'timeout': 30000,
            'enableRateLimit': True,
        })
        logger.info(f"Fetching {limit} candles of {symbol} {timeframe} from {exchange_name}...")
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
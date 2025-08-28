# src/core/analysis.py
# --- Imports ---
import numpy as np
import pandas as pd
from datetime import datetime
import logging
from functools import reduce
# SỬA LẠI IMPORT ĐỂ PHÙ HỢP CẤU TRÚC
from .data_fetcher import fetch_ohlcv, calculate_indicators

logger = logging.getLogger(__name__)

def analyze_smc_features(df: pd.DataFrame, swing_lookback: int = 20) -> pd.DataFrame:
    """
    Hàm này phân tích và thêm các cột SMC vào DataFrame.
    """
    if len(df) < swing_lookback * 2 + 1:
        cols = ['swing_high', 'swing_low', 'bos_choch_signal', 'BOS', 'CHOCH', 'OB', 
                'Top_OB', 'Bottom_OB', 'FVG', 'Top_FVG', 'Bottom_FVG', 'Swept']
        for col in cols:
            df[col] = 0 if col not in ['Top_OB', 'Bottom_OB', 'Top_FVG', 'Bottom_FVG'] else np.nan
        return df

    # --- 1. Xác định Swing Highs & Swing Lows ---
    df['swing_high'] = df['high'].rolling(window=swing_lookback*2+1, center=True).max() == df['high']
    df['swing_low'] = df['low'].rolling(window=swing_lookback*2+1, center=True).min() == df['low']
    
    # --- 2. Xác định Break of Structure (BOS) và Change of Character (CHoCH) ---
    last_swing_high, last_swing_low, trend, bos_choch = np.nan, np.nan, 0, []
    for i in range(len(df)):
        is_swing_high, is_swing_low = df['swing_high'].iloc[i], df['swing_low'].iloc[i]
        current_high, current_low = df['high'].iloc[i], df['low'].iloc[i]
        signal = 0
        if is_swing_high: last_swing_high = current_high
        if is_swing_low: last_swing_low = current_low
        if trend == 1 and not np.isnan(last_swing_low) and current_low < last_swing_low:
            signal = -2; trend = -1; last_swing_high = np.nan
        elif trend == -1 and not np.isnan(last_swing_high) and current_high > last_swing_high:
            signal = 2; trend = 1; last_swing_low = np.nan
        elif not np.isnan(last_swing_high) and current_high > last_swing_high:
            signal = 1; trend = 1; last_swing_low = np.nan
        elif not np.isnan(last_swing_low) and current_low < last_swing_low:
            signal = -1; trend = -1; last_swing_high = np.nan
        bos_choch.append(signal)
    df['bos_choch_signal'] = bos_choch
    df['BOS'] = df['bos_choch_signal'].apply(lambda x: 1 if x == 1 else (-1 if x == -1 else 0))
    df['CHOCH'] = df['bos_choch_signal'].apply(lambda x: 1 if x == 2 else (-1 if x == -2 else 0))

    # --- 3. Xác định Order Blocks (OB) ---
    df['OB'], df['Top_OB'], df['Bottom_OB'] = 0, np.nan, np.nan
    for i in range(1, len(df)):
        if df['bos_choch_signal'].iloc[i] in [1, 2]:
            for j in range(i - 1, max(0, i - 10), -1):
                if df['close'].iloc[j] < df['open'].iloc[j]:
                    df.loc[df.index[j], ['OB', 'Top_OB', 'Bottom_OB']] = [1, df['high'].iloc[j], df['low'].iloc[j]]
                    break
        elif df['bos_choch_signal'].iloc[i] in [-1, -2]:
            for j in range(i - 1, max(0, i - 10), -1):
                if df['close'].iloc[j] > df['open'].iloc[j]:
                    df.loc[df.index[j], ['OB', 'Top_OB', 'Bottom_OB']] = [-1, df['high'].iloc[j], df['low'].iloc[j]]
                    break
    
    # --- 4. Xác định Fair Value Gaps (FVG) ---
    df['FVG'], df['Top_FVG'], df['Bottom_FVG'] = 0, np.nan, np.nan
    for i in range(2, len(df)):
        if df['low'].iloc[i-2] > df['high'].iloc[i]:
            df.loc[df.index[i-1], ['FVG', 'Top_FVG', 'Bottom_FVG']] = [1, df['low'].iloc[i-2], df['high'].iloc[i]]
        elif df['high'].iloc[i-2] < df['low'].iloc[i]:
            df.loc[df.index[i-1], ['FVG', 'Top_FVG', 'Bottom_FVG']] = [-1, df['high'].iloc[i-2], df['low'].iloc[i]]

    # --- 5. Xác định Liquidity Sweeps ---
    df['Swept'] = 0
    recent_high = df['high'].rolling(5).max().shift(1)
    recent_low = df['low'].rolling(5).min().shift(1)
    df.loc[(df['high'] > recent_high) & (df['close'] < recent_high), 'Swept'] = -1
    df.loc[(df['low'] < recent_low) & (df['close'] > recent_low), 'Swept'] = 1
    return df

class AdvancedSMC:
    def __init__(self, exchange_name='binance'):
        self.exchange_name = exchange_name
        self.informative_timeframes = ['15m', '1h', '4h', '1d']
        
    def get_market_data(self, symbol, timeframe='4h', limit=200):
        try:
            return fetch_ohlcv(self.exchange_name, symbol, timeframe, limit)
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu: {e}")
            return None

    def analyze_smc_structure(self, df):
        if df is None or len(df) < 50:
            return {
                'order_blocks': [], 'liquidity_zones': [], 'fair_value_gaps': [],
                'break_of_structure': [], 'trading_signals': {
                    'entry_long': [], 'entry_short': [], 'exit_long': [], 'exit_short': []
                }
            }
        df_analyzed = analyze_smc_features(df.copy())
        df_analyzed = self.populate_entry_trend_simple(df_analyzed)
        df_analyzed = self.populate_exit_trend(df_analyzed)
        return {
            'order_blocks': self.extract_order_blocks(df_analyzed),
            'liquidity_zones': self.extract_liquidity_zones(df_analyzed),
            'fair_value_gaps': self.extract_fair_value_gaps(df_analyzed),
            'break_of_structure': self.extract_break_of_structure(df_analyzed),
            'trading_signals': self.extract_recent_signals(df_analyzed)
        }
    
    def populate_entry_trend_simple(self, dataframe):
        try:
            dataframe['enter_long'] = 0
            dataframe['enter_short'] = 0
            dataframe['enter_tag'] = ''
            long_conditions = (
                (dataframe['BOS'] == 1) & (dataframe['Swept'] == 1) & 
                (((dataframe['low'] <= dataframe['Top_OB']) & (dataframe['high'] >= dataframe['Bottom_OB']) & (dataframe['OB'] == 1)) |
                 ((dataframe['low'] <= dataframe['Top_FVG']) & (dataframe['high'] >= dataframe['Bottom_FVG']) & (dataframe['FVG'] == 1)))
            )
            short_conditions = (
                (dataframe['BOS'] == -1) & (dataframe['Swept'] == -1) &
                (((dataframe['low'] <= dataframe['Top_OB']) & (dataframe['high'] >= dataframe['Bottom_OB']) & (dataframe['OB'] == -1)) |
                 ((dataframe['low'] <= dataframe['Top_FVG']) & (dataframe['high'] >= dataframe['Bottom_FVG']) & (dataframe['FVG'] == -1)))
            )
            dataframe.loc[long_conditions, 'enter_long'] = 1
            dataframe.loc[long_conditions, 'enter_tag'] = 'long_smc_simple'
            dataframe.loc[short_conditions, 'enter_short'] = 1
            dataframe.loc[short_conditions, 'enter_tag'] = 'short_smc_simple'
            return dataframe
        except Exception as e:
            logger.error(f"Error in populate_entry_trend_simple: {e}")
            return dataframe

    def populate_exit_trend(self, dataframe):
        try:
            dataframe['exit_long'] = 0
            dataframe['exit_short'] = 0
            dataframe.loc[(dataframe['CHOCH'] == -1), 'exit_long'] = 1
            dataframe.loc[(dataframe['CHOCH'] == 1), 'exit_short'] = 1
            return dataframe
        except Exception as e:
            logger.error(f"Error in populate_exit_trend: {e}")
            return dataframe

    def get_trading_signals(self, symbol, timeframe='1d'):
        try:
            df = self.get_market_data(symbol, timeframe)
            if df is None: return None
            smc_analysis = self.analyze_smc_structure(df)
            indicators = calculate_indicators(df, df.tail(200).copy())
            return {
                'symbol': symbol, 'timeframe': timeframe,
                'timestamp': int(df.iloc[-1]['timestamp'].timestamp()),
                'current_price': float(df.iloc[-1]['close']),
                'smc_analysis': smc_analysis,
                'trading_signals': smc_analysis['trading_signals'],
                'indicators': indicators
            }
        except Exception as e:
            logger.error(f"Lỗi khi phân tích SMC: {e}")
            return None

    def extract_recent_signals(self, df):
        signals = {'entry_long': [], 'entry_short': [], 'exit_long': [], 'exit_short': []}
        recent_df = df.tail(50)
        for _, row in recent_df.iterrows():
            timestamp = int(row['timestamp'].timestamp())
            if row.get('enter_long', 0) == 1:
                signals['entry_long'].append({'time': timestamp, 'price': row['close'], 'tag': row.get('enter_tag', 'long_smc')})
            if row.get('enter_short', 0) == 1:
                signals['entry_short'].append({'time': timestamp, 'price': row['close'], 'tag': row.get('enter_tag', 'short_smc')})
            if row.get('exit_long', 0) == 1:
                signals['exit_long'].append({'time': timestamp, 'price': row['close']})
            if row.get('exit_short', 0) == 1:
                signals['exit_short'].append({'time': timestamp, 'price': row['close']})
        return signals

    def extract_order_blocks(self, df):
        order_blocks = []
        for _, row in df.iterrows():
            if row.get('OB', 0) != 0:
                order_blocks.append({
                    'type': 'bullish_ob' if row['OB'] == 1 else 'bearish_ob',
                    'high': row.get('Top_OB'), 'low': row.get('Bottom_OB'),
                    'time': int(row['timestamp'].timestamp()), 'strength': 'high'
                })
        return order_blocks[-10:]

    def extract_liquidity_zones(self, df):
        liquidity_zones = []
        swing_highs = df[df.get('swing_high', False) == True]
        swing_lows = df[df.get('swing_low', False) == True]
        for _, row in swing_highs.iterrows():
            liquidity_zones.append({'type': 'buy_side_liquidity', 'price': row['high'], 'time': int(row['timestamp'].timestamp()), 'strength': 'high'})
        for _, row in swing_lows.iterrows():
            liquidity_zones.append({'type': 'sell_side_liquidity', 'price': row['low'], 'time': int(row['timestamp'].timestamp()), 'strength': 'high'})
        return liquidity_zones[-10:]

    def extract_fair_value_gaps(self, df):
        fvgs = []
        for _, row in df.iterrows():
            if row.get('FVG', 0) != 0:
                fvgs.append({
                    'type': 'bullish_fvg' if row['FVG'] == 1 else 'bearish_fvg',
                    'top': row.get('Top_FVG'), 'bottom': row.get('Bottom_FVG'),
                    'time': int(row['timestamp'].timestamp()), 'filled': False
                })
        return fvgs[-20:]

    def extract_break_of_structure(self, df):
        bos_signals = []
        for _, row in df.iterrows():
            if row.get('BOS', 0) != 0:
                bos_signals.append({
                    'type': 'bullish_bos' if row['BOS'] == 1 else 'bearish_bos',
                    'price': row['close'], 'time': int(row['timestamp'].timestamp()), 'strength': 'confirmed'
                })
        return bos_signals[-10:]
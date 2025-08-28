# src/core/analysis.py
import numpy as np
import pandas as pd
import logging
from functools import reduce
from .data_fetcher import fetch_ohlcv, calculate_indicators

logger = logging.getLogger(__name__)

def analyze_smc_features(df: pd.DataFrame, swing_lookback: int = 20) -> pd.DataFrame:
    """Phân tích và thêm các cột SMC vào DataFrame."""
    if len(df) < swing_lookback * 2 + 1:
        # Nếu không đủ dữ liệu, trả về df với các cột trống để tránh lỗi
        cols = ['swing_high', 'swing_low', 'bos_choch_signal', 'BOS', 'CHOCH', 'OB', 
                'Top_OB', 'Bottom_OB', 'FVG', 'Top_FVG', 'Bottom_FVG', 'Swept']
        for col in cols:
            df[col] = 0 if col not in ['Top_OB', 'Bottom_OB', 'Top_FVG', 'Bottom_FVG'] else np.nan
        return df

    # --- 1. Xác định Swing Highs & Swing Lows ---
    df['swing_high'] = df['high'].rolling(window=swing_lookback*2+1, center=True, min_periods=1).max() == df['high']
    df['swing_low'] = df['low'].rolling(window=swing_lookback*2+1, center=True, min_periods=1).min() == df['low']
    
    # --- 2. Xác định Break of Structure (BOS) và Change of Character (CHoCH) ---
    last_swing_high = np.nan
    last_swing_low = np.nan
    trend = 0
    bos_choch = []
    
    for i in range(len(df)):
        is_swing_high = df['swing_high'].iloc[i]
        is_swing_low = df['swing_low'].iloc[i]
        current_high = df['high'].iloc[i]
        current_low = df['low'].iloc[i]
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
    df['OB'] = 0
    df['Top_OB'] = np.nan
    df['Bottom_OB'] = np.nan

    for i in range(1, len(df)):
        if df['bos_choch_signal'].iloc[i] in [1, 2]:
            for j in range(i - 1, max(0, i - 10), -1):
                if df['close'].iloc[j] < df['open'].iloc[j]:
                    df.loc[df.index[j], 'OB'] = 1
                    df.loc[df.index[j], 'Top_OB'] = df['high'].iloc[j]
                    df.loc[df.index[j], 'Bottom_OB'] = df['low'].iloc[j]
                    break
        elif df['bos_choch_signal'].iloc[i] in [-1, -2]:
            for j in range(i - 1, max(0, i - 10), -1):
                if df['close'].iloc[j] > df['open'].iloc[j]:
                    df.loc[df.index[j], 'OB'] = -1
                    df.loc[df.index[j], 'Top_OB'] = df['high'].iloc[j]
                    df.loc[df.index[j], 'Bottom_OB'] = df['low'].iloc[j]
                    break
    
    # --- 4. Xác định Fair Value Gaps (FVG) ---
    df['FVG'] = 0
    df['Top_FVG'] = np.nan
    df['Bottom_FVG'] = np.nan

    for i in range(2, len(df)):
        if df['low'].iloc[i-2] > df['high'].iloc[i]:
            df.loc[df.index[i-1], 'FVG'] = 1
            df.loc[df.index[i-1], 'Top_FVG'] = df['low'].iloc[i-2]
            df.loc[df.index[i-1], 'Bottom_FVG'] = df['high'].iloc[i]
        elif df['high'].iloc[i-2] < df['low'].iloc[i]:
            df.loc[df.index[i-1], 'FVG'] = -1
            df.loc[df.index[i-1], 'Top_FVG'] = df['high'].iloc[i-2]
            df.loc[df.index[i-1], 'Bottom_FVG'] = df['low'].iloc[i]

    # --- 5. Xác định Liquidity Sweeps ---
    df['Swept'] = 0
    recent_high = df['high'].rolling(5).max().shift(1)
    recent_low = df['low'].rolling(5).min().shift(1)
    df.loc[(df['high'] > recent_high) & (df['close'] < recent_high), 'Swept'] = -1
    df.loc[(df['low'] < recent_low) & (df['close'] > recent_low), 'Swept'] = 1

    return df


class AdvancedSMC:
    """Phân tích Smart Money Concepts (SMC) và trả về dữ liệu thô."""
    
    def __init__(self, exchange_name='binance'):
        self.exchange_name = exchange_name
        
    def get_market_data(self, symbol, timeframe, limit=200):
        """Lấy và trả về dữ liệu thị trường."""
        return fetch_ohlcv(self.exchange_name, symbol, timeframe, limit)
    
    def get_analysis(self, symbol: str, timeframe: str):
        """Method chính - Lấy dữ liệu phân tích đầy đủ."""
        try:
            df = self.get_market_data(symbol, timeframe)
            if df is None or df.empty:
                return {'error': True, 'message': 'Không thể lấy dữ liệu thị trường.'}
            
            df_analyzed = analyze_smc_features(df.copy())
            indicators = calculate_indicators(df_analyzed)
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_price': indicators.get('current_price'),
                'indicators': indicators,
                'smc_features': self._extract_smc_features(df_analyzed),
                'error': False
            }
        except Exception as e:
            logger.error(f"Lỗi khi phân tích SMC cho {symbol}: {e}", exc_info=True)
            return {'error': True, 'message': f"Lỗi nội bộ trong quá trình phân tích: {e}"}

    def _extract_smc_features(self, df: pd.DataFrame) -> dict:
        """Trích xuất các đặc điểm SMC từ dataframe đã phân tích."""
        features = {}
        # Lấy trạng thái gần nhất của các feature quan trọng
        last_row = df.iloc[-1]
        
        # BOS
        bos_series = df[df['BOS'] != 0]['BOS']
        features['break_of_structure'] = {'status': 'Bullish' if bos_series.iloc[-1] == 1 else 'Bearish' if not bos_series.empty else 'N/A'}

        # Order Blocks
        ob_series = df[df['OB'] != 0]['OB']
        features['order_blocks'] = {'status': 'Bullish Zone' if ob_series.iloc[-1] == 1 else 'Bearish Zone' if not ob_series.empty else 'N/A'}
        
        # FVG
        fvg_series = df[df['FVG'] != 0]['FVG']
        features['fair_value_gaps'] = {'status': 'Bullish' if fvg_series.iloc[-1] == 1 else 'Bearish' if not fvg_series.empty else 'N/A'}
        
        # Liquidity
        sweep_series = df[df['Swept'] != 0]['Swept']
        features['liquidity_zones'] = {'status': 'Buy-side Swept' if sweep_series.iloc[-1] == -1 else 'Sell-side Swept' if not sweep_series.empty else 'N/A'}

        return features
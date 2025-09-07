import logging
from src.core.analysis import AdvancedSMC
from src.core.data_fetcher import get_top_symbols_by_volume

logger = logging.getLogger(__name__)

class MarketScannerService:
    def __init__(self):
        self.smc_analyzer = AdvancedSMC()

    def _determine_market_state(self, smc: dict, trading_signals: dict) -> str:
        """
        Determine market state based on core SMC signals.
        Prioritize entry signals first, then general trend.
        """
        # Priority 1: Direct entry signals
        if trading_signals and trading_signals.get('entry_long'):
            return "Long"
        if trading_signals and trading_signals.get('entry_short'):
            return "Short"
            
        # Priority 2: Main trend from Break of Structure
        if smc and smc.get('break_of_structure'):
            latest_bos = smc['break_of_structure'][-1]
            if latest_bos.get('type') == 'bullish_bos':
                return 'Long'
            elif latest_bos.get('type') == 'bearish_bos':
                return 'Short'
        
        return "Neutral"

    def run_scan(self, previous_states: dict, timeframe='1d') -> (list, dict):
        """
        Scan 200 tokens, compare states and return tokens with changes.
        """
        flipped_tokens = []
        new_states = {}

        top_250_symbols = get_top_symbols_by_volume('binance', 250)

        for i, symbol in enumerate(top_250_symbols):
            logger.info(f"[SCAN {i+1}/{len(top_250_symbols)}] Analyzing {symbol}...")
            try:
                # Get most detailed analysis data
                analysis = self.smc_analyzer.get_trading_signals(symbol, timeframe)
                if not analysis:
                    continue

                current_state = self._determine_market_state(
                    analysis.get('smc_analysis', {}),
                    analysis.get('trading_signals', {})
                )
                previous_state = previous_states.get(symbol)
                
                # Save new state
                new_states[symbol] = current_state
                
                # Compare with previous state
                if previous_state and current_state != previous_state:
                    if current_state != 'Neutral' and previous_state != 'Neutral':
                        flipped_tokens.append({
                            'symbol': symbol,
                            'from': previous_state,
                            'to': current_state,
                            'price': analysis.get('current_price', 0)
                        })
                        logger.warning(f"SIGNAL REVERSAL: {symbol} from {previous_state} -> {current_state}")

            except Exception as e:
                logger.error(f"Error scanning token {symbol}: {e}")
                continue
                
        return flipped_tokens, new_states
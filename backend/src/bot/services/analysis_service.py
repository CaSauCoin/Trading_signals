import logging
from src.core.analysis import AdvancedSMC
from datetime import datetime

logger = logging.getLogger(__name__)

class BotAnalysisService:
    def __init__(self):
        self.smc_analyzer = AdvancedSMC()

    def get_analysis_for_symbol(self, symbol: str, timeframe: str) -> dict:
        """
        Get detailed analysis from core and create insights for bot.
        """
        logger.info(f"Starting detailed analysis for '{symbol}' ({timeframe}).")
        
        analysis_data = self.smc_analyzer.get_trading_signals(symbol, timeframe)
        
        if not analysis_data:
            return {'error': True, 'message': f'Cannot analyze {symbol}.'}

        try:
            suggestion = self._get_trading_suggestion(
                analysis_data.get('smc_analysis', {}),
                analysis_data.get('indicators', {}),
                analysis_data.get('trading_signals', {})
            )
            
            analysis_data['analysis'] = {'suggestion': suggestion}
            analysis_data['error'] = False
            return analysis_data

        except Exception as e:
            logger.error(f"Error processing and creating bot insights: {e}", exc_info=True)
            return {'error': True, 'message': 'Error processing data after analysis.'}

    def _get_trading_suggestion(self, smc: dict, indicators: dict, trading_signals: dict) -> str:
        """
        Logic to create detailed trading suggestions, combining multiple factors.
        """
        suggestions = []
        try:
            rsi = indicators.get('rsi', 50)

            # RSI Analysis
            if rsi > 70:
                suggestions.append("⚠️ Consider selling (RSI Overbought)")
            elif rsi < 30:
                suggestions.append("🚀 Consider buying (RSI Oversold)")

            # Structure Analysis (BOS)
            if smc.get('break_of_structure'):
                latest_bos = smc['break_of_structure'][-1]
                if latest_bos.get('type') == 'bullish_bos':
                    suggestions.append("📈 Uptrend confirmed")
                elif latest_bos.get('type') == 'bearish_bos':
                    suggestions.append("📉 Downtrend confirmed")

            # FVG Analysis
            if smc.get('fair_value_gaps'):
                suggestions.append("🎯 Wait for price to return and fill FVG")

            # Direct entry signal analysis
            if trading_signals and trading_signals.get('entry_long'):
                suggestions.append("🟢 BUY signal detected")
            if trading_signals and trading_signals.get('entry_short'):
                suggestions.append("🔴 SELL signal detected")

            if not suggestions:
                return "⏸️ Market is moving sideways. Consider staying out and waiting for clear Break of Structure (BOS) signals."

            return "\n".join([f"• {s}" for s in suggestions])
        except Exception as e:
            logger.error(f"Error in _get_trading_suggestion: {e}")
            return "⚠️ Cannot create suggestion - Insufficient data."
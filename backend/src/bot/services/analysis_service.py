# src/bot/services/analysis_service.py
import logging
from src.core.analysis import AdvancedSMC
from datetime import datetime

logger = logging.getLogger(__name__)

class BotAnalysisService:
    def __init__(self):
        self.smc_analyzer = AdvancedSMC()

    def get_analysis_for_symbol(self, symbol: str, timeframe: str) -> dict:
        """Lấy và xử lý dữ liệu phân tích để bot sử dụng."""
        logger.info(f"Bắt đầu phân tích cho {symbol} trên khung {timeframe}")
        
        raw_data = self.smc_analyzer.get_analysis(symbol, timeframe)
        
        if raw_data.get('error'):
            return raw_data

        try:
            smc_features = raw_data['smc_features']
            indicators = raw_data['indicators']
            
            trend = self._determine_trend(smc_features)
            signal_strength = self._calculate_signal_strength(smc_features)
            recommendation = self._get_recommendation(trend, indicators.get('rsi', 50))

            return {
                'symbol': raw_data['symbol'],
                'timeframe': raw_data['timeframe'],
                'current_price': raw_data['current_price'],
                'indicators': indicators,
                'analysis': {
                    'trend': trend,
                    'signal': recommendation,
                    'confidence': round(signal_strength * 10, 2),
                    'smc_features': smc_features,
                },
                'timestamp': datetime.now().isoformat(),
                'error': False
            }

        except Exception as e:
            logger.error(f"Lỗi xử lý dữ liệu phân tích cho bot: {e}", exc_info=True)
            return {'error': True, 'message': 'Lỗi xử lý dữ liệu sau phân tích.'}

    def _calculate_signal_strength(self, smc_features: dict):
        strength = 0.0
        if 'Bullish' in smc_features.get('break_of_structure', {}).get('status', ''): strength += 3
        if 'Bearish' in smc_features.get('break_of_structure', {}).get('status', ''): strength += 3
        if 'Zone' in smc_features.get('order_blocks', {}).get('status', ''): strength += 2
        if 'Swept' in smc_features.get('liquidity_zones', {}).get('status', ''): strength += 2
        return min(strength, 10.0)

    def _determine_trend(self, smc_features: dict):
        bos_status = smc_features.get('break_of_structure', {}).get('status', 'N/A')
        if 'Bullish' in bos_status: return 'Tăng giá'
        if 'Bearish' in bos_status: return 'Giảm giá'
        return 'Đi ngang'

    def _get_recommendation(self, trend: str, rsi: float):
        if trend == 'Tăng giá' and rsi < 65: return "MUA"
        if trend == 'Giảm giá' and rsi > 35: return "BÁN"
        return "CHỜ"
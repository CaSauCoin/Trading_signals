import logging
from src.core.analysis import AdvancedSMC
from datetime import datetime

logger = logging.getLogger(__name__)

class BotAnalysisService:
    def __init__(self):
        self.smc_analyzer = AdvancedSMC()

    def get_analysis_for_symbol(self, symbol: str, timeframe: str) -> dict:
        """
        Lấy phân tích chi tiết từ core và tạo insight cho bot.
        """
        logger.info(f"Bắt đầu phân tích '{symbol}' ({timeframe}) bằng logic chi tiết.")
        
        # Gọi hàm get_trading_signals để lấy toàn bộ dữ liệu
        analysis_data = self.smc_analyzer.get_trading_signals(symbol, timeframe)
        
        if not analysis_data:
            return {'error': True, 'message': f'Không thể phân tích {symbol}.'}

        try:
            # Tạo insight dựa trên kết quả chi tiết
            suggestion = self._get_trading_suggestion(
                analysis_data.get('smc_analysis', {}),
                analysis_data.get('indicators', {}),
                analysis_data.get('trading_signals', {})
            )
            
            # Gói kết quả trả về
            analysis_data['analysis'] = {'suggestion': suggestion}
            analysis_data['error'] = False
            return analysis_data

        except Exception as e:
            logger.error(f"Lỗi khi xử lý và tạo insight cho bot: {e}", exc_info=True)
            return {'error': True, 'message': 'Lỗi xử lý dữ liệu sau phân tích.'}

    def _get_trading_suggestion(self, smc: dict, indicators: dict, trading_signals: dict) -> str:
        """
        Tái tạo logic tạo gợi ý từ file trading_bot.py của bạn.
        """
        suggestions = []
        try:
            rsi = indicators.get('rsi', 50)

            # Phân tích RSI
            if rsi > 70: suggestions.append("⚠️ Cân nhắc bán (RSI > 70)")
            elif rsi < 30: suggestions.append("🚀 Cân nhắc mua (RSI < 30)")

            # Phân tích SMC
            if smc.get('break_of_structure'):
                latest_bos = smc['break_of_structure'][-1]
                if latest_bos.get('type') == 'bullish_bos': suggestions.append("📈 Xu hướng tăng (Bullish BOS)")
                elif latest_bos.get('type') == 'bearish_bos': suggestions.append("📉 Xu hướng giảm (Bearish BOS)")

            # Phân tích FVG
            if smc.get('fair_value_gaps'):
                suggestions.append("🎯 Chờ giá retest các vùng FVG")

            # Phân tích tín hiệu vào lệnh
            if trading_signals and trading_signals.get('entry_long'):
                suggestions.append("🟢 Tín hiệu MUA đã xuất hiện")
            if trading_signals and trading_signals.get('entry_short'):
                suggestions.append("🔴 Tín hiệu BÁN đã xuất hiện")

            if not suggestions:
                return "⏸️ Thị trường đang đi ngang. Nên đứng ngoài quan sát và chờ tín hiệu phá vỡ cấu trúc (BOS)."

            return "\n".join([f"• {s}" for s in suggestions])
        except Exception as e:
            logger.error(f"Lỗi trong _get_trading_suggestion: {e}")
            return "⚠️ Không thể tạo gợi ý - Dữ liệu không đầy đủ."

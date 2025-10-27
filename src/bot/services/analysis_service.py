# src/bot/services/analysis_service.py
import logging
from src.core.analysis import AdvancedSMC
from datetime import datetime

logger = logging.getLogger(__name__)


class BotAnalysisService:
    def __init__(self):
        self.smc_analyzer = AdvancedSMC()

    def get_analysis_for_symbol(self, symbol: str, timeframe: str) -> dict:
        """
        Lấy phân tích chi tiết từ lõi và tạo thông tin chi tiết cho bot.
        """
        logger.info(f"Bắt đầu phân tích chi tiết cho '{symbol}' ({timeframe}).")

        analysis_data = self.smc_analyzer.get_trading_signals(symbol, timeframe)

        if not analysis_data:
            return {'error': True, 'message': f'Không thể phân tích {symbol}.'}

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
            logger.error(f"Lỗi khi xử lý và tạo thông tin chi tiết cho bot: {e}", exc_info=True)
            return {'error': True, 'message': 'Lỗi xử lý dữ liệu sau khi phân tích.'}

    def _get_trading_suggestion(self, smc: dict, indicators: dict, trading_signals: dict) -> str:
        """
        Logic để tạo gợi ý giao dịch chi tiết, kết hợp nhiều yếu tố.
        ĐÃ XÓA RSI VÀ FVG THEO YÊU CẦU.
        """
        suggestions = []
        try:
            # Phân tích cấu trúc (BOS)
            if smc.get('break_of_structure'):
                latest_bos = smc['break_of_structure'][-1]
                if latest_bos.get('type') == 'bullish_bos':
                    suggestions.append("📈 Xác nhận tín hiệu tăng")
                elif latest_bos.get('type') == 'bearish_bos':
                    suggestions.append("📉 Xác nhận tín hiệu giảm")


            # Phân tích tín hiệu vào lệnh trực tiếp
            if trading_signals and trading_signals.get('entry_long'):
                suggestions.append("🟢 Đã phát hiện tín hiệu MUA")
            if trading_signals and trading_signals.get('entry_short'):
                suggestions.append("🔴 Đã phát hiện tín hiệu BÁN")
            if not suggestions:
                return "⏸️ Thị trường đang đi ngang. Cân nhắc đứng ngoài và chờ tín hiệu rõ ràng hơn."

            return "\n".join([f"• {s}" for s in suggestions])
        except Exception as e:
            logger.error(f"Lỗi trong hàm _get_trading_suggestion: {e}")
            return "⚠️ Không thể tạo gợi ý - Không đủ dữ liệu."
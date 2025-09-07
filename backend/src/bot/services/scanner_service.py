# src/bot/services/scanner_service.py
import logging
from src.core.analysis import AdvancedSMC
from src.core.data_fetcher import get_top_symbols_by_volume

logger = logging.getLogger(__name__)

class MarketScannerService:
    def __init__(self):
        self.smc_analyzer = AdvancedSMC()

    def _get_signal_state(self, recommendation: str) -> str:
        """Chuyển đổi khuyến nghị chi tiết thành trạng thái đơn giản."""
        if "BUY" in recommendation:
            return "Long"
        if "SELL" in recommendation:
            return "Short"
        return "Neutral"

    def run_scan(self, previous_states: dict, timeframe='4h') -> (list, dict):
        """
        Thực hiện quét 100 token, so sánh và trả về những token có sự thay đổi.
        """
        flipped_tokens = []
        new_states = {}
        
        top_100_symbols = get_top_symbols_by_volume('binance', 250)
        
        for i, symbol in enumerate(top_100_symbols):
            logger.info(f"[SCAN {i+1}/{len(top_100_symbols)}] Đang phân tích {symbol}...")
            try:
                # SỬA LỖI Ở ĐÂY: Gọi đúng hàm get_telegram_summary
                analysis = self.smc_analyzer.get_telegram_summary(symbol, timeframe)
                if not analysis:
                    continue

                current_state = self._get_signal_state(analysis.get('recommendation', ''))
                previous_state = previous_states.get(symbol)
                
                # Lưu trạng thái mới
                new_states[symbol] = current_state
                
                # So sánh với trạng thái cũ
                if previous_state and current_state != previous_state:
                    if current_state != 'Neutral':
                        flipped_tokens.append({
                            'symbol': symbol,
                            'from': previous_state,
                            'to': current_state,
                            'price': analysis.get('price', 0)
                        })
                        logger.warning(f"ĐẢO CHIỀU TÍN HIỆU: {symbol} từ {previous_state} -> {current_state}")

            except Exception as e:
                logger.error(f"Lỗi khi quét token {symbol}: {e}")
                continue
                
        return flipped_tokens, new_states
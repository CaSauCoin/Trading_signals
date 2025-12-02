import logging
from src.core.analysis import AdvancedSMC
from src.bot.ai_agent import TradingCouncil

logger = logging.getLogger(__name__)


class BotAnalysisService:
    def __init__(self):
        self.smc_analyzer = AdvancedSMC()
        self.council = TradingCouncil()

    def get_analysis_for_symbol(self, symbol: str, timeframe: str) -> dict:
        logger.info(f"Analyzing {symbol} ({timeframe})...")

        # 1. Lấy dữ liệu SMC & Indicators
        analysis_data = self.smc_analyzer.get_trading_signals(symbol, timeframe)
        if not analysis_data:
            return {'error': True, 'message': f'Không thể phân tích {symbol}.'}

        try:
            # 2. TÍNH TOÁN SETUP (ENTRY/SL/TP) BẰNG CODE CŨ (Toán học chính xác)
            # Chúng ta tính cả 2 kịch bản Long và Short để AI tự chọn kèo nào hợp lý
            setup_params = self._calculate_setup_parameters(
                analysis_data['current_price'],
                analysis_data['smc_analysis']
            )

            # 3. GỌI HỘI ĐỒNG AI (Kèm theo thông số Setup)
            ai_verdict = self.council.execute_analysis_pipeline(
                symbol=analysis_data['symbol'],
                timeframe=analysis_data['timeframe'],
                smc_data=analysis_data['smc_analysis'],
                indicators=analysis_data['indicators'],
                setup_params=setup_params
            )

            analysis_data['ai_analysis'] = ai_verdict
            analysis_data['error'] = False

            # Tạo gợi ý text cơ bản (fallback)
            analysis_data['analysis'] = {'suggestion': "Xem chi tiết phân tích AI bên dưới."}

            return analysis_data

        except Exception as e:
            logger.error(f"Analysis Service Error: {e}", exc_info=True)
            return {'error': True, 'message': 'Lỗi hệ thống phân tích.'}

    def _calculate_setup_parameters(self, price: float, smc_data: dict) -> dict:
        # --- 1. KỊCH BẢN LONG ---
        # Tìm SL cho Long: Đáy gần nhất hoặc OB Buy gần nhất
        long_sl = price * 0.99  # Mặc định 1%

        # Tìm Liquidity Zone (Swing Low) dưới giá
        swings = [z['price'] for z in smc_data.get('liquidity_zones', []) if
                  z['type'] == 'sell_side_liquidity' and z['price'] < price]
        # Tìm Order Block Bullish dưới giá
        obs = [ob['low'] for ob in smc_data.get('order_blocks', []) if ob['type'] == 'bullish_ob' and ob['low'] < price]

        potential_sl_long = swings + obs
        if potential_sl_long:
            long_sl = max(potential_sl_long) * 0.999  # Lấy điểm cao nhất trong các đáy (gần giá nhất) - buffer

        # Tính TP Long (R:R 1.5 và 3)
        risk_long = price - long_sl
        long_tp1 = price + (risk_long * 1.5)
        long_tp2 = price + (risk_long * 3.0)

        # --- 2. KỊCH BẢN SHORT ---
        # Tìm SL cho Short: Đỉnh gần nhất hoặc OB Sell gần nhất
        short_sl = price * 1.01  # Mặc định 1%

        swings_high = [z['price'] for z in smc_data.get('liquidity_zones', []) if
                       z['type'] == 'buy_side_liquidity' and z['price'] > price]
        obs_high = [ob['high'] for ob in smc_data.get('order_blocks', []) if
                    ob['type'] == 'bearish_ob' and ob['high'] > price]

        potential_sl_short = swings_high + obs_high
        if potential_sl_short:
            short_sl = min(potential_sl_short) * 1.001  # Lấy điểm thấp nhất trong các đỉnh - buffer

        # Tính TP Short
        risk_short = short_sl - price
        short_tp1 = price - (risk_short * 1.5)
        short_tp2 = price - (risk_short * 3.0)

        # Format số đẹp
        def fmt(p):
            return f"{p:.4f}" if p < 10 else f"{p:.2f}"

        return {
            "long_setup": f"Entry: {fmt(price)} | SL: {fmt(long_sl)} | TP1: {fmt(long_tp1)} | TP2: {fmt(long_tp2)}",
            "short_setup": f"Entry: {fmt(price)} | SL: {fmt(short_sl)} | TP1: {fmt(short_tp1)} | TP2: {fmt(short_tp2)}"
        }


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
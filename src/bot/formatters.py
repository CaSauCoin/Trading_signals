from datetime import datetime
import re  # Cần import thư viện re để lọc


def format_price(price: float) -> str:
    """Định dạng giá token một cách linh hoạt."""
    if not isinstance(price, (int, float)) or price == 0:
        return "N/A"
    if price >= 1:
        return f"{price:,.2f}"
    else:
        # Hiển thị tối đa 8 chữ số thập phân, xóa các số 0 ở cuối
        return f"{price:,.8f}".rstrip('0').rstrip('.')


def _clean_suggestion(suggestion: str) -> str:
    """
    Dịch và đơn giản hóa các thuật ngữ trong gợi ý.
    Xóa các tham chiếu đến FVG và RSI theo yêu cầu.
    """

    # 1. Dịch các thuật ngữ tiếng Anh phổ biến (Bạn có thể thêm vào đây)
    # Đây là nơi bạn dịch các chuỗi mà service của bạn có thể trả về
    replacements = {
        "Bullish trend": "Xu hướng tăng",
        "Bearish trend": "Xu hướng giảm",
        "Wait for retest": "Chờ retest",
        "Wait for confirmation": "Chờ xác nhận",
        "Long signal appeared": "Tín hiệu Long xuất hiện",
        "Short signal appeared": "Tín hiệu Short xuất hiện",
        "Consider entry": "Xem xét vào lệnh",
        "Look for Long": "Tìm cơ hội Long",
        "Look for Short": "Tìm cơ hội Short",
        "No suggestion available.": "Không có gợi ý.",
        # Thêm các cụm từ khác mà bạn muốn dịch ở đây...
    }

    for en, vi in replacements.items():
        suggestion = suggestion.replace(en, vi)

    # 2. Xóa các dòng chứa FVG hoặc RSI
    # Tách gợi ý thành các dòng riêng biệt
    lines = suggestion.split('\n')

    # Giữ lại một dòng NẾU nó KHÔNG chứa "FVG" và KHÔNG chứa "RSI"
    # re.IGNORECASE là để tìm kiếm không phân biệt hoa/thường (ví dụ: FVG, fvg, Rsi...)
    cleaned_lines = []
    for line in lines:
        if not re.search(r'FVG|RSI', line, re.IGNORECASE):
            cleaned_lines.append(line.strip())  # Thêm .strip() để xóa khoảng trắng thừa

    # 3. Nối các dòng đã lọc lại
    final_suggestion = "\n".join(cleaned_lines)

    # 4. Xử lý trường hợp sau khi lọc không còn gì
    if not final_suggestion.strip():
        return "Không có gợi ý."

    return final_suggestion


def format_analysis_result(result: dict) -> str:
    """Định dạng kết quả phân tích kèm theo AI Analysis."""
    if result.get('error'):
        return f"❌ **Lỗi:** {result.get('message')}"

    symbol = result.get('symbol', 'N/A')
    timeframe = result.get('timeframe', 'N/A')
    price = result.get('current_price', 0)
    indicators = result.get('indicators', {})
    smc = result.get('smc_analysis', {})

    # --- 1. HEADER & PRICE ---
    header = f"📊 *Phân tích {symbol} - {timeframe}*\n"
    price_info = (
        f"💰 *Giá hiện tại:* ${format_price(price)}\n"
        f"📈 *RSI:* {indicators.get('rsi', 0):.1f} | *Thay đổi:* {indicators.get('price_change_pct', 0):+.2f}%\n"
    )

    # --- 2. TECHNICAL SUMMARY (SMC) ---
    analysis_section = "🔍 *SMC STRUCTURE:*\n"

    bos_list = smc.get('break_of_structure', [])
    if bos_list:
        latest_bos = bos_list[-1]
        analysis_section += f"🔄 *BOS:* {latest_bos['type'].upper()} @ {format_price(latest_bos['price'])}\n"

    ob_list = smc.get('order_blocks', [])
    if ob_list:
        latest_ob = ob_list[-1]
        analysis_section += f"🧱 *OB:* {latest_ob['type'].upper()} ({format_price(latest_ob['low'])} - {format_price(latest_ob['high'])})\n"

    # --- 3. AI COUNCIL VERDICT (PHẦN MỚI) ---
    ai_verdict = result.get('ai_analysis', '')
    ai_section = ""
    if ai_verdict:
        ai_section = f"\n━━━━━━━━━━━━━━━━━━\n{ai_verdict}\n"

    # --- 4. FOOTER ---
    timestamp = datetime.fromtimestamp(result.get('timestamp', datetime.now().timestamp()))
    footer = f"\n🕐 *Cập nhật:* {timestamp.strftime('%H:%M %d/%m')}"

    full_message = (
        f"{header}"
        f"{price_info}\n"
        f"{analysis_section}"
        f"{ai_section}" 
        f"{footer}"
    )

    return full_message


def format_scanner_notification(flipped_tokens: list, timeframe: str) -> str:
    """Định dạng thông báo từ bộ quét thị trường."""

    bullish_flips = [t for t in flipped_tokens if t['to'] == 'Long']
    bearish_flips = [t for t in flipped_tokens if t['to'] == 'Short']

    timestamp = datetime.now().strftime('%H:%M %d/%m/%Y')
    message = f"🚨 **Tín hiệu Đảo chiều Thị trường - Khung {timeframe}**\n_{timestamp}_\n\n"

    if bullish_flips:
        message += "--- TÍN HIỆU TĂNG GIÁ ---\n"
        for token in bullish_flips:
            message += f"🟢 `{token['symbol']}`\n"
            message += f"    `{token['from']} -> {token['to']}`\n\n"

    if bearish_flips:
        message += "--- TÍN HIỆU GIẢM GIÁ ---\n"
        for token in bearish_flips:
            message += f"🔴 `{token['symbol']}`\n"
            message += f"    `{token['from']} -> {token['to']}`\n\n"

    message += "_Đây là những tín hiệu sớm, vui lòng phân tích kỹ trước khi giao dịch._"

    return message


def _calculate_dynamic_levels(price: float, is_long: bool, smc_data: dict):
    """
    Tính toán SL/TP dựa trên cấu trúc SMC (Swing Low/High, OB).
    Nếu không tìm thấy cấu trúc, fallback về mức mặc định 1%.
    """
    # 1. Lấy dữ liệu cấu trúc
    liquidity_zones = smc_data.get('liquidity_zones', [])
    order_blocks = smc_data.get('order_blocks', [])

    # Mặc định SL 1% nếu không tìm thấy điểm cản
    fallback_percent = 0.01
    stoploss = price * (1 - fallback_percent) if is_long else price * (1 + fallback_percent)
    found_structure = False

    # 2. Logic tìm điểm SL (Structural Stoploss)
    potential_sl_levels = []

    if is_long:
        # Long: Tìm các đáy (Swing Low) hoặc OB tăng nằm dưới giá hiện tại
        for zone in liquidity_zones:
            if zone['type'] == 'sell_side_liquidity' and zone['price'] < price:
                potential_sl_levels.append(zone['price'])

        for ob in order_blocks:
            if ob['type'] == 'bullish_ob' and ob['low'] < price:
                potential_sl_levels.append(ob['low'])  # Lấy cạnh dưới của OB

        # Nếu tìm thấy, lấy điểm cao nhất trong các điểm thấp (điểm gần giá nhất) làm SL
        if potential_sl_levels:
            # Trừ thêm chút buffer (0.1%) để tránh bị quét râu
            stoploss = max(potential_sl_levels) * 0.999
            found_structure = True

    else:  # Short
        # Short: Tìm các đỉnh (Swing High) hoặc OB giảm nằm trên giá hiện tại
        for zone in liquidity_zones:
            if zone['type'] == 'buy_side_liquidity' and zone['price'] > price:
                potential_sl_levels.append(zone['price'])

        for ob in order_blocks:
            if ob['type'] == 'bearish_ob' and ob['high'] > price:
                potential_sl_levels.append(ob['high'])  # Lấy cạnh trên của OB

        # Nếu tìm thấy, lấy điểm thấp nhất trong các điểm cao (điểm gần giá nhất) làm SL
        if potential_sl_levels:
            # Cộng thêm chút buffer (0.1%)
            stoploss = min(potential_sl_levels) * 1.001
            found_structure = True

    # 3. Tính TP theo Risk:Reward (R:R)
    # Risk = Khoảng cách từ Entry đến SL
    risk = abs(price - stoploss)

    # Nếu Risk quá nhỏ (do SL quá gần), force tối thiểu 0.2% để tránh TP giật cục
    min_risk = price * 0.002
    if risk < min_risk:
        risk = min_risk
        stoploss = (price - risk) if is_long else (price + risk)

    if is_long:
        tp1 = price + (risk * 1.5)  # RR 1:1.5
        tp2 = price + (risk * 3.0)  # RR 1:3
    else:
        tp1 = price - (risk * 1.5)
        tp2 = price - (risk * 3.0)

    return stoploss, tp1, tp2, found_structure


def format_short_signal_message(result: dict) -> str:
    """
    Tạo tin nhắn tín hiệu rút gọn với SL/TP thông minh từ SMC.
    """
    symbol = result.get('symbol', 'UNKNOWN').replace('/', '')
    price = result.get('current_price', 0)
    smc_data = result.get('smc_analysis', {})

    # --- Xác định Trend (Long/Short) ---
    trading_signals = result.get('trading_signals', {})

    # Ưu tiên tín hiệu entry cụ thể
    if trading_signals.get('entry_long'):
        is_long = True
        direction_str = "MUA (BUY)"
        action_str = "Mua"
        icon = "🟢"
    elif trading_signals.get('entry_short'):
        is_long = False
        direction_str = "BÁN (SELL)"
        action_str = "Bán"
        icon = "🔴"
    else:
        # Fallback theo BOS gần nhất
        bos = smc_data.get('break_of_structure', [])
        if bos and bos[-1]['type'] == 'bullish_bos':
            is_long = True
            direction_str = "MUA (BUY)"
            action_str = "Mua"
            icon = "🟢"
        else:
            is_long = False
            direction_str = "BÁN (SELL)"
            action_str = "Bán"
            icon = "🔴"

    # --- TÍNH TOÁN SL / TP DỰA TRÊN ANALYZE ---
    stoploss, tp1, tp2, is_smart_sl = _calculate_dynamic_levels(price, is_long, smc_data)

    def fmt(val):
        if val < 1: return f"{val:.5f}".rstrip('0')
        return f"{val:,.2f}"

    message = (
        f"{icon} TÍN HIỆU {direction_str}  Mã: {symbol}\n"
        f"-------------------- Vào lệnh NOW\n"
        f"➡️ {action_str}: {fmt(price)}\n"
        f"🎯 TP 1 (1.5R): {fmt(tp1)}\n"
        f"🚀 TP 2 (3.0R): {fmt(tp2)}\n"
        f"🛑 Stoploss: {fmt(stoploss)}"
    )

    return message

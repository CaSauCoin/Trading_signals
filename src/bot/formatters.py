# src/bot/formatters.py
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
    """Định dạng kết quả phân tích chi tiết sang tiếng Việt."""
    if result.get('error'):
        return f"❌ **Lỗi:** {result.get('message')}"

    # --- 1. Trích xuất dữ liệu ---
    symbol = result.get('symbol', 'N/A')
    timeframe = result.get('timeframe', 'N/A')
    price = result.get('current_price', 0)

    indicators = result.get('indicators', {})
    smc = result.get('smc_analysis', {})
    trading_signals = result.get('trading_signals', {})

    # Lấy gợi ý gốc
    original_suggestion = result.get('analysis', {}).get('suggestion', 'Không có gợi ý.')

    # **THAY ĐỔI Ở ĐÂY: Lọc và làm sạch gợi ý**
    suggestion = _clean_suggestion(original_suggestion)

    # --- 2. Xây dựng từng phần của tin nhắn ---

    # Tiêu đề
    header = f"📊 *Phân tích {symbol} - {timeframe}*\n"

    # Thông tin giá
    price_info = (
        f"💰 *Giá hiện tại:* ${format_price(price)}\n"
        f"📈 *Thay đổi 24h:* {indicators.get('price_change_pct', 0):+.2f}%\n"
    )

    # Phần PHÂN TÍCH
    analysis_section = "🔍 *ANALYSIS:*\n"

    bos_list = smc.get('break_of_structure', [])
    analysis_section += f"🔄 *Structure:*\n"
    if bos_list:
        latest_bos = bos_list[-1]
        bos_type = latest_bos.get('type', 'N/A').replace('_bos', ' ').upper()
        analysis_section += f"    *Gần nhất:* {bos_type}\n"
        analysis_section += f"    *Price:* ${format_price(latest_bos.get('price', 0))}\n"

    lz_list = smc.get('liquidity_zones', [])
    analysis_section += f"💧 *Liquidity Zones:* \n"
    if lz_list:
        latest_lz = lz_list[-1]
        lz_type = latest_lz.get('type', 'N/A').replace('_', ' ').title()
        analysis_section += f"    *Gần nhất:* {lz_type}\n"
        analysis_section += f"    *Level:* ${format_price(latest_lz.get('price', 0))}\n"

    # Phần TÍN HIỆU GIAO DỊCH
    signals_section = "🔔 *TRADING SIGNALS:*\n"
    has_signal = False
    if trading_signals:
        entry_long = trading_signals.get('entry_long', [])
        entry_short = trading_signals.get('entry_short', [])

        if entry_long:
            has_signal = True
            latest_long = entry_long[-1]
            signals_section += f"🟢 *Long Signal:* ${format_price(latest_long.get('price', 0))}\n"
            # signals_section += f"    *Tag:* {latest_long.get('tag', 'N/A')}\n"

        if entry_short:
            has_signal = True
            latest_short = entry_short[-1]
            signals_section += f"🔴 *Short Signal:* ${format_price(latest_short.get('price', 0))}\n"
            # signals_section += f"    *Tag:* {latest_short.get('tag', 'N/A')}\n"

    if not has_signal:
        signals_section += "⏸️ Không có tín hiệu vào lệnh mới.\n"

    # Gợi ý Trading (Đã được lọc)
    suggestion_section = f"💡 *Gợi ý Trading:*\n{suggestion}\n"

    # Dấu thời gian
    timestamp = datetime.fromtimestamp(result.get('timestamp', datetime.now().timestamp()))
    footer = f"🕐 *Cập nhật:* {timestamp.strftime('%H:%M:%S %d/%m/%Y')}"

    # Kết hợp tất cả
    full_message = (
        f"{header}\n"
        f"{price_info}\n"
        f"{analysis_section}\n"
        f"{signals_section}\n"
        f"{suggestion_section}\n"
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
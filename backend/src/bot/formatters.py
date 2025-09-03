# src/bot/formatters.py
from datetime import datetime

def format_price(price: float) -> str:
    """Định dạng giá token một cách linh hoạt."""
    if not isinstance(price, (int, float)) or price == 0:
        return "N/A"
    if price >= 1:
        return f"{price:,.2f}"
    else:
        return f"{price:,.8f}".rstrip('0').rstrip('.')

def format_analysis_result(result: dict) -> str:
    """Định dạng kết quả phân tích chi tiết thành tin nhắn Telegram."""
    if result.get('error'):
        return f"❌ **Lỗi:** {result.get('message')}"

    # --- Trích xuất dữ liệu ---
    symbol = result.get('symbol', 'N/A')
    timeframe = result.get('timeframe', 'N/A')
    price = result.get('current_price', 0)
    indicators = result.get('indicators', {})
    smc = result.get('smc_analysis', {})
    trading_signals = result.get('trading_signals', {})
    suggestion = result.get('analysis', {}).get('suggestion', 'Không có gợi ý.')
    
    # --- Định dạng các thành phần ---
    formatted_price = format_price(price)
    price_change = indicators.get('price_change_pct', 0)
    change_emoji = "📈" if price_change > 0 else "📉"
    
    rsi = indicators.get('rsi', 50)
    rsi_emoji = "🟢" if rsi < 30 else ("🔴" if rsi > 70 else "🟡")

    # --- Xây dựng tin nhắn ---
    message = f"📊 *Phân tích {symbol} - {timeframe}*\n\n"
    message += f"💰 *Giá hiện tại:* ${formatted_price}\n"
    message += f"{change_emoji} *Thay đổi 24h:* {price_change:+.2f}%\n"
    message += f"📈 *RSI:* {rsi_emoji} {rsi:.1f}\n\n"
    
    message += f"💡 *Gợi ý Trading:*\n{suggestion}\n\n"
    
    message += "🔍 *Tín hiệu SMC chi tiết:*\n"

    # Order Blocks
    ob_list = smc.get('order_blocks', [])
    if ob_list:
        latest_ob = ob_list[-1]
        ob_emoji = "🟢" if latest_ob['type'] == 'bullish_ob' else "🔴"
        if latest_ob.get('low') is not None and latest_ob.get('high') is not None:
            message += f"  {ob_emoji} *OB gần nhất:* ${format_price(latest_ob['low'])} - ${format_price(latest_ob['high'])}\n"

    # Fair Value Gaps
    fvg_list = smc.get('fair_value_gaps', [])
    if fvg_list:
        latest_fvg = fvg_list[-1]
        if latest_fvg.get('top') is not None and latest_fvg.get('bottom') is not None:
            message += f"  🎯 *FVG gần nhất:* ${format_price(latest_fvg['bottom'])} - ${format_price(latest_fvg['top'])}\n"

    # Break of Structure
    bos_list = smc.get('break_of_structure', [])
    if bos_list:
        latest_bos = bos_list[-1]
        bos_emoji = "🟢" if latest_bos['type'] == 'bullish_bos' else "🔴"
        bos_type = latest_bos['type'].replace('_', ' ').upper()
        message += f"  {bos_emoji} *Cấu trúc:* {bos_type} tại ${format_price(latest_bos['price'])}\n"

    # Trading Signals
    if trading_signals:
        entry_long = trading_signals.get('entry_long', [])
        entry_short = trading_signals.get('entry_short', [])
        if entry_long:
            message += f"  🟢 *Tín hiệu Long:* tại ${format_price(entry_long[-1]['price'])}\n"
        if entry_short:
            message += f"  🔴 *Tín hiệu Short:* tại ${format_price(entry_short[-1]['price'])}\n"

    # Timestamp
    timestamp = datetime.fromtimestamp(result.get('timestamp', datetime.now().timestamp()))
    message += f"\n🕐 *Cập nhật:* {timestamp.strftime('%H:%M:%S %d/%m/%Y')}"

    return message

def format_scanner_notification(flipped_tokens: list, timeframe: str) -> str:
    """Định dạng thông báo quét thị trường."""
    
    bullish_flips = [t for t in flipped_tokens if t['to'] == 'Long']
    bearish_flips = [t for t in flipped_tokens if t['to'] == 'Short']
    
    timestamp = datetime.now().strftime('%H:%M %d/%m/%Y')
    message = f"🚨 **Tín hiệu Đảo chiều Thị trường - Khung {timeframe}**\n_{timestamp}_\n\n"
    
    if bullish_flips:
        message += "--- Tín hiệu TĂNG GIÁ (Bullish Flips)  bullish ---\n"
        for token in bullish_flips:
            message += f"🟢 `{token['symbol']}`\n"
            message += f"    `{token['from']} -> {token['to']}`\n\n"
    
    if bearish_flips:
        message += "--- Tín hiệu GIẢM GIÁ (Bearish Flips) bearish ---\n"
        for token in bearish_flips:
            message += f"🔴 `{token['symbol']}`\n"
            message += f"    `{token['from']} -> {token['to']}`\n\n"
            
    message += "_Đây là tín hiệu sớm, hãy tự phân tích kỹ trước khi giao dịch._"
    
    return message
# src/bot/formatters.py
from datetime import datetime

def format_price(price: float) -> str:
    """Định dạng giá token một cách linh hoạt."""
    if not isinstance(price, (int, float)) or price == 0:
        return "N/A"
    if price >= 1:
        return f"{price:,.2f}"
    else:
        # Hiển thị tối đa 8 chữ số thập phân, xóa số 0 thừa
        return f"{price:,.8f}".rstrip('0').rstrip('.')

def format_analysis_result(result: dict) -> str:
    """Định dạng kết quả phân tích chi tiết theo format yêu cầu."""
    if result.get('error'):
        return f"❌ **Lỗi:** {result.get('message')}"

    # --- 1. Trích xuất dữ liệu ---
    symbol = result.get('symbol', 'N/A')
    timeframe = result.get('timeframe', 'N/A')
    price = result.get('current_price', 0)
    
    indicators = result.get('indicators', {})
    smc = result.get('smc_analysis', {})
    trading_signals = result.get('trading_signals', {})
    suggestion = result.get('analysis', {}).get('suggestion', 'Không có gợi ý.')
    
    # --- 2. Xây dựng từng phần của tin nhắn ---
    
    # Header
    header = f"📊 *Phân tích {symbol} - {timeframe}*\n"
    
    # Price Info
    price_info = (
        f"💰 *Giá hiện tại:* ${format_price(price)}\n"
        f"📈 *RSI:* {indicators.get('rsi', 0):.1f}\n"
        f"📊 *Giá sát (SMA20):* ${format_price(indicators.get('sma_20', 0))}\n"
        f"📉 *Giá dự tốt (EMA20):* ${format_price(indicators.get('ema_20', 0))}\n"
        f"📈 *Thay đổi 24h:* {indicators.get('price_change_pct', 0):+.2f}%\n"
    )

    # ANALYSIS Section
    analysis_section = "🔍 *ANALYSIS:*\n"
    
    # Order Blocks
    ob_list = smc.get('order_blocks', [])
    analysis_section += f"📦 *Order Blocks:* {len(ob_list)}\n"

    # Structure (BOS)
    bos_list = smc.get('break_of_structure', [])
    analysis_section += f"🔄 *Structure:* {len(bos_list)}\n"
    if bos_list:
        latest_bos = bos_list[-1]
        bos_type = "BEARISH BOS" if latest_bos.get('BOS') == -1 else "BULLISH BOS"
        analysis_section += f"    *Gần nhất:* {bos_type}\n"
        analysis_section += f"    *Price:* ${format_price(latest_bos.get('close', 0))}\n"

    # Liquidity Zones
    lz_list = smc.get('liquidity_zones', [])
    analysis_section += f"💧 *Liquidity Zones:* {len(lz_list)}\n"
    if lz_list:
        latest_lz = lz_list[-1]
        lz_type = latest_lz.get('type', 'N/A').replace('_', ' ').title()
        analysis_section += f"    *Gần nhất:* {lz_type}\n"
        analysis_section += f"    *Level:* ${format_price(latest_lz.get('price', 0))}\n"

    # TRADING SIGNALS Section
    signals_section = "🔔 *TRADING SIGNALS:*\n"
    has_signal = False
    if trading_signals:
        entry_long = trading_signals.get('entry_long', [])
        entry_short = trading_signals.get('entry_short', [])
        if entry_long:
            has_signal = True
            latest_long = entry_long[-1]
            signals_section += f"🟢 *Long Signal:* ${format_price(latest_long.get('price', 0))}\n"
            signals_section += f"    *Tag:* {latest_long.get('tag', 'N/A')}\n"
        if entry_short:
            has_signal = True
            latest_short = entry_short[-1]
            signals_section += f"🔴 *Short Signal:* ${format_price(latest_short.get('price', 0))}\n"
            signals_section += f"    *Tag:* {latest_short.get('tag', 'N/A')}\n"
    
    if not has_signal:
        signals_section += "⏸️ Không có tín hiệu vào lệnh mới.\n"

    # Gợi ý Trading
    suggestion_section = f"💡 *Gợi ý Trading:*\n{suggestion}\n"

    # Timestamp
    timestamp = datetime.fromtimestamp(result.get('timestamp', datetime.now().timestamp()))
    footer = f"🕐 *Cập nhật:* {timestamp.strftime('%H:%M:%S %d/%m/%Y')}"

    # --- 3. Ghép nối tất cả lại ---
    full_message = (
        f"{header}\n"
        f"{price_info}\n"
        f"{analysis_section}\n"
        f"{signals_section}\n"
        f"{suggestion_section}\n"
        f"{footer}"
    )

    return full_message
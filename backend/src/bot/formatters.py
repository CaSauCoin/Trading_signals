# src/bot/formatters.py
from . import constants as const
from datetime import datetime

def format_price(price: float) -> str:
    """
    Định dạng giá token một cách linh hoạt:
    - Nếu giá > 10: Lấy 2 chữ số thập phân (ví dụ: $1,234.56)
    - Nếu 1 <= giá <= 10: Lấy 4 chữ số thập phân (ví dụ: $7.8912)
    - Nếu giá < 1: Lấy tối đa 8 chữ số thập phân để hiển thị đủ giá trị cho các token siêu nhỏ (ví dụ: $0.00000078)
    """
    if not isinstance(price, (int, float)) or price == 0:
        return "N/A"
    
    if price > 10:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:,.4f}"
    else:
        # Dùng .8f để đảm bảo các số 0 quan trọng được hiển thị
        # Sau đó dùng .rstrip('0').rstrip('.') để xóa các số 0 không cần thiết ở cuối
        formatted_str = f"{price:,.8f}"
        return f"${formatted_str.rstrip('0').rstrip('.')}"

def format_analysis_result(result: dict) -> str:
    """Định dạng kết quả phân tích để hiển thị."""
    if result.get('error'):
        return f"❌ **Lỗi:** {result.get('message')}"

    symbol = result.get('symbol', 'N/A')
    timeframe = result.get('timeframe', 'N/A')
    analysis = result.get('analysis', {})
    smc_data = analysis.get('smc_features', {})
    price = result.get('current_price', 0)
    indicators = result.get('indicators', {})
    
    signal = analysis.get('signal', 'CHỜ')
    signal_emoji = const.EMOJI_SIGNAL_BUY if signal == 'MUA' else const.EMOJI_SIGNAL_SELL if signal == 'BÁN' else const.EMOJI_SIGNAL_NEUTRAL

    price_change = indicators.get('price_change_pct', 0)
    change_emoji = const.EMOJI_CHART_UP if price_change > 0 else const.EMOJI_CHART_DOWN if price_change < 0 else const.EMOJI_ARROW_RIGHT

    formatted_price = format_price(price)

    return f"""
📊 **Phân tích SMC: {symbol} ({timeframe})**

💰 **Giá hiện tại:** {formatted_price} {change_emoji} {price_change:+.2f}%

{signal_emoji} **Tín hiệu:** {signal}
📈 **Độ tin cậy:** {analysis.get('confidence', 0)}%
📉 **Xu hướng:** {analysis.get('trend', 'N/A')}

🔲 **Order Blocks:** {smc_data.get('order_blocks', {}).get('status', 'N/A')}
⚡ **Fair Value Gaps:** {smc_data.get('fair_value_gaps', {}).get('status', 'N/A')}
📊 **Break of Structure:** {smc_data.get('break_of_structure', {}).get('status', 'N/A')}
💧 **Thanh khoản:** {smc_data.get('liquidity_zones', {}).get('status', 'N/A')}

📊 **RSI:** {indicators.get('rsi', 0):.1f}
💹 **Volume 24h:** ${indicators.get('volume_24h', 0) * float(formatted_price.strip('$').replace(',', '')):,.0f}

⏰ **Cập nhật lúc:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ *Chỉ mang tính tham khảo, không phải lời khuyên tài chính.*
    """.strip()
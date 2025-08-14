import requests

def send_telegram_message(bot_token, chat_id, message):
    """Gửi tin nhắn đến một chat Telegram cụ thể."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'  # Cho phép định dạng text
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # Báo lỗi nếu request thất bại
        print("Gửi tin nhắn Telegram thành công!")
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gửi tin nhắn Telegram: {e}")

def format_fvg_summary(df):
    """Tạo một bản tóm tắt các FVG mới nhất."""
    summary = "*--- Tóm tắt FVG Mới Nhất ---*\n\n"

    # Lấy FVG tăng giá cuối cùng
    last_bullish_fvg = df[df['is_bullish_fvg']].tail(1)
    if not last_bullish_fvg.empty:
        fvg = last_bullish_fvg.iloc[0]
        summary += f"📈 *Bullish FVG*:\n"
        summary += f"  - Thời gian: {fvg.name.strftime('%Y-%m-%d %H:%M')}\n"
        summary += f"  - Vùng giá: {fvg['bullish_fvg_bottom']:.4f} - {fvg['bullish_fvg_top']:.4f}\n\n"

    # Lấy FVG giảm giá cuối cùng
    last_bearish_fvg = df[df['is_bearish_fvg']].tail(1)
    if not last_bearish_fvg.empty:
        fvg = last_bearish_fvg.iloc[0]
        summary += f"📉 *Bearish FVG*:\n"
        summary += f"  - Thời gian: {fvg.name.strftime('%Y-%m-%d %H:%M')}\n"
        summary += f"  - Vùng giá: {fvg['bearish_fvg_bottom']:.4f} - {fvg['bearish_fvg_top']:.4f}\n"

    return summary

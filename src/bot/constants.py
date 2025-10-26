# src/bot/constants.py

# --- Texts ---
WELCOME_TEXT = """
🚀 **Alpha Signal!**

Chọn một tùy chọn bên dưới để bắt đầu
"""

HELP_TEXT = """
ℹ️ **Hướng dẫn sử dụng Alpha Signal**

**🎯 Tính năng chính:**
• Phân tích dựa trên SMC (Smart Money Concepts)
• Xác định các Khối Lệnh (Order Blocks), Vùng mất cân bằng (Fair Value Gaps)
• Tín hiệu Phá vỡ cấu trúc (Break of Structure), Vùng thanh khoản (Liquidity zones)

**📱 Cách sử dụng:**
1️⃣ Chọn token từ menu hoặc nhập tùy chỉnh
2️⃣ Xem kết quả phân tích
3️⃣ Thêm vào danh sách theo dõi nếu muốn

**⚡ Lệnh nhanh:**
• /start - Hiển thị menu chính
• /analysis BTC/USDT 4h - Phân tích nhanh

**⚠️ Tuyên bố miễn trừ trách nhiệm:**
Bot chỉ cung cấp phân tích, không phải là lời khuyên tài chính.
"""

# --- User States ---
STATE_WAITING_FOR = "waiting_for"
STATE_CUSTOM_TOKEN = "custom_token"
STATE_ADD_WATCHLIST = "add_watchlist"

# --- Callback Data Prefixes ---
CB_ANALYZE = "analyze"
CB_TIMEFRAME = "timeframe"
CB_REFRESH = "refresh"
CB_WATCHLIST = "watchlist" 
CB_BACK_MAIN = "back_main"
CB_SELECT_PAIR = "select_pair"
CB_CUSTOM_TOKEN = "custom_token"
CB_HELP = "help"

# --- Emojis ---
EMOJI_CHART_UP = "📈"
EMOJI_CHART_DOWN = "📉"
EMOJI_ARROW_RIGHT = "➡️"
EMOJI_SIGNAL_BUY = "🟢"
EMOJI_SIGNAL_SELL = "🔴"
EMOJI_SIGNAL_NEUTRAL = "🟡"
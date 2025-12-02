# src/bot/constants.py

# --- Texts ---
WELCOME_TEXT = """
🚀 **Alpha Signal!**

Chọn một tùy chọn bên dưới để bắt đầu
"""

HELP_TEXT = """
ℹ️ **Hướng dẫn sử dụng Alpha Signal**

Bot này phân tích tín hiệu kỹ thuật (SMC) cho nhiều loại tài sản.

**🎯 Tính năng chính:**
• Phân tích: **Crypto**, **Cổ phiếu (Stocks)**, **Hàng hóa** (Vàng, Dầu...) & **Forex**.
• Xác định các Khối Lệnh (Order Blocks), Tín hiệu Phá vỡ cấu trúc (BOS) và Vùng thanh khoản (Liquidity).

---

**📱 Cách sử dụng Menu**
• Sử dụng các nút bấm trên menu chính để xem nhanh các tài sản phổ biến (BTC, Vàng, Dầu, v.v.).
• Vào **Watchlist** -> **Thông báo** để cài đặt tần suất nhận thông báo (5m, 15m...) cho các mã bạn theo dõi.

---

**✏️ Cách nhập Mã Tùy Chỉnh**
Sử dụng nút "✏️ Nhập token tùy chỉnh" và gửi mã theo các định dạng sau:

1.  **Crypto:** 
    • Phải có dấu `/`.
    • Ví dụ: `BTC/USDT`, `ETH/USDT`, `PEPE/USDT`

2.  **Cổ phiếu, Vàng, Dầu, Forex:** 
    • **Cổ phiếu (Mỹ):** Mã ticker. Ví dụ: `AAPL`, `MSFT`, `TSLA`
    • **Vàng (Gold):** `XAUUSD=X`
    • **Bạc (Silver):** `XAGUSD=X`
    • **Dầu thô (WTI):** `CL=F`
    • **Forex (USD/JPY):** `JPY=X`

---

**⚡ Lệnh nhanh:**
• `/start` - Hiển thị menu chính
• `/analysis <MÃ> <KHUNG_THỜI_GIAN>`
  • Ví dụ Crypto: `/analysis BTC/USDT 4h`
  • Ví dụ Stock: `/analysis AAPL 1d`
  • Ví dụ Vàng: `/analysis XAUUSD=X 1h`

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
CB_SCANNER_MENU = "scanner_menu"
CB_SCANNER_SET = "scanner_set"
CB_HELP = "help"

# --- Emojis ---
EMOJI_CHART_UP = "📈"
EMOJI_CHART_DOWN = "📉"
EMOJI_ARROW_RIGHT = "➡️"
EMOJI_SIGNAL_BUY = "🟢"
EMOJI_SIGNAL_SELL = "🔴"
EMOJI_SIGNAL_NEUTRAL = "🟡"
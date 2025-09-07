# src/bot/constants.py

# --- Texts ---
WELCOME_TEXT = """
🚀 **Alpha Signal!**

Choose an option below to get started
"""

HELP_TEXT = """
ℹ️ **Alpha Signal User Guide**

**🎯 Main Features:**
• Analysis based on SMC (Smart Money Concepts)
• Identify Order Blocks, Fair Value Gaps
• Break of Structure signals, Liquidity zones

**📱 How to use:**
1️⃣ Select token from menu or enter custom
2️⃣ View analysis results
3️⃣ Add to watchlist if desired

**⚡ Quick commands:**
• /start - Show main menu
• /analysis BTC/USDT 4h - Quick analysis

**⚠️ Disclaimer:**
Bot provides analysis only, not financial advice.
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
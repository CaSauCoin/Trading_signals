from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Phân tích BTC/USDT", callback_data='analyze_BTC/USDT')],
        [InlineKeyboardButton("📈 Phân tích ETH/USDT", callback_data='analyze_ETH/USDT')],
        [InlineKeyboardButton("🔍 Chọn cặp có sẵn", callback_data='select_pair')],
        [InlineKeyboardButton("✏️ Nhập token tùy chỉnh", callback_data='custom_token')],
        [InlineKeyboardButton("👁️ Danh sách theo dõi", callback_data='watchlist_menu')],
        [InlineKeyboardButton("ℹ️ Hướng dẫn", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)
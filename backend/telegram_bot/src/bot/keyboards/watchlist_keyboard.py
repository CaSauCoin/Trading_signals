from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_watchlist_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Thêm token theo dõi", callback_data='add_to_watchlist')],
        [InlineKeyboardButton("📋 Xem danh sách theo dõi", callback_data='view_watchlist')],
        [InlineKeyboardButton("🗑️ Xóa token", callback_data='remove_from_watchlist')],
        [InlineKeyboardButton("🔄 Cập nhật ngay", callback_data='update_watchlist_now')],
        [InlineKeyboardButton("🏠 Quay lại Menu", callback_data='start')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_add_to_watchlist_keyboard(symbol):
    keyboard = [
        [InlineKeyboardButton("📊 15m", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_15m'),
         InlineKeyboardButton("📊 1h", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_1h')],
        [InlineKeyboardButton("📊 4h", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_4h'),
         InlineKeyboardButton("📊 1d", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_1d')],
        [InlineKeyboardButton("🔙 Quay lại", callback_data='watchlist_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_remove_from_watchlist_keyboard(watchlist_items):
    keyboard = []
    for i, item in enumerate(watchlist_items):
        callback_data = f"watchlist_remove_{i}_{item['symbol'].replace('/', '_')}_{item['timeframe']}"
        keyboard.append([InlineKeyboardButton(f"🗑️ {item['symbol']} ({item['timeframe']})", callback_data=callback_data)])
    keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data='watchlist_menu')])
    return InlineKeyboardMarkup(keyboard)
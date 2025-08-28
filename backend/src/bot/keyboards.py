# src/bot/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from . import constants as const
from typing import List, Dict, Any

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím cho menu chính."""
    keyboard = [
        [InlineKeyboardButton("📊 Phân tích BTC/USDT", callback_data=f'{const.CB_ANALYZE}:BTC/USDT:4h')],
        [InlineKeyboardButton("📈 Phân tích ETH/USDT", callback_data=f'{const.CB_ANALYZE}:ETH/USDT:4h')],
        [InlineKeyboardButton("🔍 Chọn cặp có sẵn", callback_data=const.CB_SELECT_PAIR)],
        [InlineKeyboardButton("✏️ Nhập token tùy chỉnh", callback_data=const.CB_CUSTOM_TOKEN)],
        [InlineKeyboardButton("👁️ Watchlist", callback_data=f'{const.CB_WATCHLIST}:menu')],
        [InlineKeyboardButton("ℹ️ Hướng dẫn", callback_data=const.CB_HELP)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_analysis_options_keyboard(symbol: str, timeframe: str) -> InlineKeyboardMarkup:
    """Tạo bàn phím sau khi phân tích thành công."""
    keyboard = [
        [InlineKeyboardButton("➕ Thêm vào Watchlist", callback_data=f'{const.CB_WATCHLIST}:add_direct:{symbol}:{timeframe}')],
        [InlineKeyboardButton("🔄 Tải lại", callback_data=f'{const.CB_REFRESH}:{symbol}:{timeframe}')],
        [InlineKeyboardButton("⏱️ Đổi khung thời gian", callback_data=f'{const.CB_TIMEFRAME}:{symbol}')],
        [InlineKeyboardButton("🔙 Menu chính", callback_data=const.CB_BACK_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_timeframe_selection_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """Tạo bàn phím chọn khung thời gian."""
    keyboard = [
        [InlineKeyboardButton(tf, callback_data=f'{const.CB_ANALYZE}:{symbol}:{tf}') for tf in ["15m", "1h", "4h"]],
        [InlineKeyboardButton(tf, callback_data=f'{const.CB_ANALYZE}:{symbol}:{tf}') for tf in ["1d", "3d", "1w"]],
        [InlineKeyboardButton("🔙 Quay lại", callback_data=const.CB_BACK_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_popular_pairs_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím chọn các cặp phổ biến."""
    pairs = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT", "DOT/USDT"]
    keyboard = [
        [
            InlineKeyboardButton(pairs[i], callback_data=f'{const.CB_ANALYZE}:{pairs[i]}:4h'),
            InlineKeyboardButton(pairs[i+1], callback_data=f'{const.CB_ANALYZE}:{pairs[i+1]}:4h')
        ] for i in range(0, len(pairs), 2)
    ]
    keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data=const.CB_BACK_MAIN)])
    return InlineKeyboardMarkup(keyboard)

def create_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím chỉ có nút Back to Main."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data=const.CB_BACK_MAIN)]])

def create_watchlist_menu_keyboard(watchlist: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Tạo bàn phím quản lý watchlist."""
    keyboard = [
        [InlineKeyboardButton(f"📋 Xem danh sách ({len(watchlist)}/10)", callback_data=f'{const.CB_WATCHLIST}:view')],
        [InlineKeyboardButton("➕ Thêm Token", callback_data=f'{const.CB_WATCHLIST}:add_prompt')],
        [InlineKeyboardButton("🗑️ Xóa Token", callback_data=f'{const.CB_WATCHLIST}:remove_menu')],
        [InlineKeyboardButton("🔙 Menu chính", callback_data=const.CB_BACK_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_post_add_watchlist_keyboard() -> InlineKeyboardMarkup:
    """
    Tạo bàn phím hiển thị sau khi thêm token vào watchlist thành công.
    """
    keyboard = [
        [InlineKeyboardButton("➕ Thêm Token Khác", callback_data=f'{const.CB_WATCHLIST}:add_prompt')],
        [InlineKeyboardButton("📋 Xem danh sách", callback_data=f'{const.CB_WATCHLIST}:view')],
        [InlineKeyboardButton("🔙 Menu chính", callback_data=f'{const.CB_BACK_MAIN}')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_remove_token_keyboard(watchlist: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Tạo bàn phím để chọn token cần xóa."""
    keyboard = []
    for item in watchlist:
        symbol = item['symbol']
        timeframe = item['timeframe']
        text = f"❌ {symbol} ({timeframe})"
        callback_data = f"{const.CB_WATCHLIST}:remove_confirm:{symbol}:{timeframe}"
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 Quay lại Watchlist", callback_data=f'{const.CB_WATCHLIST}:menu')])
    return InlineKeyboardMarkup(keyboard)

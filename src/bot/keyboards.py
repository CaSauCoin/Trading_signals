# src/bot/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from . import constants as const
from typing import List, Dict, Any, Optional

from .services.scheduler_service import WATCHLIST_LIMIT



def create_main_menu_keyboard(current_subscription: Optional[str] = None) -> InlineKeyboardMarkup:
    TICKER_OIL = "CL=F"

    keyboard = [
        [InlineKeyboardButton("📊 Phân tích BTC/USDT", callback_data=f'{const.CB_ANALYZE}:BTC/USDT:15m')],
        [InlineKeyboardButton("📈 Phân tích ETH/USDT", callback_data=f'{const.CB_ANALYZE}:ETH/USDT:15m')],
        [InlineKeyboardButton("👑 Vàng (TXAU/USDT)", callback_data=f'{const.CB_ANALYZE}:XAUT/USDT:15m')],
        [InlineKeyboardButton("🛢️ Dầu thô (WTI)", callback_data=f'{const.CB_ANALYZE}:{TICKER_OIL}:1d')],
        [InlineKeyboardButton("🔍 Chọn cặp có sẵn", callback_data=const.CB_SELECT_PAIR)],
        [InlineKeyboardButton("✏️ Nhập token tùy chỉnh", callback_data=const.CB_CUSTOM_TOKEN)],
        [InlineKeyboardButton("👁️ Danh sách theo dõi", callback_data=f'{const.CB_WATCHLIST}:menu')],
        [InlineKeyboardButton("ℹ️ Trợ giúp", callback_data=const.CB_HELP)]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_scanner_menu_keyboard(current_subscription: Optional[str] = None) -> InlineKeyboardMarkup:
    """Tạo bàn phím chọn timeframe cho market scanner."""
    timeframes = ["5m", "15m", "30m", "1h"]
    keyboard = []

    # Tạo các hàng nút, 2 nút mỗi hàng
    for i in range(0, len(timeframes), 2):
        row = []
        for tf in timeframes[i:i + 2]:
            text = f"{'✅' if tf == current_subscription else ''} {tf}"
            callback = f"{const.CB_SCANNER_SET}:{tf}"
            row.append(InlineKeyboardButton(text, callback_data=callback))
        keyboard.append(row)

    # Thêm nút Tắt
    off_text = f"{'✅' if current_subscription is None else ''} Tắt Thông báo"
    keyboard.append([
        InlineKeyboardButton(off_text, callback_data=f"{const.CB_SCANNER_SET}:off")
    ])

    # Thêm nút Quay lại
    keyboard.append([InlineKeyboardButton("🔙 Menu chính", callback_data=const.CB_BACK_MAIN)])
    return InlineKeyboardMarkup(keyboard)

def create_analysis_options_keyboard(symbol: str, timeframe: str) -> InlineKeyboardMarkup:
    """Tạo bàn phím sau khi phân tích thành công."""
    s_symbol = symbol.replace(' ', '')  # Xóa khoảng trắng cho an toàn
    callback_data_sig = f"sig_{s_symbol}_{timeframe}"
    keyboard = [
        [InlineKeyboardButton("⚡ Copy Signal (TP/SL)", callback_data=callback_data_sig)],
        [InlineKeyboardButton("➕ Thêm vào Watchlist",
                              callback_data=f'{const.CB_WATCHLIST}:add_direct:{symbol}:{timeframe}')],
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
            InlineKeyboardButton(pairs[i], callback_data=f'{const.CB_ANALYZE}:{pairs[i]}:15m'),
            InlineKeyboardButton(pairs[i + 1], callback_data=f'{const.CB_ANALYZE}:{pairs[i + 1]}:15m')
        ] for i in range(0, len(pairs), 2)
    ]
    keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data=const.CB_BACK_MAIN)])
    return InlineKeyboardMarkup(keyboard)


def create_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím chỉ có nút Quay lại Menu chính."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại Menu chính", callback_data=const.CB_BACK_MAIN)]])


def create_watchlist_menu_keyboard(watchlist: List[Dict[str, Any]], current_interval: Optional[str] = None) -> InlineKeyboardMarkup:
    """Tạo bàn phím quản lý danh sách theo dõi."""
    # Lưu ý: Giới hạn /10 đang được viết cứng ở đây.
    # Nếu bạn muốn nó đồng bộ với file scheduler_service.py (đang là 3), bạn cần sửa số 10 ở đây.
    if current_interval:
        interval_text = f"🔔 Thông báo ({current_interval})"
    else:
        interval_text = "🔕 Thông báo (Đã tắt)"
    keyboard = [
        [InlineKeyboardButton(f"📋 Xem danh sách ({len(watchlist)}/{WATCHLIST_LIMIT})", callback_data=f'{const.CB_WATCHLIST}:view')],
        [InlineKeyboardButton("➕ Thêm Token", callback_data=f'{const.CB_WATCHLIST}:add_prompt')],
        [InlineKeyboardButton("🗑️ Xóa Token", callback_data=f'{const.CB_WATCHLIST}:remove_menu')],
        [InlineKeyboardButton(interval_text, callback_data=f'{const.CB_WATCHLIST}:notify_menu')],
        [InlineKeyboardButton("🔙 Menu chính", callback_data=const.CB_BACK_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_watchlist_notify_menu_keyboard(current_interval: Optional[str] = None) -> InlineKeyboardMarkup:
    """Tạo bàn phím chọn tần suất thông báo watchlist."""
    timeframes = ["5m", "15m", "30m", "1h"]
    keyboard = []

    for i in range(0, len(timeframes), 2):
        row = []
        for tf in timeframes[i:i + 2]:
            text = f"{'✅' if tf == current_interval else ''} {tf}"
            callback = f"{const.CB_WATCHLIST}:notify_set:{tf}"
            row.append(InlineKeyboardButton(text, callback_data=callback))
        keyboard.append(row)

    off_text = f"{'✅' if current_interval is None else ''} Tắt Thông báo"
    keyboard.append([
        InlineKeyboardButton(off_text, callback_data=f"{const.CB_WATCHLIST}:notify_set:off")
    ])

    keyboard.append([InlineKeyboardButton("🔙 Quay lại Watchlist", callback_data=f'{const.CB_WATCHLIST}:menu')])
    return InlineKeyboardMarkup(keyboard)

def create_post_add_watchlist_keyboard() -> InlineKeyboardMarkup:
    """
    Tạo bàn phím hiển thị sau khi thêm token vào watchlist thành công.
    """
    keyboard = [
        [InlineKeyboardButton("➕ Thêm Token khác", callback_data=f'{const.CB_WATCHLIST}:add_prompt')],
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
        text = f"❌ {symbol} ({timeframe})"  # Giữ nguyên emoji ❌ vì nó rõ ràng
        callback_data = f"{const.CB_WATCHLIST}:remove_confirm:{symbol}:{timeframe}"
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("🔙 Quay lại Watchlist", callback_data=f'{const.CB_WATCHLIST}:menu')])
    return InlineKeyboardMarkup(keyboard)

# src/bot/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from . import constants as const
from typing import List, Dict, Any

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for main menu."""
    keyboard = [
        [InlineKeyboardButton("📊 Analyze BTC/USDT", callback_data=f'{const.CB_ANALYZE}:BTC/USDT:4h')],
        [InlineKeyboardButton("📈 Analyze ETH/USDT", callback_data=f'{const.CB_ANALYZE}:ETH/USDT:4h')],
        [InlineKeyboardButton("🔍 Select available pair", callback_data=const.CB_SELECT_PAIR)],
        [InlineKeyboardButton("✏️ Enter custom token", callback_data=const.CB_CUSTOM_TOKEN)],
        [InlineKeyboardButton("👁️ Watchlist", callback_data=f'{const.CB_WATCHLIST}:menu')],
        [InlineKeyboardButton("ℹ️ Help", callback_data=const.CB_HELP)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_analysis_options_keyboard(symbol: str, timeframe: str) -> InlineKeyboardMarkup:
    """Create keyboard after successful analysis."""
    keyboard = [
        [InlineKeyboardButton("➕ Add to Watchlist", callback_data=f'{const.CB_WATCHLIST}:add_direct:{symbol}:{timeframe}')],
        [InlineKeyboardButton("🔄 Refresh", callback_data=f'{const.CB_REFRESH}:{symbol}:{timeframe}')],
        [InlineKeyboardButton("⏱️ Change timeframe", callback_data=f'{const.CB_TIMEFRAME}:{symbol}')],
        [InlineKeyboardButton("🔙 Main menu", callback_data=const.CB_BACK_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_timeframe_selection_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """Create timeframe selection keyboard."""
    keyboard = [
        [InlineKeyboardButton(tf, callback_data=f'{const.CB_ANALYZE}:{symbol}:{tf}') for tf in ["15m", "1h", "4h"]],
        [InlineKeyboardButton(tf, callback_data=f'{const.CB_ANALYZE}:{symbol}:{tf}') for tf in ["1d", "3d", "1w"]],
        [InlineKeyboardButton("🔙 Back", callback_data=const.CB_BACK_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_popular_pairs_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for selecting popular pairs."""
    pairs = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT", "DOT/USDT"]
    keyboard = [
        [
            InlineKeyboardButton(pairs[i], callback_data=f'{const.CB_ANALYZE}:{pairs[i]}:4h'),
            InlineKeyboardButton(pairs[i+1], callback_data=f'{const.CB_ANALYZE}:{pairs[i+1]}:4h')
        ] for i in range(0, len(pairs), 2)
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=const.CB_BACK_MAIN)])
    return InlineKeyboardMarkup(keyboard)

def create_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard with only Back to Main button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data=const.CB_BACK_MAIN)]])

def create_watchlist_menu_keyboard(watchlist: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Create watchlist management keyboard."""
    keyboard = [
        [InlineKeyboardButton(f"📋 View list ({len(watchlist)}/10)", callback_data=f'{const.CB_WATCHLIST}:view')],
        [InlineKeyboardButton("➕ Add Token", callback_data=f'{const.CB_WATCHLIST}:add_prompt')],
        [InlineKeyboardButton("🗑️ Remove Token", callback_data=f'{const.CB_WATCHLIST}:remove_menu')],
        [InlineKeyboardButton("🔙 Main menu", callback_data=const.CB_BACK_MAIN)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_post_add_watchlist_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard displayed after successfully adding token to watchlist.
    """
    keyboard = [
        [InlineKeyboardButton("➕ Add Another Token", callback_data=f'{const.CB_WATCHLIST}:add_prompt')],
        [InlineKeyboardButton("📋 View list", callback_data=f'{const.CB_WATCHLIST}:view')],
        [InlineKeyboardButton("🔙 Main menu", callback_data=f'{const.CB_BACK_MAIN}')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_remove_token_keyboard(watchlist: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Create keyboard to select token to remove."""
    keyboard = []
    for item in watchlist:
        symbol = item['symbol']
        timeframe = item['timeframe']
        text = f"❌ {symbol} ({timeframe})"
        callback_data = f"{const.CB_WATCHLIST}:remove_confirm:{symbol}:{timeframe}"
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Watchlist", callback_data=f'{const.CB_WATCHLIST}:menu')])
    return InlineKeyboardMarkup(keyboard)
# src/bot/handlers/message_handlers.py
import logging
from telegram import Update
from telegram.ext import CallbackContext

from src.bot.utils.state_manager import get_user_state, reset_user_state
from src.bot import constants as const
from src.bot import keyboards
from .callback_handlers import perform_analysis 

logger = logging.getLogger(__name__)

def handle_message(update: Update, context: CallbackContext):
    """Handle text messages from users."""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    user_state = get_user_state(user_id, context)
    waiting_for = user_state.get(const.STATE_WAITING_FOR)
    
    logger.info(f"User {user_id} sent '{message_text}', state: {waiting_for}")
    
    if waiting_for == const.STATE_CUSTOM_TOKEN:
        handle_custom_token_input(update, context, message_text)
    elif waiting_for == const.STATE_ADD_WATCHLIST:
        handle_watchlist_add_input(update, context, message_text)
    else:
        # Default, guide the user
        update.message.reply_text(
            "🤖 Vui lòng sử dụng các nút hoặc lệnh /start để tương tác.",
            parse_mode='Markdown'
        )

def handle_custom_token_input(update: Update, context: CallbackContext, token_input: str):
    """Handle custom token input from user."""
    user_id = update.effective_user.id
    
    # Normalize input
    symbol = token_input.upper()
    
    # Reset user state
    reset_user_state(user_id, context)
    
    # Send temporary message and call analysis function
    loading_msg = update.message.reply_text(f"Đang tìm kiếm {symbol}...", parse_mode='Markdown')
    perform_analysis(loading_msg, context, symbol, timeframe='4h')

def handle_watchlist_add_input(update: Update, context: CallbackContext, text: str):
    """Handle input to add to watchlist."""
    user_id = update.effective_user.id
    scheduler_service = context.bot_data['scheduler_service']
    
    parts = text.split()
    if len(parts) != 2:
        update.message.reply_text("❌ Sai định dạng. Vui lòng thử lại, ví dụ: `BTC/USDT 4h`", parse_mode='Markdown')
        return

    symbol = parts[0].upper()
    timeframe = parts[1].lower()
    
    # TODO: Validate timeframe (15m, 1h, 4h, 1d, 3d, 1w)
    
    result = scheduler_service.add_to_watchlist(user_id, symbol, timeframe)
    update.message.reply_text(result['message'])
    
    reset_user_state(user_id, context)
    if result['success']:
        keyboard = keyboards.create_post_add_watchlist_keyboard()
        message_text = f"✅ **Thành công!**\n\n{result['message']}\n\nBạn muốn làm gì tiếp theo?"
        update.message.reply_text(message_text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        update.message.reply_text(result['message'])
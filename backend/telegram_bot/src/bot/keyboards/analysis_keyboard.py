from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_analysis_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 15m", callback_data='tf_15m'),
            InlineKeyboardButton("📊 1h", callback_data='tf_1h'),
            InlineKeyboardButton("📊 4h", callback_data='tf_4h')
        ],
        [
            InlineKeyboardButton("📊 1d", callback_data='tf_1d'),
            InlineKeyboardButton("📊 3d", callback_data='tf_3d'),
            InlineKeyboardButton("📊 1w", callback_data='tf_1w')
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data='refresh'),
            InlineKeyboardButton("✏️ Other Token", callback_data='custom_token'),
            InlineKeyboardButton("🏠 Menu", callback_data='start')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
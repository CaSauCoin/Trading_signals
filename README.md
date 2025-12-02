# Trading Signals Telegram Bot

## 📋 Tổng quan

Alpha Signal (Smart Money Concepts) là một bot Telegram tự động phân tích các cặp tiền điện tử sử dụng các khái niệm Smart Money như Order Blocks, Fair Value Gaps, Break of Structure và Liquidity Zones.

## 🚀 Tính năng chính

- 📊 **Phân tích SMC**: Order Blocks, Fair Value Gaps, Break of Structure, Liquidity Zones
- 🎯 **Signals tự động**: Entry/Exit signals dựa trên SMC analysis
- 👁️ **Watchlist**: Theo dõi tối đa 5 tokens với cập nhật mỗi giờ
- ✏️ **Custom tokens**: Hỗ trợ mọi token trên Binance
- 📈 **Multi-timeframe**: 15m, 1h, 4h, 1d, 3d, 1w
- 🔔 **Thông báo tự động**: Cập nhật watchlist theo lịch

## 📁 Cấu trúc thư mục

```
telegram_bot/
├── src/
│   ├── main.py                 # Entry point chính
│   ├── bot/                    # Core bot logic
│   │   ├── trading_bot.py      # Main bot class
│   │   ├── handlers/           # Event handlers
│   │   ├── keyboards/          # UI keyboards
│   │   └── utils/              # Utilities
│   ├── services/               # Business logic
│   ├── models/                 # Data models
│   ├── data/                   # Data storage
│   └── config/                 # Configuration
├── requirements.txt
├── .env.example
└── README.md
```

## 📄 Mô tả từng file

### 🎯 Core Files

#### `src/main.py`
- **Mục đích**: Entry point chính của ứng dụng
- **Chức năng**: Khởi tạo bot, load config, start application
- **Dependencies**: `TradingBot`, `settings`

#### `src/bot/trading_bot.py`
- **Mục đích**: Main bot class, orchestrator chính
- **Chức năng**: 
  - Khởi tạo Telegram Application
  - Register handlers
  - Quản lý state và lifecycle
  - Integration với scheduler
- **Dependencies**: Tất cả handlers, services

### 🎮 Handlers Package (`src/bot/handlers/`)

#### `command_handlers.py`
- **Mục đích**: Xử lý các Telegram commands
- **Commands**: `/start`, `/analysis`, `/help`
- **Chức năng**:
  - Welcome message với main keyboard
  - Direct analysis command
  - Help và instructions

#### `callback_handlers.py`
- **Mục đích**: Xử lý inline keyboard callbacks
- **Callbacks**: `analyze_*`, `watchlist_*`, `tf_*`, etc.
- **Chức năng**:
  - Route callbacks đến appropriate handlers
  - State management cho user interactions
  - Navigation logic

#### `message_handlers.py`
- **Mục đích**: Xử lý text messages từ users
- **Chức năng**:
  - Custom token input processing
  - Watchlist token input
  - Text-based commands
  - Input validation

#### `error_handlers.py`
- **Mục đích**: Global error handling
- **Chức năng**:
  - Catch và log errors
  - User-friendly error messages
  - Retry logic cho network errors
  - Graceful degradation

### ⌨️ Keyboards Package (`src/bot/keyboards/`)

#### `main_keyboard.py`
- **Mục đích**: Main menu keyboards
- **Keyboards**: Welcome menu, pair selection
- **Chức năng**: Navigation và primary actions

#### `analysis_keyboard.py`
- **Mục đích**: Analysis-related keyboards
- **Keyboards**: Timeframe selection, analysis options
- **Chức năng**: Analysis workflow navigation

#### `watchlist_keyboard.py`
- **Mục đích**: Watchlist management keyboards
- **Keyboards**: Add/remove/view watchlist
- **Chức năng**: Watchlist CRUD operations

### 🛠️ Utils Package (`src/bot/utils/`)

#### `state_manager.py`
- **Mục đích**: User state management
- **Chức năng**:
  - Track user conversation state
  - Manage multi-step workflows
  - State persistence

#### `message_formatter.py`
- **Mục đích**: Format analysis results cho Telegram
- **Chức năng**:
  - SMC analysis formatting
  - Emoji và styling
  - Message length management

#### `validators.py`
- **Mục đích**: Input validation utilities
- **Chức năng**:
  - Token symbol validation
  - Binance API validation
  - Format checking

### 🔧 Services Package (`src/services/`)

#### `watchlist_service.py`
- **Mục đích**: Watchlist business logic
- **Chức năng**:
  - CRUD operations cho watchlist
  - File persistence
  - User quota management
  - Batch operations

#### `analysis_service.py`
- **Mục đích**: Analysis business logic
- **Chức năng**:
  - Interface với AdvancedSMC
  - Result processing
  - Caching logic
  - Timeout handling

#### `scheduler_service.py`
- **Mục đích**: Background task scheduling
- **Chức năng**:
  - Hourly watchlist updates
  - Job management
  - Error recovery
  - Batch user notifications

### 📊 Models Package (`src/models/`)

#### `user_state.py`
- **Mục đích**: User state data model
- **Fields**: `user_id`, `waiting_for`, `context`
- **Methods**: State transitions, validation

#### `watchlist_item.py`
- **Mục đích**: Watchlist item data model
- **Fields**: `symbol`, `timeframe`, `added_at`
- **Methods**: Serialization, validation

### 💾 Data Package (`src/data/`)

#### `file_storage.py`
- **Mục đích**: File-based data persistence
- **Chức năng**:
  - JSON file operations
  - Atomic writes
  - Backup và recovery
  - Data migration

### ⚙️ Config Package (`src/config/`)

#### `settings.py`
- **Mục đích**: Application configuration
- **Settings**: Bot token, API keys, limits
- **Environment**: Development/Production configs

#### `logging_config.py`
- **Mục đích**: Logging configuration
- **Features**: Structured logging, rotation, levels

## 🔄 Workflow của Bot

### 1. **Khởi động (Startup)**
```
main.py → TradingBot.__init__() → Register handlers → Start scheduler → Run polling
```

### 2. **User Interaction Flow**

#### **Phân tích cơ bản**:
```
/start → Main keyboard → Select pair → Select timeframe → Analysis → Results
```

#### **Custom token**:
```
/start → Custom token → Input text → Validate → Select timeframe → Analysis → Results
```

#### **Watchlist workflow**:
```
/start → Watchlist menu → Add token → Input + validate → Select timeframe → Save → Auto updates
```

### 3. **Background Jobs**
```
Scheduler (mỗi giờ) → Get all users → Check watchlists → Run analysis → Send updates
```

### 4. **Error Handling Flow**
```
Error occurs → Log error → User notification → Retry logic → Graceful fallback
```

## 🚀 Cài đặt và chạy

### Prerequisites
```bash
pip install python-telegram-bot asyncio apscheduler
```

### Environment Setup
```bash
cp .env.example .env
# Edit .env với bot token
```

### Run
```bash
cd src
python main.py
```

## 📝 Configuration

### Environment Variables
- `BOT_TOKEN`: Telegram bot token
- `LOG_LEVEL`: Logging level (INFO, DEBUG, ERROR)
- `WATCHLIST_LIMIT`: Max watchlist per user (default: 5)
- `UPDATE_INTERVAL`: Update interval in hours (default: 1)

### Bot Commands
- `/start` - Khởi động bot và hiển thị menu
- `/analysis SYMBOL TIMEFRAME` - Phân tích trực tiếp
- `/help` - Hướng dẫn sử dụng

### Supported Timeframes
- `15m`, `1h`, `4h`, `1d`, `3d`, `1w`

## 🔧 Development

### Adding New Features
1. Create appropriate handler trong `handlers/`
2. Add keyboard logic trong `keyboards/`
3. Implement business logic trong `services/`
4. Register handler trong `trading_bot.py`

### Testing
```bash
# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/
```

## 📈 Monitoring

### Logs
- Bot activities: `logs/bot.log`
- Errors: `logs/error.log`
- Analysis: `logs/analysis.log`

### Metrics
- User count
- Analysis requests per hour
- Watchlist usage
- Error rates

## 🛡️ Security

- Input validation tại mọi entry points
- Rate limiting cho analysis requests
- User data encryption
- Secure token storage

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Follow code style guidelines
4. Add tests
5. Submit pull request

## 📞 Support

- Issues: GitHub Issues
- Documentation: Wiki
- Contact: Bot admin commands

---

**Note**: Bot này chỉ để mục đích giáo dục và hỗ trợ phân tích. Không phải lời khuyên đầu tư
import logging
import json
from typing import Dict, List, Any
import os

logger = logging.getLogger(__name__)

# Định nghĩa đường dẫn file và giới hạn watchlist
PERSISTENCE_FILE = 'bot_data.json'
WATCHLIST_LIMIT = 10

class SchedulerService:
    """Quản lý Watchlist và danh sách Subscribers với file persistence."""

    def __init__(self):
        self.db = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Tải dữ liệu từ file JSON khi khởi động."""
        if os.path.exists(PERSISTENCE_FILE):
            try:
                with open(PERSISTENCE_FILE, 'r') as f:
                    data = json.load(f)
                    # Chuyển key của watchlist về int
                    if 'watchlists' in data:
                        data['watchlists'] = {int(k): v for k, v in data['watchlists'].items()}
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Lỗi khi tải dữ liệu từ {PERSISTENCE_FILE}: {e}")
        # Trả về cấu trúc mặc định nếu file chưa có
        return {"watchlists": {}, "scanner_subscribers": []}

    def _save_data(self):
        """Lưu trạng thái hiện tại vào file JSON."""
        try:
            with open(PERSISTENCE_FILE, 'w') as f:
                json.dump(self.db, f, indent=4)
        except IOError as e:
            logger.error(f"Không thể lưu dữ liệu vào {PERSISTENCE_FILE}: {e}")

    # --- Watchlist Methods ---
    def get_user_watchlist(self, user_id: int) -> List[Dict[str, Any]]:
        return self.db.get("watchlists", {}).get(user_id, [])

    def add_to_watchlist(self, user_id: int, symbol: str, timeframe: str) -> Dict[str, Any]:
        watchlist = self.get_user_watchlist(user_id)
        if len(watchlist) >= WATCHLIST_LIMIT:
            return {'success': False, 'message': f'Watchlist đã đầy! (Tối đa {WATCHLIST_LIMIT} token).'}
        if any(item['symbol'] == symbol and item['timeframe'] == timeframe for item in watchlist):
            return {'success': False, 'message': f'Token {symbol} ({timeframe}) đã có trong watchlist.'}
        
        self.db.setdefault("watchlists", {}).setdefault(user_id, []).append({'symbol': symbol, 'timeframe': timeframe})
        self._save_data()
        logger.info(f"User {user_id} đã thêm {symbol} ({timeframe}) vào watchlist.")
        return {'success': True, 'message': f'Đã thêm {symbol} ({timeframe}) vào watchlist.'}

    def remove_from_watchlist(self, user_id: int, symbol: str, timeframe: str) -> bool:
        # ... (logic không đổi, chỉ cần save)
        watchlist = self.get_user_watchlist(user_id)
        item_to_remove = next((item for item in watchlist if item['symbol'] == symbol and item['timeframe'] == timeframe), None)
        if item_to_remove:
            watchlist.remove(item_to_remove)
            self._save_data()
            return True
        return False
        
    def get_all_watchlists(self) -> Dict[int, List[Dict[str, Any]]]:
        return self.db.get("watchlists", {})

    # --- Scanner Subscriber Methods ---
    def get_scanner_subscribers(self) -> List[int]:
        """Lấy danh sách ID của người dùng đã đăng ký."""
        return self.db.get("scanner_subscribers", [])

    def add_scanner_subscriber(self, user_id: int) -> bool:
        """Thêm người dùng vào danh sách đăng ký."""
        subscribers = self.get_scanner_subscribers()
        if user_id not in subscribers:
            subscribers.append(user_id)
            self.db["scanner_subscribers"] = subscribers
            self._save_data()
            logger.info(f"User {user_id} đã đăng ký nhận tin quét thị trường.")
            return True
        return False # Đã đăng ký từ trước

    def remove_scanner_subscriber(self, user_id: int) -> bool:
        """Xóa người dùng khỏi danh sách đăng ký."""
        subscribers = self.get_scanner_subscribers()
        if user_id in subscribers:
            subscribers.remove(user_id)
            self.db["scanner_subscribers"] = subscribers
            self._save_data()
            logger.info(f"User {user_id} đã hủy đăng ký nhận tin quét thị trường.")
            return True
        return False # Không có trong danh sách
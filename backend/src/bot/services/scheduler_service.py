# src/bot/services/scheduler_service.py
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Trong một ứng dụng thực tế, bạn nên dùng database (SQLite, Redis,...) thay vì dict.
# Đây là ví dụ lưu trong bộ nhớ để đơn giản hóa.
WATCHLIST_DB: Dict[int, List[Dict[str, Any]]] = {}
WATCHLIST_LIMIT = 10

class SchedulerService:
    """Quản lý toàn bộ logic và dữ liệu của Watchlist."""

    def get_user_watchlist(self, user_id: int) -> List[Dict[str, Any]]:
        """Lấy watchlist của một người dùng."""
        return WATCHLIST_DB.get(user_id, [])

    def add_to_watchlist(self, user_id: int, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Thêm một token vào watchlist của người dùng."""
        watchlist = self.get_user_watchlist(user_id)
        
        # Kiểm tra giới hạn
        if len(watchlist) >= WATCHLIST_LIMIT:
            return {'success': False, 'message': f'Watchlist đã đầy! (Tối đa {WATCHLIST_LIMIT} token).'}
        
        # Kiểm tra token đã tồn tại chưa
        for item in watchlist:
            if item['symbol'] == symbol and item['timeframe'] == timeframe:
                return {'success': False, 'message': f'Token {symbol} ({timeframe}) đã có trong watchlist.'}
        
        # Thêm mới
        new_item = {'symbol': symbol, 'timeframe': timeframe}
        if user_id not in WATCHLIST_DB:
            WATCHLIST_DB[user_id] = []
        WATCHLIST_DB[user_id].append(new_item)
        
        logger.info(f"User {user_id} đã thêm {symbol} ({timeframe}) vào watchlist.")
        return {'success': True, 'message': f'Đã thêm {symbol} ({timeframe}) vào watchlist.'}

    def remove_from_watchlist(self, user_id: int, symbol: str, timeframe: str) -> bool:
        """Xóa một token khỏi watchlist."""
        watchlist = self.get_user_watchlist(user_id)
        
        item_to_remove = None
        for item in watchlist:
            if item['symbol'] == symbol and item['timeframe'] == timeframe:
                item_to_remove = item
                break
        
        if item_to_remove:
            watchlist.remove(item_to_remove)
            logger.info(f"User {user_id} đã xóa {symbol} ({timeframe}) khỏi watchlist.")
            return True
        return False

    def clear_watchlist(self, user_id: int) -> bool:
        """Xóa toàn bộ watchlist của người dùng."""
        if user_id in WATCHLIST_DB and WATCHLIST_DB[user_id]:
            WATCHLIST_DB[user_id] = []
            logger.info(f"Đã xóa toàn bộ watchlist của user {user_id}.")
            return True
        return False
        
    def get_all_watchlists(self) -> Dict[int, List[Dict[str, Any]]]:
        """Lấy toàn bộ dữ liệu watchlist cho job."""
        return WATCHLIST_DB
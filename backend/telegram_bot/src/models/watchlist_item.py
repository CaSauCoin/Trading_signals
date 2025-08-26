from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class WatchlistItem:
    symbol: str
    timeframe: str = '4h'
    added_at: Optional[datetime] = None
    last_analysis: Optional[datetime] = None
    active: bool = True
    
    def __post_init__(self):
        if self.added_at is None:
            self.added_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WatchlistItem':
        """Create from dictionary"""
        added_at = None
        if data.get('added_at'):
            added_at = datetime.fromisoformat(data['added_at'])
        
        last_analysis = None
        if data.get('last_analysis'):
            last_analysis = datetime.fromisoformat(data['last_analysis'])
        
        return cls(
            symbol=data['symbol'],
            timeframe=data.get('timeframe', '4h'),
            added_at=added_at,
            last_analysis=last_analysis,
            active=data.get('active', True)
        )
    
    def update_analysis_time(self):
        """Update last analysis time"""
        self.last_analysis = datetime.now()
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class UserState:
    user_id: int
    waiting_for: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.context is None:
            self.context = {}
    
    def update_state(self, waiting_for: str, context: Dict[str, Any] = None):
        """Update user state"""
        self.waiting_for = waiting_for
        if context:
            self.context.update(context)
        self.last_updated = datetime.now()
    
    def reset(self):
        """Reset user state"""
        self.waiting_for = None
        self.context = {}
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'waiting_for': self.waiting_for,
            'context': self.context,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserState':
        """Create from dictionary"""
        last_updated = None
        if data.get('last_updated'):
            last_updated = datetime.fromisoformat(data['last_updated'])
        
        return cls(
            user_id=data['user_id'],
            waiting_for=data.get('waiting_for'),
            context=data.get('context', {}),
            last_updated=last_updated
        )
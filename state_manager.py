import redis
import json
import pickle
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class StateStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"

@dataclass
class ConversationState:
    session_id: str
    user_id: str
    message_list: List[tuple]
    current_node: str
    status: StateStatus
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create from dictionary from Redis storage"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['status'] = StateStatus(data['status'])
        return cls(**data)

class StateManager:
    """Scalable state management using Redis"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 default_ttl: int = 3600):
        try:
            self.redis_client = redis.from_url(redis_url)
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis connection established: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Create a fallback in-memory storage for development
            self.redis_client = None
            self._fallback_storage = {}
            logger.warning("Using fallback in-memory storage")
            
        self.default_ttl = default_ttl
        self.session_prefix = "conversation:"
        self.user_prefix = "user:"
        
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"{self.session_prefix}{session_id}"
    
    def _get_user_key(self, user_id: str) -> str:
        """Generate Redis key for user sessions"""
        return f"{self.user_prefix}{user_id}:sessions"
    
    async def create_session(self, session_id: str, user_id: str, 
                           initial_state: Dict[str, Any] = None) -> ConversationState:
        """Create a new conversation session"""
        now = datetime.utcnow()
        
        state = ConversationState(
            session_id=session_id,
            user_id=user_id,
            message_list=initial_state.get('message_list', []) if initial_state else [],
            current_node=initial_state.get('next', 'chatbot') if initial_state else 'chatbot',
            status=StateStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            metadata=initial_state.get('metadata', {}) if initial_state else {}
        )
        
        # Store in Redis or fallback
        if self.redis_client:
            try:
                key = self._get_session_key(session_id)
                self.redis_client.setex(
                    key, 
                    self.default_ttl, 
                    json.dumps(state.to_dict())
                )
                
                # Add to user's session list
                user_key = self._get_user_key(user_id)
                self.redis_client.sadd(user_key, session_id)
                self.redis_client.expire(user_key, self.default_ttl * 24)
            except Exception as e:
                logger.error(f"Redis error in create_session: {e}")
                # Fallback to in-memory
                self._fallback_storage[session_id] = state.to_dict()
        else:
            # Use fallback storage
            self._fallback_storage[session_id] = state.to_dict()
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return state
    
    async def get_session(self, session_id: str) -> Optional[ConversationState]:
        """Retrieve a conversation session"""
        if self.redis_client:
            key = self._get_session_key(session_id)
            data = self.redis_client.get(key)
            
            if data is None:
                return None
                
            try:
                state_dict = json.loads(data)
                return ConversationState.from_dict(state_dict)
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error deserializing session {session_id}: {e}")
                return None
        else:
            # Fallback to in-memory storage
            return self._fallback_storage.get(session_id)
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update a conversation session"""
        state = await self.get_session(session_id)
        if not state:
            return False
            
        # Update fields
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        state.updated_at = datetime.utcnow()
        
        # Store updated state
        if self.redis_client:
            try:
                key = self._get_session_key(session_id)
                self.redis_client.setex(
                    key,
                    self.default_ttl,
                    json.dumps(state.to_dict())
                )
            except Exception as e:
                logger.error(f"Redis error in update_session: {e}")
                # Fallback to in-memory
                self._fallback_storage[session_id] = state.to_dict()
        else:
            # Fallback to in-memory
            self._fallback_storage[session_id] = state.to_dict()
        
        logger.info(f"Updated session {session_id}")
        return True
    
    async def add_message(self, session_id: str, message: tuple) -> bool:
        """Add a message to the conversation"""
        state = await self.get_session(session_id)
        if not state:
            return False
            
        state.message_list.append(message)
        state.updated_at = datetime.utcnow()
        
        # Store updated state
        if self.redis_client:
            try:
                key = self._get_session_key(session_id)
                self.redis_client.setex(
                    key,
                    self.default_ttl,
                    json.dumps(state.to_dict())
                )
            except Exception as e:
                logger.error(f"Redis error in add_message: {e}")
                # Fallback to in-memory
                self._fallback_storage[session_id] = state.to_dict()
        else:
            # Fallback to in-memory
            self._fallback_storage[session_id] = state.to_dict()
        
        return True
    
    async def complete_session(self, session_id: str) -> bool:
        """Mark a session as completed"""
        return await self.update_session(session_id, {
            'status': StateStatus.COMPLETED
        })
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session"""
        if self.redis_client:
            key = self._get_session_key(session_id)
            state = await self.get_session(session_id)
            
            if state:
                # Remove from user's session list
                user_key = self._get_user_key(state.user_id)
                self.redis_client.srem(user_key, session_id)
            
            deleted = self.redis_client.delete(key)
            logger.info(f"Deleted session {session_id}")
            return deleted > 0
        else:
            # Fallback to in-memory
            if session_id in self._fallback_storage:
                del self._fallback_storage[session_id]
                logger.info(f"Deleted session {session_id} from fallback")
                return True
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[ConversationState]:
        """Get all sessions for a user"""
        if self.redis_client:
            user_key = self._get_user_key(user_id)
            session_ids = self.redis_client.smembers(user_key)
            
            sessions = []
            for session_id in session_ids:
                session = await self.get_session(session_id.decode())
                if session:
                    sessions.append(session)
            
            return sessions
        else:
            # Fallback to in-memory
            return [ConversationState(**d) for d in self._fallback_storage.values() if d['user_id'] == user_id]
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        if self.redis_client:
            # This would typically be done by Redis TTL, but we can also
            # manually clean up sessions that are too old
            pattern = f"{self.session_prefix}*"
            keys = self.redis_client.keys(pattern)
            
            cleaned = 0
            for key in keys:
                session_id = key.decode().replace(self.session_prefix, "")
                state = await self.get_session(session_id)
                
                if state and state.updated_at < datetime.utcnow() - timedelta(hours=24):
                    await self.delete_session(session_id)
                    cleaned += 1
            
            logger.info(f"Cleaned up {cleaned} expired sessions")
            return cleaned
        else:
            # Fallback to in-memory
            expired_sessions = []
            for session_id, state_dict in self._fallback_storage.items():
                state = ConversationState(**state_dict)
                if state.updated_at < datetime.utcnow() - timedelta(hours=24):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                await self.delete_session(session_id)
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions from fallback")
            return len(expired_sessions)
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about sessions"""
        if self.redis_client:
            pattern = f"{self.session_prefix}*"
            keys = self.redis_client.keys(pattern)
            
            total_sessions = len(keys)
            active_sessions = 0
            completed_sessions = 0
            error_sessions = 0
            
            for key in keys:
                session_id = key.decode().replace(self.session_prefix, "")
                state = await self.get_session(session_id)
                
                if state:
                    if state.status == StateStatus.ACTIVE:
                        active_sessions += 1
                    elif state.status == StateStatus.COMPLETED:
                        completed_sessions += 1
                    elif state.status == StateStatus.ERROR:
                        error_sessions += 1
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'completed_sessions': completed_sessions,
                'error_sessions': error_sessions
            }
        else:
            # Fallback to in-memory
            active_sessions = 0
            completed_sessions = 0
            error_sessions = 0
            
            for state_dict in self._fallback_storage.values():
                state = ConversationState(**state_dict)
                if state.status == StateStatus.ACTIVE:
                    active_sessions += 1
                elif state.status == StateStatus.COMPLETED:
                    completed_sessions += 1
                elif state.status == StateStatus.ERROR:
                    error_sessions += 1
            
            return {
                'total_sessions': len(self._fallback_storage),
                'active_sessions': active_sessions,
                'completed_sessions': completed_sessions,
                'error_sessions': error_sessions
            }

# Global state manager instance
state_manager = StateManager() 
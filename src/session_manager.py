"""
Session Manager for Standalone MCP Server

Handles session lifecycle and state management for the MCP server.
Uses in-memory storage since this is a dedicated server.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

class Session:
    """Session data structure"""
    
    def __init__(self, session_id: str, user_id: str, context: Optional[Dict[str, Any]] = None):
        self.id = session_id
        self.user_id = user_id
        self.context = context or {}
        self.metadata = {}
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.status = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "status": self.status
        }
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

class SessionManager:
    """Manages MCP sessions"""
    
    def __init__(self, session_timeout_minutes: int = 120):
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background task to clean up expired sessions"""
        async def cleanup_expired_sessions():
            while True:
                try:
                    await asyncio.sleep(300)  # Check every 5 minutes
                    await self._cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Error in session cleanup task: {e}")
        
        self.cleanup_task = asyncio.create_task(cleanup_expired_sessions())
    
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if now - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
    
    async def create_session(self, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new session"""
        session_id = str(uuid4())
        session = Session(session_id, user_id, context)
        self.sessions[session_id] = session
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session.to_dict()
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
            return session.to_dict()
        return None
    
    async def update_session(
        self, 
        session_id: str, 
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update session context and metadata"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        if context is not None:
            session.context.update(context)
        
        if metadata is not None:
            session.metadata.update(metadata)
        
        session.update_activity()
        
        logger.info(f"Updated session {session_id}")
        return session.to_dict()
    
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Terminated session {session_id}")
            return True
        return False
    
    async def get_user_sessions(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all sessions for a user"""
        user_sessions = []
        for session in self.sessions.values():
            if session.user_id == user_id:
                session.update_activity()
                user_sessions.append(session.to_dict())
        return user_sessions
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Session manager cleaned up") 
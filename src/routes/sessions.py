"""
Session endpoints for the MCP HTTP API

Contains all session-related endpoints including creation, retrieval, updates, and termination.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends

from ..models.requests import SessionCreateRequest, SessionUpdateRequest
from ..util.dependencies import get_initialized_server, get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/create")
async def create_session(
    request: SessionCreateRequest,
    _: bool = Depends(get_initialized_server)
):
    """Create a new session"""
    try:
        session_manager = get_session_manager()
        session = await session_manager.create_session(request.user_id, request.context)
        return {"success": True, "data": session}

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    _: bool = Depends(get_initialized_server)
):
    """Get session details"""
    try:
        session_manager = get_session_manager()
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"success": True, "data": session}

    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}")
async def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    _: bool = Depends(get_initialized_server)
):
    """Update session"""
    try:
        session_manager = get_session_manager()
        session = await session_manager.update_session(
            session_id,
            request.context,
            request.metadata
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"success": True, "data": session}

    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def terminate_session(
    session_id: str,
    _: bool = Depends(get_initialized_server)
):
    """Terminate session"""
    try:
        session_manager = get_session_manager()
        success = await session_manager.terminate_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"success": True, "message": "Session terminated"}

    except Exception as e:
        logger.error(f"Error terminating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
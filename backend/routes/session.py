import asyncio
import logging
from enum import Enum
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.agents.orchestrator import orchestrator
from backend.services.learner_store import learner_store
from backend.auth.dependencies import get_current_user, verify_ownership
from backend.events import EventBus, StreamEvent, create_sse_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/session", tags=["session"])


class ResponseType(str, Enum):
    answer = "answer"
    self_assessment = "self_assessment"
    chat = "chat"


class StartSessionRequest(BaseModel):
    learner_id: str
    topic: str | None = None


class RespondRequest(BaseModel):
    response_type: ResponseType
    content: str = Field(default="", max_length=10000)
    confidence: float | None = Field(default=None, ge=1, le=10)


@router.post("/start")
async def start_session(req: StartSessionRequest, user: dict = Depends(get_current_user)):
    await verify_ownership(user, req.learner_id)
    learner = await learner_store.get_learner(req.learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    try:
        logger.info(f"Starting session for learner {req.learner_id}")
        result = await orchestrator.start_session(learner, topic=req.topic)
        return result
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(500, f"Orchestrator error: {str(e)}")


@router.post("/{session_id}/respond")
async def respond(session_id: str, req: RespondRequest, user: dict = Depends(get_current_user)):
    session = orchestrator.get_session(session_id)
    if not session:
        session = await learner_store.get_session(session_id)
        if session:
            orchestrator.active_sessions[session_id] = session
        else:
            raise HTTPException(404, "Session not found")

    await verify_ownership(user, session.learner_id)
    learner = await learner_store.get_learner(session.learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    try:
        logger.info(f"Response in session {session_id}: type={req.response_type}")
        result = await orchestrator.handle_response(
            session_id, learner, req.response_type, req.content, req.confidence
        )
        return result
    except Exception as e:
        logger.error(f"Respond error in session {session_id}: {e}")
        raise HTTPException(500, f"Orchestrator error: {str(e)}")


# ── SSE Streaming endpoints ──────────────────────────────────────────────


@router.post("/start/stream")
async def start_session_stream(req: StartSessionRequest, user: dict = Depends(get_current_user)):
    """Start a learning session with SSE streaming events."""
    await verify_ownership(user, req.learner_id)
    learner = await learner_store.get_learner(req.learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    event_bus = EventBus()

    async def process():
        try:
            await event_bus.emit(StreamEvent.acknowledged())
            result = await orchestrator.start_session(learner, event_bus=event_bus, topic=req.topic)
        except Exception as e:
            logger.error(f"Stream start_session error: {e}")
            await event_bus.emit(StreamEvent.error(str(e)))
            await event_bus.emit(StreamEvent.stream_complete())

    asyncio.create_task(process())
    return create_sse_response(event_bus)


@router.post("/{session_id}/respond/stream")
async def respond_stream(session_id: str, req: RespondRequest, user: dict = Depends(get_current_user)):
    """Respond in a session with SSE streaming events."""
    session = orchestrator.get_session(session_id)
    if not session:
        session = await learner_store.get_session(session_id)
        if session:
            orchestrator.active_sessions[session_id] = session
        else:
            raise HTTPException(404, "Session not found")

    await verify_ownership(user, session.learner_id)
    learner = await learner_store.get_learner(session.learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    event_bus = EventBus()

    async def process():
        try:
            await event_bus.emit(StreamEvent.acknowledged())
            result = await orchestrator.handle_response(
                session_id, learner, req.response_type, req.content, req.confidence,
                event_bus=event_bus,
            )
        except Exception as e:
            logger.error(f"Stream respond error in {session_id}: {e}")
            await event_bus.emit(StreamEvent.error(str(e)))
            await event_bus.emit(StreamEvent.stream_complete())

    asyncio.create_task(process())
    return create_sse_response(event_bus)


@router.get("/{session_id}/events")
async def get_events(session_id: str, user: dict = Depends(get_current_user)):
    session = orchestrator.get_session(session_id)
    if not session:
        session = await learner_store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    await verify_ownership(user, session.learner_id)
    return [e.model_dump() for e in session.events]



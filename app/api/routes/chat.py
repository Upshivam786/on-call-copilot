"""Chat API endpoints with streaming agent support."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import ChatSession, ChatMessage, ChatSessionCreate, ChatSessionRead, ChatMessageRead
from app.agent.loop import AgentLoop
from app.utils.streaming import build_sse_response

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionRead, status_code=201)
async def create_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new chat session."""
    session = ChatSession(
        user_id=session_data.user_id,
        title=session_data.title,
        context={},
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionRead(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        context=session.context,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_sessions(
    user_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
):
    """List chat sessions."""
    stmt = select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(limit).offset(offset)
    if user_id:
        stmt = stmt.where(ChatSession.user_id == user_id)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return [
        ChatSessionRead(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            context=s.context,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
async def get_messages(
    session_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
):
    """Get messages for a session."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return [
        ChatMessageRead(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            citations=m.citations,
            tool_calls=m.tool_calls,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a chat session and its messages."""
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()


class ChatRequest:
    """Request model for chat stream."""
    def __init__(self, query: str, session_id: str | None = None, context: dict = None):
        self.query = query
        self.session_id = session_id
        self.context = context or {}


@router.post("/stream")
async def stream_chat(request: dict):
    """Streaming chat endpoint with agent loop."""
    query = request.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    session_id = request.get("session_id")
    context = request.get("context", {})

    # Initialize agent loop
    agent = AgentLoop()

    # Run streaming
    async def agent_stream():
        async for event in agent.run_stream(
            user_query=query,
            session_id=session_id,
            context=context,
        ):
            yield event

    return build_sse_response(agent_stream())

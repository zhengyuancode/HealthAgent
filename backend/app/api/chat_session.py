import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.services.chat_window_service import ChatWindowService
from app.services.knowledge.deps import get_chat_window_service
from app.db.session import get_db
from app.db.user import User
from app.schemas.chat_db import ChatMessageRead, ChatSessionCreate, ChatSessionRead
from app.services.chat_service import ChatService
from app.repositories.chat_repository import ChatRepository
from app.core.config import Settings
from app.agents.memory_agent import ConversationSummaryAgent
from app.services.orchestration.medical_workflow import build_ConversationSummaryAgent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat-session"])

chat_service = ChatService()


@router.post("/sessions", response_model=ChatSessionRead)
def create_session(
    payload: Optional[ChatSessionCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session_obj = chat_service.create_session(
        db=db,
        user_id=current_user.id,
        title=(payload.title if payload else "新对话"),
    )
    result = ChatSessionRead.model_validate(session_obj)
    result.message_count = 0
    return result


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = chat_service.list_sessions(db=db, user_id=current_user.id)
    result = []
    for session_obj, message_count in rows:
        item = ChatSessionRead.model_validate(session_obj)
        item.message_count = message_count
        result.append(item)
    return result


def _build_recent_rounds(messages, max_rounds: int = 3) -> list[dict]:
    """
    从按时间正序排列的 ChatMessage 列表里，提取最近 max_rounds 轮。
    一轮定义为：user + assistant
    """
    recent_messages = messages[-max_rounds * 2:]
    rounds = []

    i = 0
    while i < len(recent_messages) - 1:
        first = recent_messages[i]
        second = recent_messages[i + 1]

        if first.role == "user" and second.role == "assistant":
            rounds.append({
                "query": first.content,
                "answer": second.content,
                "created_at": str(second.created_at or first.created_at),
            })
            i += 2
        else:
            i += 1

    return rounds[-max_rounds:]

@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
def list_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_window_service: ChatWindowService = Depends(get_chat_window_service)
):
    session_obj = chat_service.get_session(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
    )
    if not session_obj:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = chat_service.list_messages(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
    )
    # 切换 session 后，重建这个 session 对应的 Redis 窗口
    try:
        rounds = _build_recent_rounds(messages, max_rounds=Settings().chat_window_rounds)
        chat_window_service.replace_rounds(
            user_id=current_user.id,
            session_id=session_id,
            rounds=rounds,
        )
        
    except Exception:
        logger.exception("重建 Redis 会话窗口失败, session_id=%s", session_id)
    return [ChatMessageRead.model_validate(m) for m in messages]

@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_window_service: ChatWindowService = Depends(get_chat_window_service),
    conversation_summary_agent: ConversationSummaryAgent = Depends(build_ConversationSummaryAgent),
):
    deleted = ChatRepository.delete_session(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    db.commit()
    redis_cleared = False
    qdrant_cleared = False

    try:
        redis_cleared = chat_window_service.clear_session(
            user_id=current_user.id,
            session_id=session_id,
        )
    except Exception:
        logger.exception(
            "清理 Redis 会话窗口失败, user_id=%s, session_id=%s",
            current_user.id,
            session_id,
        )

    try:
        conversation_summary_agent.delete_session_memories(
            user_id=current_user.id,
            session_id=session_id,
        )
        qdrant_cleared = True
    except Exception:
        logger.exception(
            "清理 Qdrant 会话记忆失败, user_id=%s, session_id=%s",
            current_user.id,
            session_id,
        )
    return {
        "message": "删除成功",
        "session_id": session_id,
        "redis_cleared": redis_cleared,
        "qdrant_cleared": qdrant_cleared,
    }
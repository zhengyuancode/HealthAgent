from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.chat import ChatMessage, ChatSession


class ChatRepository:
    @staticmethod
    def create_session(
        db: Session,
        *,
        user_id: int,
        title: str | None = None,
    ) -> ChatSession:
        session_obj = ChatSession(
            user_id=user_id,
            title=title or "新对话",
        )
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
        return session_obj

    @staticmethod
    def get_session_by_id(
        db: Session,
        *,
        user_id: int,
        session_id: int,
    ) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_sessions_by_user(
        db: Session,
        *,
        user_id: int,
    ) -> list[tuple[ChatSession, int]]:
        stmt = (
            select(
                ChatSession,
                func.count(ChatMessage.id).label("message_count"),
            )
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.last_message_at.desc(), ChatSession.id.desc())
        )
        rows = db.execute(stmt).all()
        return [(row[0], row[1]) for row in rows]

    @staticmethod
    def list_messages_by_session(
        db: Session,
        *,
        user_id: int,
        session_id: int,
    ) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
            )
            .order_by(ChatMessage.id.asc())
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def create_round(
        db: Session,
        *,
        user_id: int,
        session_id: int,
        query: str,
        answer: str,
    ) -> None:
        user_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=query,
        )
        assistant_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=answer,
        )

        db.add(user_msg)
        db.add(assistant_msg)

        session_obj = ChatRepository.get_session_by_id(
            db,
            user_id=user_id,
            session_id=session_id,
        )
        if session_obj:
            session_obj.last_message_at = func.now()
            if not session_obj.title or session_obj.title == "新对话":
                session_obj.title = query[:20] if query else "新对话"

        db.commit()
        
    @staticmethod
    def delete_session(db: Session, *, user_id: int, session_id: int) -> bool:
        session_obj = ChatRepository.get_session_by_id(
            db,
            user_id=user_id,
            session_id=session_id,
        )
        if not session_obj:
            return False

        db.delete(session_obj)
        return True
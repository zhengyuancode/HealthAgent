from sqlalchemy.orm import Session

from app.repositories.chat_repository import ChatRepository


class ChatService:
    @staticmethod
    def create_session(
        db: Session,
        *,
        user_id: int,
        title: str | None = None,
    ):
        return ChatRepository.create_session(
            db,
            user_id=user_id,
            title=title,
        )

    @staticmethod
    def get_session(
        db: Session,
        *,
        user_id: int,
        session_id: int,
    ):
        return ChatRepository.get_session_by_id(
            db,
            user_id=user_id,
            session_id=session_id,
        )

    @staticmethod
    def list_sessions(
        db: Session,
        *,
        user_id: int,
    ):
        return ChatRepository.list_sessions_by_user(
            db,
            user_id=user_id,
        )

    @staticmethod
    def list_messages(
        db: Session,
        *,
        user_id: int,
        session_id: int,
    ):
        return ChatRepository.list_messages_by_session(
            db,
            user_id=user_id,
            session_id=session_id,
        )

    @staticmethod
    def create_round(
        db: Session,
        *,
        user_id: int,
        session_id: int,
        query: str,
        answer: str,
    ):
        return ChatRepository.create_round(
            db,
            user_id=user_id,
            session_id=session_id,
            query=query,
            answer=answer,
        )
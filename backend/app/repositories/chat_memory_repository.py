import json
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.chat import ChatMessage, ChatSession
from app.db.chat_memory import UserProfileMemory


class ChatRepository:
    @staticmethod
    def get_session_by_id(db: Session, *, user_id: int, session_id: int) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_messages_by_session_id(
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
    def get_recent_messages_by_session_id(
        db: Session,
        *,
        user_id: int,
        session_id: int,
        limit: int = 6,
    ) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
            )
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        )
        rows = list(db.execute(stmt).scalars().all())
        rows.reverse()
        return rows

    @staticmethod
    def create_round(
        db: Session,
        *,
        user_id: int,
        session_id: int,
        query: str,
        answer: str,
    ) -> tuple[ChatMessage, ChatMessage]:
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
        db.flush()  # 先拿到 message.id

        session_obj = ChatRepository.get_session_by_id(
            db,
            user_id=user_id,
            session_id=session_id,
        )

        if session_obj:
            session_obj.last_message_at = func.now()
            if not session_obj.title or session_obj.title == "新对话":
                session_obj.title = query[:20] if query else "新对话"

        return user_msg, assistant_msg


    @staticmethod
    def get_user_profile_memory(
        db: Session,
        *,
        user_id: int,
    ) -> UserProfileMemory:
        stmt = select(UserProfileMemory).where(UserProfileMemory.user_id == user_id)
        obj = db.execute(stmt).scalar_one_or_none()

        if not obj:
            obj = UserProfileMemory(user_id=user_id)
            db.add(obj)
            db.flush()

        return obj
    
    @staticmethod
    def get_user_profile_dict(
        db: Session,
        *,
        user_id: int,
    ) -> dict:
        obj = ChatRepository.get_user_profile_memory(db, user_id=user_id)
        db.commit()
        if not obj:
            return {
                "age": "",
                "gender": "",
                "chronic_disease": "",
                "allergy_history": "",
                "long_term_medications": "",
                "pregnancy_planning": "",
                "surgical_history": "",
                "long_term_lifestyle_traits": "",
            }

        return {
            "age": obj.age or "",
            "gender": obj.gender or "",
            "chronic_disease": obj.chronic_disease or "",
            "allergy_history": obj.allergy_history or "",
            "long_term_medications": obj.long_term_medications or "",
            "pregnancy_planning": obj.pregnancy_planning or "",
            "surgical_history": obj.surgical_history or "",
            "long_term_lifestyle_traits": obj.long_term_lifestyle_traits or "",
        }

    @staticmethod
    def upsert_user_profile_memory(
        db: Session,
        *,
        user_id: int,
        profile: dict,
    ) -> UserProfileMemory:
        stmt = select(UserProfileMemory).where(UserProfileMemory.user_id == user_id)
        obj = db.execute(stmt).scalar_one_or_none()

        if not obj:
            obj = UserProfileMemory(user_id=user_id)
            db.add(obj)
            db.flush()

        allowed_fields = [
            "age",
            "gender",
            "chronic_disease",
            "allergy_history",
            "long_term_medications",
            "pregnancy_planning",
            "surgical_history",
            "long_term_lifestyle_traits",
        ]

        for field in allowed_fields:
            value = profile.get(field)
            if value is not None:
                value = str(value).strip()
                if value:
                    setattr(obj, field, value)

        return obj
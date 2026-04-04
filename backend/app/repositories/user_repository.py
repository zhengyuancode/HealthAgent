from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.user import User


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    @staticmethod
    def get_by_phone(db: Session, phone: str) -> User | None:
        stmt = select(User).where(User.phone == phone)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_account(db: Session, account: str) -> User | None:
        stmt = select(User).where(
            or_(User.phone == account, User.username == account)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create(
        db: Session,
        *,
        phone: str,
        username: str,
        password_hash: str,
    ) -> User:
        user = User(
            phone=phone,
            username=username,
            password_hash=password_hash,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_last_login(db: Session, user: User) -> None:
        user.last_login_at = datetime.now()
        db.add(user)
        db.commit()
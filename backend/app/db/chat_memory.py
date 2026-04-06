from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT

from app.db.base import Base


class UserProfileMemory(Base):
    __tablename__ = "user_profile_memory"

    id = Column(MYSQL_BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(
        MYSQL_BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    age = Column(String(50), nullable=True)
    gender = Column(String(20), nullable=True)
    chronic_disease = Column(Text, nullable=True)
    allergy_history = Column(Text, nullable=True)
    long_term_medications = Column(Text, nullable=True)
    pregnancy_planning = Column(String(100), nullable=True)
    surgical_history = Column(Text, nullable=True)
    long_term_lifestyle_traits = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
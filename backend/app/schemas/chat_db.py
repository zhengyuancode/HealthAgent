from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "新对话"


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    message_count: int = 0


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    session_id: int
    role: str
    content: str
    created_at: datetime


class ChatMessageCreate(BaseModel):
    role: str
    content: str
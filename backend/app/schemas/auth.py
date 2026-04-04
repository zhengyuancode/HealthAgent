import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=6, max_length=20)
    username: str = Field(..., min_length=4, max_length=50)
    password: str = Field(..., min_length=8, max_length=64)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6,20}", value):
            raise ValueError("手机号只能包含数字，长度 6-20 位")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]{4,50}", value):
            raise ValueError("账户名只能包含字母、数字、下划线，长度 4-50 位")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("密码首尾不能有空格")
        return value


class LoginRequest(BaseModel):
    account: str = Field(..., min_length=4, max_length=50, description="手机号或账户名")
    password: str = Field(..., min_length=8, max_length=64)


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    username: str
    is_active: bool


class RegisterResponse(BaseModel):
    message: str
    user: UserInfo


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
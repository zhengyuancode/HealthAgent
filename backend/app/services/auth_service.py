from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.utils.security import create_access_token, hash_password, verify_password


class AuthService:
    @staticmethod
    def register(db: Session, data: RegisterRequest):
        if UserRepository.get_by_phone(db, data.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已注册",
            )

        if UserRepository.get_by_username(db, data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="账户名已存在",
            )

        password_hash = hash_password(data.password)

        user = UserRepository.create(
            db,
            phone=data.phone,
            username=data.username,
            password_hash=password_hash,
        )
        return user

    @staticmethod
    def login(db: Session, data: LoginRequest) -> TokenResponse:
        user = UserRepository.get_by_account(db, data.account)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账号或密码错误",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已禁用",
            )

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账号或密码错误",
            )

        UserRepository.update_last_login(db, user)
        token, expires_in = create_access_token(user.id, user.username)

        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user=UserInfo.model_validate(user),
        )
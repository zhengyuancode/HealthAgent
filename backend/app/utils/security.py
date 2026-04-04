from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import Settings


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(user_id: int, username: str) -> tuple[str, int]:
    expire_seconds = Settings().jwt_access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=expire_seconds)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = jwt.encode(
        payload,
        Settings().jwt_secret_key,
        algorithm=Settings().jwt_algorithm,
    )
    return token, expire_seconds


def parse_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            Settings().jwt_secret_key,
            algorithms=[Settings().jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("登录已过期，请重新登录") from exc
    except InvalidTokenError as exc:
        raise TokenInvalidError("无效 token") from exc

    if payload.get("type") != "access":
        raise TokenInvalidError("token 类型错误")

    if not payload.get("sub"):
        raise TokenInvalidError("token 缺少用户标识")

    return payload
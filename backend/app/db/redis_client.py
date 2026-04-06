import redis
from app.core.config import Settings

settings = Settings()

redis_client = redis.Redis(
    host=settings.server_ip,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    decode_responses=True,
)
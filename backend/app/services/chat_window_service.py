import json
from datetime import datetime
from typing import Any


class ChatWindowService:
    def __init__(self, redis_client, max_rounds: int = 3, ttl_seconds: int = 7 * 24 * 3600):
        self.redis = redis_client
        self.max_rounds = max_rounds
        self.ttl_seconds = ttl_seconds

    def _key(self, user_id: int, session_id: int) -> str:
        return f"chat:window:{user_id}:{session_id}"

    def append_round_and_get_evicted(
        self,
        *,
        user_id: int,
        session_id: int,
        query: str,
        answer: str,
    ) -> list[dict[str, Any]]:
        key = self._key(user_id, session_id)

        round_data = {
            "query": query,
            "answer": answer,
            "created_at": datetime.now().isoformat(),
        }

        pipe = self.redis.pipeline()
        pipe.rpush(key, json.dumps(round_data, ensure_ascii=False))
        pipe.expire(key, self.ttl_seconds)
        pipe.execute()

        all_items = self.redis.lrange(key, 0, -1)
        overflow = max(0, len(all_items) - self.max_rounds)

        if overflow <= 0:
            return []

        evicted_raw = all_items[:overflow]
        self.redis.ltrim(key, overflow, -1)

        return [json.loads(x) for x in evicted_raw]

    def get_rounds(
        self,
        *,
        user_id: int,
        session_id: int,
    ) -> list[dict[str, Any]]:
        key = self._key(user_id, session_id)
        rows = self.redis.lrange(key, 0, -1)
        return [json.loads(x) for x in rows]

    def replace_rounds(
        self,
        *,
        user_id: int,
        session_id: int,
        rounds: list[dict[str, Any]],
    ) -> None:
        key = self._key(user_id, session_id)

        pipe = self.redis.pipeline()
        pipe.delete(key)

        for item in rounds[-self.max_rounds:]:
            pipe.rpush(key, json.dumps(item, ensure_ascii=False))

        pipe.expire(key, self.ttl_seconds)
        pipe.execute()
        
    def clear_session(self, *, user_id: int, session_id: int) -> bool:
        key = self._key(user_id, session_id)
        deleted = self.redis.delete(key)
        return bool(deleted)
    
    def clear_all_cache(self) -> bool:
        self.redis.flushdb()
        self.redis.flushall()
        return True
    
# def main():
#     from app.db.redis_client import redis_client
#     chatWindowService = ChatWindowService(redis_client)
#     chatWindowService.clear_all_cache()

# if __name__ == "__main__":
#     main()
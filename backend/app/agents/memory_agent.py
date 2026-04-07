import hashlib
from typing import Any
from app.db.session import SessionLocal
from app.repositories.chat_memory_repository import ChatRepository
from qdrant_client import QdrantClient
from app.core.config import Settings
from datetime import datetime, timedelta, timezone
import uuid
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue
from app.llm.client import EmbeddingClient
import json


class ProfileMemoryAgent:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.db = SessionLocal()

    def run(self, round_messages: list[dict[str, Any]], user_id: int) -> dict[str, Any]:
        profile = ChatRepository.get_user_profile_dict(
            self.db,
            user_id=user_id
        )
        user_prompt = f"""
你是一个用户静态资料提取器。

输入是一轮或多轮对话。
请判断这轮对话里是否包含或潜藏着“对未来有长期价值的用户静态信息”。

只分析出稳定、长期、可靠的信息，例如：
- 年龄(age)
- 性别(gender)
- 慢性病(chronic_disease)
- 过敏史(allergy_history)
- 长期用药(long_term_medications)
- 妊娠/备孕(pregnancy_planning)
- 既往手术史(surgical_history)
- 长期生活方式特征(long_term_lifestyle_traits)

不要提取短期状态、临时情绪、一次性事件。
所有信息应尽可能简洁，简短，不要包含没有意义的信息。
构建json中的field_key时，请使用上述括号中的英文标识，而不是中文描述。
field_value代表对应的信息。

之前的用户画像：
{json.dumps(profile, ensure_ascii=False)}

你需要输出 JSON：
如果没有任何有价值的用户静态信息，则输出：
{json.dumps(profile, ensure_ascii=False)}

如果包含有价值的用户静态信息，更新之前的用户画像，输出：
{{
    "age": "更新后的年龄",
    "gender": "更新后的性别",
    "chronic_disease": "更新后的慢性病",
    "allergy_history": "更新后的过敏史",
    "long_term_medications": "更新后的长期用药",
    "pregnancy_planning": "更新后的妊娠/备孕",
    "surgical_history": "更新后的手术史",
    "long_term_lifestyle_traits": "更新后的长期生活方式特征"
}}

对话内容：
{round_messages}
        """.strip()
        messages = [
            {
                "role": "system",
                "content": "你是一个助手，只返回合法 JSON 对象。"
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        if hasattr(self.llm_client, "chat_json"):
            new_profile_data = self.llm_client.chat_json(messages)
            obj = ChatRepository.upsert_user_profile_memory(
                self.db, 
                user_id=user_id,
                profile=new_profile_data)
            self.db.commit()
            self.db.refresh(obj)


class ConversationSummaryAgent:
    def __init__(self, llm_client, collection_name: str = "conversation_summary"):
        self.llm_client = llm_client
        self.settings = Settings()
        self.qdrant_client = QdrantClient(
            host=self.settings.server_ip,
            port=6333,
            timeout=120.0,
        )
        self.embedder = EmbeddingClient(self.settings)
        self.collection_name = collection_name

    def _extract_vector(self, embedding_result: Any) -> list[float]:
        """
        兼容不同 embedding 返回格式，最终拿到单向量 list[float]
        """
        if isinstance(embedding_result, dict):
            if "embedding" in embedding_result:
                vector = embedding_result["embedding"]
            elif "embeddings" in embedding_result:
                vector = embedding_result["embeddings"]
            else:
                vector = embedding_result
        else:
            vector = embedding_result

        if not isinstance(vector, list) or not vector:
            raise ValueError("embedding 返回结果为空或格式不正确")

        # 防止拿到的是 [[...]] 这种二维结构
        if isinstance(vector[0], list):
            if len(vector) != 1:
                raise ValueError("当前 collection 需要单向量，但拿到了多向量 embeddings")
            vector = vector[0]

        return vector

    def _ensure_collection_exists(self, vector: list[float]) -> None:
        """
        有就不创建，没有就按当前 vector 维度创建
        """
        if self.qdrant_client.collection_exists(self.collection_name):
            return

        vector_size = len(vector)
        if vector_size == 0:
            raise ValueError("vector 为空，无法创建 collection")

        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

    def run(
        self,
        round_messages: list[dict[str, Any]],
        *,
        user_id: int,
        session_id: int,
        expire_days: int = 30,
    ) -> dict[str, Any]:
        user_prompt = f"""
你是一个对话摘要判断器。

输入是一轮或多轮对话。
请判断这轮对话是否值得做长期记忆摘要。

满足以下之一可判定 need_summary=True：
- 对后续问答有持续参考价值
- 包含明确病情背景、既往史、检查结果、核心诉求
- 后续很可能被再次引用

如果只是普通寒暄、很短的泛问、无有效信息，则不需要摘要。

输出 JSON：
{{
  "need_summary": True/False,
  "summary": "如果 need_summary=true, 写一份简洁、稳定、去噪的对话摘要总结；否则给空字符串"
}}

对话内容：
{round_messages}
        """.strip()
        messages = [
            {
                "role": "system",
                "content": "你是一个助手，只返回合法 JSON 对象。"
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
        if not hasattr(self.llm_client, "chat_json"):
            return {
                "need_summary": False,
                "summary": "",
                "stored": False,
            }

        result = self.llm_client.chat_json(messages) or {}
        need_summary = bool(result.get("need_summary"))
        summary = (result.get("summary") or "").strip()
        
        if not need_summary or not summary:
            return {
                "need_summary": False,
                "summary": "",
                "stored": False,
            }

        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(days=expire_days)

        raw_key = f"{user_id}:{session_id}:{summary}"
        summary_hash = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, summary_hash))

        embedding_result = self.embedder.embed_content(
            [summary],
            task="retrieval.passage",
            return_multivector=False,
        )[0]

        vector = self._extract_vector(embedding_result)

        # 先确保集合存在
        self._ensure_collection_exists(vector)

        point = PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "user_id": user_id,
                "session_id": session_id,
                "type": "chat_summary",
                "summary": summary,
                "summary_hash": summary_hash,
                "raw_round": round_messages,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            },
        )

        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

        return {
            "need_summary": True,
            "summary": summary,
            "stored": True,
            "point_id": point_id,
            "summary_hash": summary_hash,
            "expires_at": expires_at.isoformat(),
        }
        
    def delete_session_memories(self, *, user_id: int, session_id: int) -> None:
        if not self.qdrant_client.collection_exists(self.collection_name):
            return

        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id),
                    ),
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id),
                    ),
                    FieldCondition(
                        key="type",
                        match=MatchValue(value="chat_summary"),
                    ),
                ]
            ),
            wait=True,
        )
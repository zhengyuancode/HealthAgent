from fastapi import Depends
from app.core.config import Settings, get_settings
from app.services.knowledge.interfaces import MedicalGraphService
from app.services.knowledge.medical_graph_service import Neo4jMedicalGraphService
from app.services.knowledge.interfaces import PolicyRAGService
from app.services.knowledge.policy_rag_service import LocalPolicyRAGService
from app.services.knowledge.schema_retriever import QdrantSchemaRetriever
from qdrant_client import QdrantClient
from app.llm.client import EmbeddingClient
from app.db.redis_client import redis_client
from app.services.chat_window_service import ChatWindowService


def get_medical_graph_service(
    settings: Settings = Depends(get_settings),
):
    qdrant_client = QdrantClient(
                host=settings.server_ip,
                port=6333,
                timeout=120.0,
            )
    embedder = EmbeddingClient(settings)
    retriever = QdrantSchemaRetriever(client=qdrant_client, embedder=embedder)
    service = Neo4jMedicalGraphService(
        neo4j_uri=settings.neo4j_url,
        username=settings.neo4j_user,
        password=settings.neo4j_password,
        retriver=retriever
    )
    try:
        yield service
    finally:
        service.close()
        
def get_policy_rag_service(
    settings: Settings = Depends(get_settings),
) -> PolicyRAGService:
    embedder = EmbeddingClient(settings)
    return LocalPolicyRAGService(settings, embedder=embedder)

def get_chat_window_service(
        settings: Settings = Depends(get_settings)
    ) -> ChatWindowService:
    return ChatWindowService(redis_client, max_rounds=settings.chat_window_rounds, ttl_seconds=settings.chat_window_ttl_seconds)
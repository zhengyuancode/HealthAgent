from qdrant_client import QdrantClient

from app.services.knowledge.schema_retriever import QdrantSchemaRetriever
from app.graph.get_entity import load_entity_docs_from_neo4j
from app.core.config import Settings
from app.llm.client import EmbeddingClient
import os
import json
from app.services.knowledge.schema_retriever import SchemaDoc

def load_or_build_docs():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(BASE_DIR, "entity_doc.json") 

    if os.path.exists(cache_path):
        print("检测到本地缓存，正在加载 entity_doc.json ...")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = [SchemaDoc(**item) for item in data]

        print(f"缓存加载完成，共 {len(docs)} 条")
    else:
        docs = load_entity_docs_from_neo4j(
            neo4j_uri=settings.neo4j_url,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
        )
    return docs

def build_schema_index(settings: Settings):
    qdrant_client = QdrantClient(
                host=settings.server_ip,
                port=6333,
                timeout=120.0,
            )

    embedder = EmbeddingClient(settings)

    retriever = QdrantSchemaRetriever(
        client=qdrant_client,
        embedder=embedder,
        collection_name="medical_schema",
    )

    docs = load_or_build_docs()

    retriever.rebuild_index(docs, recreate=True)

    print(f"索引构建完成，总文档数: {len(docs)}")


if __name__ == "__main__":
    settings = Settings()
    build_schema_index(settings)
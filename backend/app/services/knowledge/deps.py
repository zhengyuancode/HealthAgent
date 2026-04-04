from fastapi import Depends
from app.core.config import Settings, get_settings
from app.services.knowledge.interfaces import MedicalGraphService
from app.services.knowledge.medical_graph_service import Neo4jMedicalGraphService
from app.services.knowledge.interfaces import PolicyRAGService
from app.services.knowledge.policy_rag_service import LocalPolicyRAGService



def get_medical_graph_service(
    settings: Settings = Depends(get_settings),
):
    service = Neo4jMedicalGraphService(
        neo4j_uri=settings.NEO4J_URI,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD,
    )
    try:
        yield service
    finally:
        service.close()
        
def get_policy_rag_service(
    settings: Settings = Depends(get_settings),
) -> PolicyRAGService:
    return LocalPolicyRAGService(settings)
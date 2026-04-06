from fastapi import Depends

from app.core.config import Settings, get_settings
from app.llm.client import LLMClient
from app.services.intake.query_analyze import QueryAnalyzerService
from app.services.knowledge.interfaces import MedicalGraphService, PolicyRAGService
from app.services.knowledge.deps import (
    get_medical_graph_service,
    get_policy_rag_service,
)

from app.agents.planner_agent import PlannerAgent
from app.agents.medical_agent import MedicalAgent
from app.agents.policy_agent import PolicyRAGAgent
from app.agents.orchestrator import MedicalOrchestrator
from app.agents.memory_agent import ProfileMemoryAgent, ConversationSummaryAgent


def build_medical_orchestrator(
    settings: Settings = Depends(get_settings),
    medical_graph_service: MedicalGraphService = Depends(get_medical_graph_service),
    policy_rag_service: PolicyRAGService = Depends(get_policy_rag_service),
) -> MedicalOrchestrator:
    llm_client = LLMClient(settings)

    analyzer = QueryAnalyzerService()
    planner = PlannerAgent(llm_client=llm_client)

    medical_agent = MedicalAgent(
        llm_client=llm_client,
        graph_service=medical_graph_service,
    )
    policy_rag_agent = PolicyRAGAgent(
        llm_client=llm_client,
        policy_rag_service=policy_rag_service,
    )

    return MedicalOrchestrator(
        analyzer=analyzer,
        planner=planner,
        medical_agent=medical_agent,
        policy_rag_agent=policy_rag_agent,
        llm_client=llm_client,
    )
    
def build_ProfileMemoryAgent(
    settings: Settings = Depends(get_settings),
) -> ProfileMemoryAgent:
    llm_client = LLMClient(settings)
    return ProfileMemoryAgent(llm_client=llm_client)

def build_ConversationSummaryAgent(
    settings: Settings = Depends(get_settings),
) -> ConversationSummaryAgent:
    llm_client = LLMClient(settings)
    return ConversationSummaryAgent(llm_client=llm_client)

    
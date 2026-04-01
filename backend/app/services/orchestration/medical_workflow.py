from app.core.config import Settings
from app.llm.client import LLMClient
from backend.app.services.intake.query_analyze import QueryAnalyzerService
from app.services.knowledge.interfaces import MedicalGraphService, PolicyRAGService

from app.agents.planner_agent import PlannerAgent
from app.agents.medical_agent import MedicalAgent
from app.agents.policy_agent import PolicyRAGAgent
from app.agents.safety_agent import SafetyAgent
from app.agents.orchestrator import MedicalOrchestrator


def build_medical_orchestrator(
    settings: Settings,
    medical_graph_service: MedicalGraphService,
    policy_rag_service: PolicyRAGService,
) -> MedicalOrchestrator:
    llm_client = LLMClient(settings)

    analyzer = QueryAnalyzerService()
    planner = PlannerAgent(llm_client=llm_client)

    medical_agent = MedicalAgent(
        llm_client=llm_client,
        medical_graph_service=medical_graph_service,
    )
    policy_rag_agent = PolicyRAGAgent(
        llm_client=llm_client,
        policy_rag_service=policy_rag_service,
    )

    # safety_agent = SafetyAgent()

    return MedicalOrchestrator(
        analyzer=analyzer,
        planner=planner,
        graph_agent=medical_agent,
        policy_rag_agent=policy_rag_agent,
        # safety_agent=safety_agent,
        llm_client=llm_client
    )
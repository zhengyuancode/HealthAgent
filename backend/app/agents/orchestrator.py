from typing import Any, Dict, List

from app.schemas.agent import (
    AnalysisResult,
    ExecutionPlan,
    FinalResponse,
    RagExecutionOutput,
    GraphExecutionOutput
)
from backend.app.services.intake.query_analyze import QueryAnalyzerService
from app.agents.planner_agent import PlannerAgent
from app.agents.medical_agent import MedicalAgent
from app.agents.policy_agent import PolicyRAGAgent
from app.agents.safety_agent import SafetyAgent
from app.llm.client import LLMClient


class MedicalOrchestrator:
    def __init__(
        self,
        analyzer: QueryAnalyzerService,
        planner: PlannerAgent,
        medical_agent: MedicalAgent,
        policy_rag_agent: PolicyRAGAgent,
        # safety_agent: SafetyAgent,
        llm_client: LLMClient
    ):
        self.analyzer = analyzer
        self.planner = planner
        self.medical_agent = medical_agent
        self.policy_rag_agent = policy_rag_agent
        # self.safety_agent = safety_agent
        self.llm_client = llm_client

    def run(self, query: str) -> FinalResponse:
        analysis = self.analyzer.analyze(query)
        plan = self.planner.plan(analysis)

        shared_memory: Dict[str, Any] = {}
        rag_results: List[RagExecutionOutput] = []
        graph_results: List[GraphExecutionOutput] = []

        for task in plan.tasks:
            result = self._run_task(task)
            
            if task.knowledge_route == "policy_rag":
                rag_results.append(result)
            elif task.knowledge_route == "medical_graph":
                graph_results.append(result)
            
            shared_memory[task.task_id] = result.model_dump()

        answer = self._synthesize(query, analysis, plan, rag_results, graph_results)
        # safe_answer, warnings = self.safety_agent.review(
        #     analysis=analysis,
        #     answer=answer,
        #     task_results=task_results,
        # )


# class FinalResponse(BaseModel):
#     answer: str
#     risk_level: RiskLevel
#     analysis: AnalysisResult
#     plan: ExecutionPlan
#     rag_results: List[RagExecutionOutput] = Field(default_factory=list)
#     graph_results: List[GraphExecutionOutput] = Field(default_factory=list)
        return FinalResponse(
            answer=answer,
            risk_level=analysis.risk_level,
            analysis=analysis,
            plan=plan,
            rag_results=rag_results,
            graph_results=graph_results
        )

    def _run_task(
        self,
        task
    ):
        if task.knowledge_route == "medical":
            return self.medical_agent.run(task)

        if task.knowledge_route == "policy_rag":
            return self.policy_rag_agent.run(task)


    def _synthesize(
        self,
        query: str,
        analysis: AnalysisResult,
        plan: ExecutionPlan,
        rag_results: List[RagExecutionOutput],
        graph_results: List[GraphExecutionOutput]
    ) -> str:

        success_results = []
        for result in rag_results + graph_results:
            if result.status == "success":
                success_results.append(result)

        if len(success_results) == 0:
            return "当前没有获得足够的知识库结果，建议补充更具体的问题描述后再试。"

        parts = []
        for idx, result in enumerate(success_results, start=1):
            parts.append(f"{idx}. {result.summary}")

        answer = "根据你的问题，我整理如下：\n" + "\n".join(parts)


        return answer

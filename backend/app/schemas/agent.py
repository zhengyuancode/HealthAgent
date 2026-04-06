from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field


SemanticType = Literal[
    "symptom_consult",
    "drug_consult",
    "department_recommend",
    "policy_consult",
    "complication_consult",
    "producer_consult",
    "general",
    "mixed",
]

KnowledgeRoute = Literal["medical_graph", "policy_rag", "memory", "none"]
RiskLevel = Literal["low", "medium", "high"]
RunStatus = Literal["success", "failed", "skipped"]


class AnalysisResult(BaseModel):
    raw_query: str
    normalized_query: str
    entities: List[str] = Field(default_factory=list)
    candidate_semantics: List[SemanticType] = Field(default_factory=list)
    risk_level: RiskLevel = "low"
    risk_signals: List[str] = Field(default_factory=list)
    special_population: List[str] = Field(default_factory=list)
    rule_signals: Dict[str, List[str]] = Field(default_factory=dict)


class TaskPlan(BaseModel):
    task_id: str
    semantic_type: SemanticType
    knowledge_route: KnowledgeRoute
    question: str
    entities: List[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    mode: Literal["single", "composite"] = "single"
    tasks: List[TaskPlan] = Field(default_factory=list)
    planner_source: Literal["llm", "fallback"] = "fallback"


class RagExecutionOutput(BaseModel):
    task: TaskPlan
    summary: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    status: str

class GraphExecutionOutput(BaseModel):
    task: TaskPlan
    summary: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    status: str

class NoneExecutionOutput(BaseModel):
    task: TaskPlan
    summary: str
    status: str
    
class MemoryExecutionOutput(BaseModel):
    task: TaskPlan
    summary: str
    status: str

class FinalResponse(BaseModel):
    answer: str
    risk_level: RiskLevel
    # warnings: List[str] = Field(default_factory=list)
    analysis: AnalysisResult
    plan: ExecutionPlan
    rag_results: List[RagExecutionOutput] = Field(default_factory=list)
    graph_results: List[GraphExecutionOutput] = Field(default_factory=list)
from typing import Any, Dict, List

from app.schemas.agent import AnalysisResult, ExecutionPlan, TaskPlan


class PlannerAgent:
    name = "planner_agent"
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def plan(self, analysis: AnalysisResult) -> ExecutionPlan:
        if self.llm_client is None:
            return self._fallback_plan(analysis)

        try:
            plan_data = self._plan_by_llm(analysis)
            return self._sanitize_plan(plan_data, analysis)
        except Exception:
            return self._fallback_plan(analysis)

    def _plan_by_llm(self, analysis: AnalysisResult) -> Dict[str, Any]:
        system_prompt = """
你是医疗问答系统中的 Planner Agent。
你的任务是做子问题拆解和知识路由，不直接回答用户问题。
用户原问题不可分时，只返回一个子问题即用户原问题

系统只有两类知识源：
1. medical_graph：医疗知识图谱
2. policy_rag：政策类向量检索

输出 JSON，不要输出任何额外文字。
"""

        user_prompt = f"""
用户原问题：
{analysis.raw_query}

前置分析结果（由预定义词表构建，可能存在未知词汇导致分析结果有缺陷，仅供参考）：
{analysis.model_dump_json(indent=2, ensure_ascii=False)}

请输出 JSON，格式如下：
{{
  "mode": "single（只采用一个知识源） 或 composite（采用多个知识源）",
  "tasks": [
    {{
      "semantic_type": "symptom_consult 或 drug_consult 或 department_recommend 或 policy_consult 或 general",
      "knowledge_route": "medical_graph 或 policy_rag",
      "question": "子问题1",
      "entities": ["子问题1中实体1", "子问题1中实体2", ...]
    }},
    {{
      "semantic_type": "symptom_consult 或 drug_consult 或 department_recommend 或 policy_consult 或 general",
      "knowledge_route": "medical_graph 或 policy_rag",
      "question": "子问题2",
      "entities": ["子问题2中实体1", "子问题2中实体2", ...]
    }},
    ...
  ]
}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.llm_client.chat_json(messages=messages, thinking=False)
    
    def _determine_mode(self, tasks: List[TaskPlan]) -> str:
        """判断执行模式：如果多个任务有不同的route则为composite，否则为single"""
        if len(tasks) <= 1:
            return "single"
        
        # 检查是否有不同的route
        routes = {task.knowledge_route for task in tasks}
        return "composite" if len(routes) > 1 else "single"
    
    def _sanitize_plan(self, plan_data: Dict[str, Any], analysis: AnalysisResult) -> ExecutionPlan:
        tasks: List[TaskPlan] = []
        for idx, item in enumerate(plan_data.get("tasks", []), start=1):
            tasks.append(
                TaskPlan(
                    task_id=item.get(f"task_{idx}"),
                    semantic_type=item.get("semantic_type", "general"),
                    knowledge_route=item.get("knowledge_route", "none"),
                    question=item.get("question", analysis.raw_query),
                    entities=item.get("entities", analysis.entities)
                )
            )

        if not tasks:
            return self._fallback_plan(analysis)

        return ExecutionPlan(
            mode=plan_data.get("mode") or self._determine_mode(tasks),
            tasks=tasks,
            planner_source="llm",
        )

    
    def _fallback_plan(self, analysis: AnalysisResult) -> ExecutionPlan:
        semantics = analysis.candidate_semantics or ["general"]

        # 去掉 general 干扰
        semantics = [s for s in semantics if s != "general"] or ["general"]

        tasks = []
        for idx, semantic in enumerate(semantics, start=1):
            if semantic == "policy_consult":
                route = "policy_rag"
            else:
                route = "medical_graph"

            tasks.append(
                TaskPlan(
                    task_id=f"task_{idx}",
                    semantic_type=semantic,
                    knowledge_route=route,
                    question=analysis.raw_query,
                    entities=analysis.entities
                )
            )

        return ExecutionPlan(
            mode=self._determine_mode(tasks),
            planner_source="fallback",
            tasks=tasks,
        )
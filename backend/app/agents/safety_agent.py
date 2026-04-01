from typing import List

from app.schemas.agent import AnalysisResult, TaskExecutionResult


class SafetyAgent:
    """
    最终输出安全审查：
    - 高风险加警示
    - 特殊人群加谨慎提示
    - 对措辞做最后兜底
    """

    def review(
        self,
        analysis: AnalysisResult,
        answer: str,
        task_results: List[TaskExecutionResult],
    ) -> tuple[str, List[str]]:
        warnings: List[str] = []

        if analysis.risk_level == "high":
            warnings.append("检测到高风险症状或描述，建议尽快线下就医或急诊评估。")

        if analysis.risk_level == "medium":
            warnings.append("当前问题包含一定风险，请结合实际症状变化，必要时尽快就医。")

        if analysis.special_population:
            warnings.append("涉及特殊人群，用药和处理建议需更加谨慎，建议优先咨询医生。")

        if any(r.risk_flags for r in task_results):
            warnings.append("部分结论基于知识库推理与检索结果，仅作为辅助参考，不能替代医生面诊。")

        safe_answer = self._soften_answer(answer)

        if warnings:
            prefix = "\n".join([f"【安全提示】{w}" for w in warnings])
            safe_answer = f"{prefix}\n\n{safe_answer}"

        return safe_answer, warnings

    def _soften_answer(self, answer: str) -> str:
        """
        很轻量的保守化处理。
        这里只做最低限度兜底，不做复杂改写。
        """
        replacements = {
            "一定是": "有可能是",
            "就是": "可能与…有关",
            "肯定是": "不能排除",
            "必须吃": "是否使用需结合具体情况判断",
            "不用去医院": "若症状持续或加重，仍建议就医评估",
        }

        safe_text = answer
        for src, dst in replacements.items():
            safe_text = safe_text.replace(src, dst)

        return safe_text
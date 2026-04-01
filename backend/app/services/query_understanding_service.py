from typing import Any, Dict, List, Optional

import re
from app.core.config import Settings
from app.llm.client import LLMClient
from app.core.constants import (
    INTENT_SYMPTOM,
    INTENT_DRUG,
    INTENT_POLICY,
    INTENT_DEPARTMENT,
    INTENT_GENERAL,
    INTENT_LIST,
    INTENT_PRIORITY,
    RISK_LOW,
    RISK_MEDIUM,
    RISK_HIGH,
    SYMPTOM_TERMS,
    DRUG_TERMS,
    DRUG_QUERY_TERMS,
    POLICY_TERMS,
    DEPARTMENT_QUERY_TERMS,
    HIGH_RISK_TERMS,
    MEDIUM_RISK_TERMS,
    SPECIAL_POPULATION_TERMS,
    INTENT_NEED_GRAPH,
    INTENT_NEED_RAG,
    ENTITY_TERM_POOL,
    UNCERTAIN_INTENT,
)


class QueryUnderstandingService:
    """
    第一版用户问题理解服务：
    - 规则优先
    - LLM兜底
    - 输出统一结构
    """

    def __init__(self, settings: Settings, use_llm_fallback: bool = True):
        self.settings = settings
        self.use_llm_fallback = use_llm_fallback
        self.llm_client = LLMClient(settings) if use_llm_fallback else None

    def understand(self, query: str) -> Dict[str, Any]:
        text = self._normalize_text(query)

        rule_result = self._understand_by_rules(text)

        if self._is_rule_result_confident(rule_result):
            return rule_result

        if self.use_llm_fallback and self.llm_client is not None:
            try:
                llm_result = self._understand_by_llm(text, rule_result)
                return self._merge_result(rule_result, llm_result)
            except Exception:
                # LLM失败时直接回退到规则结果
                return self._finalize_uncertain_rule_result(rule_result)

        return self._finalize_uncertain_rule_result(rule_result)

    def _understand_by_rules(self, text: str) -> Dict[str, Any]:
        entities = self._extract_entities(text)
        candidate_intents = self._collect_candidate_intents(text)
        intent = self._classify_intent(candidate_intents)
        risk_level = self._assess_risk(text, intent)
        need_graph = self._decide_graph(intent)
        need_rag = self._decide_rag(intent)

        return {
            "intent": intent,
            "entities": entities,
            "risk_level": risk_level,
            "need_graph": need_graph,
            "need_rag": need_rag,
            "_meta": {
                "source": "rule",
                "candidate_intents": candidate_intents,
                "matched_entity_count": len(entities),
            }
        }

    def _fullwidth_to_halfwidth(self, text: str) -> str:
        result = ""
        for char in text:
            code = ord(char)
            if code == 0x3000:
                code = 32
            elif 0xFF01 <= code <= 0xFF5E:
                code -= 0xFEE0
            result += chr(code)
        return result

    def _normalize_text(self, text: str) -> str:
        text = text.strip().lower()

        # 去掉多余空格（中文一般不用，但防御）
        text = re.sub(r"\s+", "", text)

        # 全角转半角（很重要）
        text = self._fullwidth_to_halfwidth(text)

        return text

    def _extract_entities(self, text: str) -> List[str]:
        entities: List[str] = []
        for term in ENTITY_TERM_POOL:
            if term in text and term not in entities:
                entities.append(term)
        return entities

    def _collect_candidate_intents(self, text: str) -> List[str]:
        candidates: List[str] = []

        if any(term in text for term in DEPARTMENT_QUERY_TERMS):
            candidates.append(INTENT_DEPARTMENT)

        if any(term in text for term in POLICY_TERMS):
            candidates.append(INTENT_POLICY)

        if any(term in text for term in DRUG_TERMS) or any(term in text for term in DRUG_QUERY_TERMS):
            candidates.append(INTENT_DRUG)

        if any(term in text for term in SYMPTOM_TERMS):
            candidates.append(INTENT_SYMPTOM)

        if not candidates:
            candidates.append(INTENT_GENERAL)

        return candidates

    def _classify_intent(self, candidate_intents: List[str]) -> str:
        if not candidate_intents:
            return UNCERTAIN_INTENT

        if len(candidate_intents) == 1:
            return candidate_intents[0]

        # 多意图时按优先级选主意图
        return min(candidate_intents, key=lambda x: INTENT_PRIORITY.get(x, 999))

    def _assess_risk(self, text: str, intent: str) -> str:
        if any(term in text for term in HIGH_RISK_TERMS):
            return RISK_HIGH

        if any(term in text for term in SPECIAL_POPULATION_TERMS):
            if intent in {INTENT_DRUG, INTENT_SYMPTOM, INTENT_DEPARTMENT}:
                return RISK_MEDIUM

        if any(term in text for term in MEDIUM_RISK_TERMS):
            return RISK_MEDIUM

        return RISK_LOW

    def _decide_graph(self, intent: str) -> bool:
        return INTENT_NEED_GRAPH.get(intent, False)

    def _decide_rag(self, intent: str) -> bool:
        return INTENT_NEED_RAG.get(intent, False)

    def _is_rule_result_confident(self, rule_result: Dict[str, Any]) -> bool:
        intent = rule_result.get("intent")
        meta = rule_result.get("_meta", {})
        candidate_intents = meta.get("candidate_intents", [])
        matched_entity_count = meta.get("matched_entity_count", 0)

        # 规则明确情况：
        # 1. 只有一个候选意图，且不是general
        # 2. 或者命中实体比较多
        if intent != INTENT_GENERAL and len(candidate_intents) == 1:
            return True

        if intent != INTENT_GENERAL and matched_entity_count >= 2:
            return True

        return False

    def _finalize_uncertain_rule_result(self, rule_result: Dict[str, Any]) -> Dict[str, Any]:
        result = {k: v for k, v in rule_result.items() if k != "_meta"}
        return result

    def _understand_by_llm(self, text: str, rule_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        当规则不确定时，调用LLM做补充判断。
        注意：system/user里明确写json，避免json_object模式报错。
        """

        candidate_intents = rule_result.get("_meta", {}).get("candidate_intents", [])
        extracted_entities = rule_result.get("entities", [])

        system_prompt = f"""
你是医疗问答系统中的“用户问题理解器”。

请你根据用户问题，输出一个 JSON 对象，不要输出任何额外文字。
JSON 必须包含以下字段：
- intent: 只能从 {INTENT_LIST} 中选择一个
- entities: 字符串数组，提取问题中的关键实体
- risk_level: 只能是 "{RISK_LOW}" / "{RISK_MEDIUM}" / "{RISK_HIGH}"
- need_graph: 布尔值
- need_rag: 布尔值

判断规则：
1. symptom_consult：用户在咨询症状、病情、原因、是否严重等
2. drug_consult：用户在咨询药物、用药、副作用、禁忌、剂量等
3. policy_consult：用户在咨询医保、报销、医院政策、费用政策等
4. department_recommend：用户在问挂什么科、看什么科、去哪个科室
5. general：以上都不明显时使用

输出必须是合法 JSON。
"""

        user_prompt = f"""
请用 JSON 返回结果。

用户原问题：
{text}

规则初步候选意图：
{candidate_intents}

规则已提取实体：
{extracted_entities}

请输出最终 JSON。
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        llm_result = self.llm_client.chat_json(messages=messages, thinking=False)

        return self._sanitize_llm_result(llm_result, fallback=rule_result)

    def _sanitize_llm_result(
        self,
        llm_result: Dict[str, Any],
        fallback: Dict[str, Any]
    ) -> Dict[str, Any]:
        intent = llm_result.get("intent", fallback.get("intent", INTENT_GENERAL))
        if intent not in INTENT_LIST:
            intent = fallback.get("intent", INTENT_GENERAL)

        entities = llm_result.get("entities", fallback.get("entities", []))
        if not isinstance(entities, list):
            entities = fallback.get("entities", [])

        risk_level = llm_result.get("risk_level", fallback.get("risk_level", RISK_LOW))
        if risk_level not in {RISK_LOW, RISK_MEDIUM, RISK_HIGH}:
            risk_level = fallback.get("risk_level", RISK_LOW)

        need_graph = llm_result.get("need_graph", INTENT_NEED_GRAPH.get(intent, False))
        if not isinstance(need_graph, bool):
            need_graph = INTENT_NEED_GRAPH.get(intent, False)

        need_rag = llm_result.get("need_rag", INTENT_NEED_RAG.get(intent, False))
        if not isinstance(need_rag, bool):
            need_rag = INTENT_NEED_RAG.get(intent, False)

        return {
            "intent": intent,
            "entities": entities,
            "risk_level": risk_level,
            "need_graph": need_graph,
            "need_rag": need_rag,
            "_meta": {
                "source": "llm"
            }
        }

    def _merge_result(
        self,
        rule_result: Dict[str, Any],
        llm_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并策略：
        - intent 以 LLM 为主
        - entities 合并去重
        - risk 取更高等级
        - graph/rag 只要有一个建议查，就设为 True
        """
        merged_entities = []
        for item in rule_result.get("entities", []) + llm_result.get("entities", []):
            if item not in merged_entities:
                merged_entities.append(item)

        final_intent = llm_result.get("intent", rule_result.get("intent", INTENT_GENERAL))

        final_risk = self._max_risk(
            rule_result.get("risk_level", RISK_LOW),
            llm_result.get("risk_level", RISK_LOW)
        )

        final_result = {
            "intent": final_intent,
            "entities": merged_entities,
            "risk_level": final_risk,
            "need_graph": (
                rule_result.get("need_graph", False) or
                llm_result.get("need_graph", False)
            ),
            "need_rag": (
                rule_result.get("need_rag", False) or
                llm_result.get("need_rag", False)
            ),
        }
        return final_result

    def _max_risk(self, a: str, b: str) -> str:
        order = {
            RISK_LOW: 1,
            RISK_MEDIUM: 2,
            RISK_HIGH: 3,
        }
        return a if order.get(a, 0) >= order.get(b, 0) else b
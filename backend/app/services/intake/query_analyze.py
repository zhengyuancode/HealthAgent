from typing import List
import re
from app.schemas.agent import AnalysisResult
from app.core.constants import (
    SYMPTOM_TERMS,
    DRUG_TERMS,
    PRODUCER_TERMS,
    COMPLICATION_TERMS,
    DRUG_QUERY_TERMS,
    POLICY_TERMS,
    DEPARTMENT_QUERY_TERMS,
    HIGH_RISK_TERMS,
    MEDIUM_RISK_TERMS,
    SPECIAL_POPULATION_TERMS,
    ENTITY_TERM_POOL,
)


class QueryAnalyzerService:
    """
    只做分析，不做最终单意图裁决：
    - normalize
    - extract entities
    - collect candidate domains
    - detect risk
    - detect composite query
    """

    def analyze(self, query: str) -> AnalysisResult:
        text = self._normalize_text(query)

        entities = self._extract_entities(text)
        candidate_domains = self._collect_candidate_domains(text)
        risk_level, risk_signals = self._assess_risk(text, candidate_domains)
        special_population = self._extract_special_population(text)

        rule_signals = {
            "matched_symptoms": [t for t in SYMPTOM_TERMS if t in text],
            "matched_drugs": [t for t in DRUG_TERMS if t in text],
            "matched_policy_terms": [t for t in POLICY_TERMS if t in text],
            "matched_department_terms": [t for t in DEPARTMENT_QUERY_TERMS if t in text],
            "matched_special_population": special_population,
        }

        return AnalysisResult(
            raw_query=query,
            normalized_query=text,
            entities=entities,
            candidate_semantics=candidate_domains,
            risk_level=risk_level,
            risk_signals=risk_signals,
            special_population=special_population,
            rule_signals=rule_signals
        )

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
        text = re.sub(r"\s+", "", text)
        text = self._fullwidth_to_halfwidth(text)
        return text

    def _extract_entities(self, text: str) -> List[str]:
        entities: List[str] = []
        for term in ENTITY_TERM_POOL:
            if term in text and term not in entities:
                entities.append(term)
        return entities

    def _collect_candidate_domains(self, text: str) -> List[str]:
        domains: List[str] = []

        if any(term in text for term in SYMPTOM_TERMS):
            domains.append("symptom_consult")

        if any(term in text for term in DRUG_TERMS) or any(term in text for term in DRUG_QUERY_TERMS):
            domains.append("drug_consult")

        if any(term in text for term in DEPARTMENT_QUERY_TERMS):
            domains.append("department_recommend")

        if any(term in text for term in POLICY_TERMS):
            domains.append("policy_consult")
        
        if any(term in text for term in PRODUCER_TERMS):
            domains.append("producer_consult")
            
        if any(term in text for term in COMPLICATION_TERMS):
            domains.append("complication_consult")

        if not domains:
            domains.append("general")

        # 去重保序
        deduped: List[str] = []
        for item in domains:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _extract_special_population(self, text: str) -> List[str]:
        matched: List[str] = []
        for term in SPECIAL_POPULATION_TERMS:
            if term in text and term not in matched:
                matched.append(term)
        return matched

    def _assess_risk(self, text: str, candidate_domains: List[str]) -> tuple[str, List[str]]:
        risk_signals: List[str] = []

        for term in HIGH_RISK_TERMS:
            if term in text:
                risk_signals.append(term)
        if risk_signals:
            return "high", risk_signals

        for term in MEDIUM_RISK_TERMS:
            if term in text:
                risk_signals.append(term)

        if self._extract_special_population(text) and any(
            d in candidate_domains for d in ["symptom_consult", "drug_consult", "department_recommend"]
        ):
            risk_signals.append("special_population")

        if risk_signals:
            return "medium", risk_signals

        return "low", risk_signals

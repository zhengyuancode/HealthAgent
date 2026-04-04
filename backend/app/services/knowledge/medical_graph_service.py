from typing import Any, Dict, List, Optional, Set
from neo4j import GraphDatabase

from app.services.knowledge.interfaces import MedicalGraphService
from app.services.knowledge.schema_retriever import QdrantSchemaRetriever


INTENT_SYMPTOM = "symptom_consult"
INTENT_DRUG = "drug_consult"
INTENT_PRODUCER = "producer_consult"
INTENT_COMPLICATION = "complication_consult"
INTENT_DEPARTMENT = "department_recommend"

def _truncate_text(value: Any, max_len: int = 120) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."


def _normalize_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if x is not None and str(x).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        return [text]
    return [str(value).strip()]

class Neo4jMedicalGraphService(MedicalGraphService):
    def __init__(self, neo4j_uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def query(
        self,
        query: str,
        retriever: QdrantSchemaRetriever,
        entities: Optional[List[str]] = None,
        semantic_type: str = "",
        topk: int = 5,
        topn: int = 5
    ) -> Dict[str, Any]:
        entities = entities or []

        emb_entities = self._get_emb_entities(retriever, query, topk, topn)
        candidates = self._merge_candidates(entities, emb_entities)
        graph_entities = self._match_graph_entities(candidates)
        entity_details = self._get_entity_details(
            graph_entities,
            max_desc_len=120,
            max_cause_len=120,
            max_prevent_len=120,
        )
        graph_results = self._query_by_intent(graph_entities, semantic_type)

        return {
            "query": query,
            "semantic_type": semantic_type,
            "rule_entities": entities,
            "embedding_entities": emb_entities,
            "graph_entities": graph_entities,
            "entity_details": entity_details,
            "graph_results": graph_results,
            "stats": {
                "rule_entity_count": len(entities),
                "embedding_entity_count": len(emb_entities),
                "matched_entity_count": len(graph_entities),
                "entity_detail_count": len(entity_details),
                "result_count": len(graph_results),
            }
        }
        

    def _get_entity_details(
        self,
        graph_entities: List[Dict[str, Any]],
        max_desc_len: int = 120,
        max_cause_len: int = 120,
        max_prevent_len: int = 120,
    ) -> List[Dict[str, Any]]:
        details = []
        seen = set()

        for item in graph_entities:
            labels = item.get("labels", [])
            node = item.get("node", {})
            name = node.get("name", "")
            if not name:
                continue

            key = f"{','.join(labels)}::{name}"
            if key in seen:
                continue
            seen.add(key)

            detail = {
                "name": name,
                "labels": labels,
            }

            if "Disease" in labels:
                detail.update({
                    "cause": _truncate_text(node.get("cause", ""), max_cause_len),
                    "cure_department": _normalize_str_list(node.get("cure_department")),
                    "cure_lasttime": str(node.get("cure_lasttime", "") or "").strip(),
                    "cure_way": _normalize_str_list(node.get("cure_way")),
                    "cured_prob": str(node.get("cured_prob", "") or "").strip(),
                    "desc": _truncate_text(node.get("desc", ""), max_desc_len),
                    "easy_get": str(node.get("easy_get", "") or "").strip(),
                    "prevent": _truncate_text(node.get("prevent", ""), max_prevent_len),
                })

            details.append(detail)

        return details

    def _get_emb_entities(
        self,
        retriever: QdrantSchemaRetriever,
        query: str,
        topk: int,
        topn: int
    ) -> List[Dict[str, str]]:
        docs = retriever.search(query, topk, topn)
        emb_entities = []
        seen = set()

        for doc in docs:
            doc_key = doc.get("doc_key", "")
            if not doc_key:
                continue

            if "::" in doc_key:
                label, name = doc_key.split("::", 1)
            elif "_" in doc_key:
                label, name = doc_key.split("_", 1)
            else:
                continue

            key = f"{label}::{name}"
            if key in seen:
                continue
            seen.add(key)

            emb_entities.append({
                "label": label,
                "name": name
            })

        return emb_entities

    def _merge_candidates(
        self,
        rule_entities: List[str],
        emb_entities: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        merged = []
        seen: Set[str] = set()

        for name in rule_entities:
            name = str(name).strip()
            if not name:
                continue
            key = f"rule::{name}"
            if key in seen:
                continue
            seen.add(key)
            merged.append({
                "source": "rule",
                "label": "",
                "name": name
            })

        for item in emb_entities:
            label = item.get("label", "").strip()
            name = item.get("name", "").strip()
            if not name:
                continue
            key = f"embedding::{label}::{name}"
            if key in seen:
                continue
            seen.add(key)
            merged.append({
                "source": "embedding",
                "label": label,
                "name": name
            })

        return merged

    def _match_graph_entities(
        self,
        candidates: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        results = []
        seen = set()

        with self.driver.session() as session:
            for item in candidates:
                source = item["source"]
                label = item["label"]
                name = item["name"]

                if source == "embedding" and label:
                    cypher = f"""
                    MATCH (n:`{label}`)
                    WHERE n.name = $name
                    RETURN labels(n) AS labels, properties(n) AS props
                    LIMIT 1
                    """
                    record = session.run(cypher, name=name).single()

                    if record:
                        node = record["props"]
                        node_name = node.get("name", "")
                        dedup_key = f"{','.join(record['labels'])}::{node_name}"
                        if dedup_key not in seen:
                            seen.add(dedup_key)
                            results.append({
                                "source": source,
                                "matched_name": name,
                                "labels": record["labels"],
                                "node": node
                            })
                else:
                    cypher = """
                    MATCH (n)
                    WHERE n.name CONTAINS $name
                    RETURN labels(n) AS labels, properties(n) AS props
                    LIMIT 5
                    """
                    records = list(session.run(cypher, name=name))

                    for r in records:
                        node = r["props"]
                        node_name = node.get("name", "")
                        dedup_key = f"{','.join(r['labels'])}::{node_name}"
                        if dedup_key in seen:
                            continue
                        seen.add(dedup_key)
                        results.append({
                            "source": source,
                            "matched_name": name,
                            "labels": r["labels"],
                            "node": node
                        })

        return results

    def _query_by_intent(
        self,
        graph_entities: List[Dict[str, Any]],
        semantic_type: str
    ) -> List[Dict[str, Any]]:
        if not graph_entities:
            return []

        if semantic_type == INTENT_SYMPTOM:
            return self._query_symptom_consult(graph_entities)
        elif semantic_type == INTENT_DRUG:
            return self._query_drug_consult(graph_entities)
        elif semantic_type == INTENT_PRODUCER:
            return self._query_producer_consult(graph_entities)
        elif semantic_type == INTENT_COMPLICATION:
            return self._query_complication_consult(graph_entities)
        elif semantic_type == INTENT_DEPARTMENT:
            return self._query_department_recommend(graph_entities)
        else:
            return self._query_general(graph_entities)

    def _query_symptom_consult(
        self,
        graph_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []

        disease_names = []
        symptom_names = []

        for item in graph_entities:
            labels = item.get("labels", [])
            node = item.get("node", {})
            name = node.get("name", "")
            if not name:
                continue

            if "Disease" in labels:
                disease_names.append(name)
            if "Symptom" in labels:
                symptom_names.append(name)

        with self.driver.session() as session:
            if disease_names:
                cypher = """
                MATCH (d:Disease)-[:has_symptom]->(s:Symptom)
                WHERE d.name IN $names
                RETURN
                    d.name AS entity,
                    d.desc AS desc,
                    d.cause AS cause,
                    d.prevent AS prevent,
                    d.cure_department AS cure_department,
                    d.cure_lasttime AS cure_lasttime,
                    d.cure_way AS cure_way,
                    d.cured_prob AS cured_prob,
                    d.easy_get AS easy_get,
                    'has_symptom' AS relation,
                    collect(DISTINCT s.name) AS targets
                """
                for r in session.run(cypher, names=disease_names):
                    row = dict(r)
                    row["desc"] = _truncate_text(row.get("desc", ""), 120)
                    row["cause"] = _truncate_text(row.get("cause", ""), 120)
                    row["prevent"] = _truncate_text(row.get("prevent", ""), 120)
                    row["cure_department"] = _normalize_str_list(row.get("cure_department"))
                    row["cure_way"] = _normalize_str_list(row.get("cure_way"))
                    results.append(row)

            if symptom_names:
                cypher = """
                MATCH (d:Disease)-[:has_symptom]->(s:Symptom)
                WHERE s.name IN $names
                RETURN
                    s.name AS entity,
                    'symptom_of' AS relation,
                    collect(DISTINCT d.name) AS targets
                """
                for r in session.run(cypher, names=symptom_names):
                    results.append(dict(r))

        return results

    def _query_drug_consult(
        self,
        graph_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []

        disease_names = []
        drug_names = []
        producer_names = []

        for item in graph_entities:
            labels = item.get("labels", [])
            node = item.get("node", {})
            name = node.get("name", "")
            if not name:
                continue

            if "Disease" in labels:
                disease_names.append(name)
            if "Drug" in labels:
                drug_names.append(name)
            if "Producer" in labels:
                producer_names.append(name)

        with self.driver.session() as session:
            if disease_names:
                cypher = """
                MATCH (d:Disease)-[r:common_drug|recommand_drug]->(drug:Drug)
                WHERE d.name IN $names
                RETURN
                    d.name AS entity,
                    d.desc AS desc,
                    d.cause AS cause,
                    d.prevent AS prevent,
                    d.cure_department AS cure_department,
                    d.cure_lasttime AS cure_lasttime,
                    d.cure_way AS cure_way,
                    d.cured_prob AS cured_prob,
                    d.easy_get AS easy_get,
                    type(r) AS relation,
                    collect(DISTINCT drug.name) AS targets
                """
                for r in session.run(cypher, names=disease_names):
                    row = dict(r)
                    row["desc"] = _truncate_text(row.get("desc", ""), 120)
                    row["cause"] = _truncate_text(row.get("cause", ""), 120)
                    row["prevent"] = _truncate_text(row.get("prevent", ""), 120)
                    row["cure_department"] = _normalize_str_list(row.get("cure_department"))
                    row["cure_way"] = _normalize_str_list(row.get("cure_way"))
                    results.append(row)

            if drug_names:
                cypher = """
                MATCH (p:Producer)-[:drugs_of]->(drug:Drug)
                WHERE drug.name IN $names
                RETURN
                    drug.name AS entity,
                    'produced_by' AS relation,
                    collect(DISTINCT p.name) AS targets
                """
                for r in session.run(cypher, names=drug_names):
                    results.append(dict(r))

            if drug_names:
                cypher = """
                MATCH (d:Disease)-[r:common_drug|recommand_drug]->(drug:Drug)
                WHERE drug.name IN $names
                RETURN
                    drug.name AS entity,
                    type(r) AS relation,
                    collect(DISTINCT d.name) AS targets
                """
                for r in session.run(cypher, names=drug_names):
                    results.append(dict(r))

            if producer_names:
                cypher = """
                MATCH (p:Producer)-[:drugs_of]->(drug:Drug)
                WHERE p.name IN $names
                RETURN
                    p.name AS entity,
                    'drugs_of' AS relation,
                    collect(DISTINCT drug.name) AS targets
                """
                for r in session.run(cypher, names=producer_names):
                    results.append(dict(r))

        return results

    def _query_producer_consult(
        self,
        graph_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        producer_names = []
        drug_names = []

        for item in graph_entities:
            labels = item.get("labels", [])
            node = item.get("node", {})
            name = node.get("name", "")
            if not name:
                continue

            if "Producer" in labels:
                producer_names.append(name)
            if "Drug" in labels:
                drug_names.append(name)

        with self.driver.session() as session:
            if producer_names:
                cypher = """
                MATCH (p:Producer)-[:drugs_of]->(drug:Drug)
                WHERE p.name IN $names
                RETURN p.name AS entity, 'drugs_of' AS relation, collect(drug.name) AS targets
                """
                for r in session.run(cypher, names=producer_names):
                    results.append(dict(r))

            if drug_names:
                cypher = """
                MATCH (p:Producer)-[:drugs_of]->(drug:Drug)
                WHERE drug.name IN $names
                RETURN drug.name AS entity, 'produced_by' AS relation, collect(p.name) AS targets
                """
                for r in session.run(cypher, names=drug_names):
                    results.append(dict(r))

        return results

    def _query_complication_consult(
        self,
        graph_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        disease_names = []

        for item in graph_entities:
            labels = item.get("labels", [])
            node = item.get("node", {})
            name = node.get("name", "")
            if "Disease" in labels and name:
                disease_names.append(name)

        if not disease_names:
            return results

        with self.driver.session() as session:
            cypher = """
            MATCH (d:Disease)-[:acompany_with]->(other:Disease)
            WHERE d.name IN $names
            RETURN
                d.name AS entity,
                d.desc AS desc,
                d.cause AS cause,
                d.prevent AS prevent,
                d.cure_department AS cure_department,
                d.cure_lasttime AS cure_lasttime,
                d.cure_way AS cure_way,
                d.cured_prob AS cured_prob,
                d.easy_get AS easy_get,
                'acompany_with' AS relation,
                collect(DISTINCT other.name) AS targets
            """
            for r in session.run(cypher, names=disease_names):
                row = dict(r)
                row["desc"] = _truncate_text(row.get("desc", ""), 120)
                row["cause"] = _truncate_text(row.get("cause", ""), 120)
                row["prevent"] = _truncate_text(row.get("prevent", ""), 120)
                row["cure_department"] = _normalize_str_list(row.get("cure_department"))
                row["cure_way"] = _normalize_str_list(row.get("cure_way"))
                results.append(row)

        return results

    def _query_department_recommend(
        self,
        graph_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        disease_names = []
        symptom_names = []

        for item in graph_entities:
            labels = item.get("labels", [])
            node = item.get("node", {})
            name = node.get("name", "")
            if not name:
                continue

            if "Disease" in labels:
                disease_names.append(name)
            if "Symptom" in labels:
                symptom_names.append(name)

        with self.driver.session() as session:
            if disease_names:
                cypher = """
                MATCH (d:Disease)-[:belongs_to]->(dep:Department)
                WHERE d.name IN $names
                RETURN
                    d.name AS entity,
                    d.desc AS desc,
                    d.cause AS cause,
                    d.prevent AS prevent,
                    d.cure_department AS cure_department,
                    d.cure_lasttime AS cure_lasttime,
                    d.cure_way AS cure_way,
                    d.cured_prob AS cured_prob,
                    d.easy_get AS easy_get,
                    'belongs_to' AS relation,
                    collect(DISTINCT dep.name) AS targets
                """
                for r in session.run(cypher, names=disease_names):
                    row = dict(r)
                    row["desc"] = _truncate_text(row.get("desc", ""), 120)
                    row["cause"] = _truncate_text(row.get("cause", ""), 120)
                    row["prevent"] = _truncate_text(row.get("prevent", ""), 120)
                    row["cure_department"] = _normalize_str_list(row.get("cure_department"))
                    row["cure_way"] = _normalize_str_list(row.get("cure_way"))
                    results.append(row)

            if symptom_names:
                cypher = """
                MATCH (d:Disease)-[:has_symptom]->(s:Symptom)
                MATCH (d)-[:belongs_to]->(dep:Department)
                WHERE s.name IN $names
                RETURN
                    s.name AS entity,
                    'recommend_department' AS relation,
                    collect(DISTINCT d.name) AS diseases,
                    collect(DISTINCT dep.name) AS targets
                """
                for r in session.run(cypher, names=symptom_names):
                    results.append(dict(r))

        return results

    def _query_general(
        self,
        graph_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        names = []

        for item in graph_entities:
            node = item.get("node", {})
            name = node.get("name", "")
            if name:
                names.append(name)

        if not names:
            return results

        with self.driver.session() as session:
            cypher = """
            MATCH (n)-[r]-(m)
            WHERE n.name IN $names
            RETURN
                n.name AS entity,
                type(r) AS relation,
                collect(DISTINCT m.name)[0..10] AS targets
            """
            for r in session.run(cypher, names=names):
                results.append(dict(r))

        return results
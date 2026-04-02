from typing import Any, List
from neo4j import GraphDatabase
import json
import os
from dataclasses import asdict
from app.services.knowledge.schema_retriever import SchemaDoc


LABEL_CN_MAP = {
    "Disease": "疾病",
    "Drug": "药物",
    "Symptom": "症状",
    "Food": "食物",
    "Check": "检查",
    "Department": "科室",
    "Producer": "药企",
}


def normalize_list(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return "、".join(
            str(x).strip()
            for x in value
            if x is not None and str(x).strip()
        )

    text = str(value).strip()
    return text


def load_entity_docs_from_neo4j(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
) -> List[SchemaDoc]:
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    docs: List[SchemaDoc] = []

    cypher = """
    MATCH (n)
    WHERE n.name IS NOT NULL
    RETURN labels(n)[0] AS label,
           n.name AS name,
           coalesce(n.desc, '') AS desc,
           coalesce(n.cause, '') AS cause,
           coalesce(n.prevent, '') AS prevent,
           coalesce(n.easy_get, '') AS easy_get,
           coalesce(n.cure_lasttime, '') AS cure_lasttime,
           coalesce(n.cured_prob, '') AS cured_prob,
           coalesce(n.cure_way, []) AS cure_way,
           coalesce(n.cure_department, []) AS cure_department
    """

    try:
        with driver.session() as session:
            result = session.run(cypher)

            for record in result:
                label = record["label"] or ""
                name = record["name"] or ""

                label_cn = LABEL_CN_MAP.get(label, label)
                extra_parts = []

                if label == "Disease":
                    desc = record["desc"]
                    cause = record["cause"]
                    prevent = record["prevent"]
                    easy_get = record["easy_get"]
                    cure_lasttime = record["cure_lasttime"]
                    cured_prob = record["cured_prob"]

                    cure_way = normalize_list(record["cure_way"])
                    cure_department = normalize_list(record["cure_department"])

                    if desc:
                        extra_parts.append(desc)
                    if cause:
                        extra_parts.append(f"病因: {cause}")
                    if prevent:
                        extra_parts.append(f"预防: {prevent}")
                    if easy_get:
                        extra_parts.append(f"易感人群: {easy_get}")
                    if cure_way:
                        extra_parts.append(f"治疗方式: {cure_way}")
                    if cure_department:
                        extra_parts.append(f"就诊科室: {cure_department}")
                    if cure_lasttime:
                        extra_parts.append(f"治疗周期: {cure_lasttime}")
                    if cured_prob:
                        extra_parts.append(f"治愈概率: {cured_prob}")

                merged_desc = f"{label_cn}；" + "；".join(extra_parts) if extra_parts else label_cn

                docs.append(
                    SchemaDoc(
                        item_type="entity",
                        std_name=name,
                        label=label,
                        aliases=[],
                        desc=merged_desc,
                    )
                )
    finally:
        driver.close()
    
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(BASE_DIR, "entity_doc.json") 
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(
            [asdict(doc) for doc in docs],
            f,
            ensure_ascii=False,
            indent=2
        )

    return docs
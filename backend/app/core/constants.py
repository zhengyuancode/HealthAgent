"""
Global constants for query understanding and medical assistant logic
"""

# ================================
# Intent Types
# ================================

INTENT_SYMPTOM = "symptom_consult"
INTENT_DRUG = "drug_consult"
INTENT_POLICY = "policy_consult"
INTENT_DEPARTMENT = "department_recommend"
INTENT_GENERAL = "general"

INTENT_LIST = [
    INTENT_SYMPTOM,
    INTENT_DRUG,
    INTENT_POLICY,
    INTENT_DEPARTMENT,
    INTENT_GENERAL,
]

# ================================
# Intent Priority (重要！避免冲突)
# ================================
# 数值越小优先级越高

INTENT_PRIORITY = {
    INTENT_DEPARTMENT: 1,   # "挂什么科"优先最高
    INTENT_POLICY: 2,
    INTENT_DRUG: 3,
    INTENT_SYMPTOM: 4,
    INTENT_GENERAL: 99,
}

# ================================
# Risk Levels
# ================================

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

# ================================
# Keyword Dictionaries
# ================================

# ---- 症状词 ----
SYMPTOM_TERMS = [
    "发烧", "发热", "咳嗽", "头痛", "头晕", "腹痛", "腹泻",
    "恶心", "呕吐", "胸痛", "呼吸困难", "鼻塞", "流鼻涕",
    "喉咙痛", "乏力", "失眠", "心慌", "气短", "出汗"
]

# ---- 药物名称（可不断扩展）----
DRUG_TERMS = [
    "布洛芬", "阿莫西林", "头孢", "对乙酰氨基酚",
    "感冒药", "退烧药", "止痛药"
]

# ---- 药物相关问法 ----
DRUG_QUERY_TERMS = [
    "药", "用药", "吃什么药", "怎么吃", "剂量",
    "副作用", "不良反应", "禁忌", "说明书",
    "能不能吃", "可以吃吗"
]

# ---- 医保 / 政策 ----
POLICY_TERMS = [
    "医保", "报销", "政策", "门诊统筹", "住院",
    "自费", "商保", "新农合", "费用", "能报吗"
]

# ---- 科室推荐 ----
DEPARTMENT_QUERY_TERMS = [
    "挂什么科", "挂哪科", "看什么科", "看哪科",
    "去哪个科", "什么门诊", "应该看什么科"
]

# ---- 高风险关键词 ----
HIGH_RISK_TERMS = [
    "胸痛", "呼吸困难", "抽搐", "昏迷", "意识不清",
    "大出血", "呕血", "黑便", "休克",
    "心梗", "脑出血",
    "自杀", "轻生", "不想活"
]

# ---- 中风险提示词 ----
MEDIUM_RISK_TERMS = [
    "高烧", "持续发热", "剧烈疼痛",
    "便血", "血尿"
]

# ---- 特殊人群 ----
SPECIAL_POPULATION_TERMS = [
    "孕妇", "怀孕",
    "婴儿", "宝宝", "新生儿",
    "儿童",
    "老人", "老年人"
]

# ================================
# Retrieval Strategy Mapping
# ================================

# ---- 是否建议查知识图谱 ----
INTENT_NEED_GRAPH = {
    INTENT_SYMPTOM: True,
    INTENT_DRUG: True,
    INTENT_DEPARTMENT: True,
    INTENT_POLICY: False,
    INTENT_GENERAL: False,
}

# ---- 是否建议查RAG ----
INTENT_NEED_RAG = {
    INTENT_POLICY: True,
    INTENT_DRUG: True,
    INTENT_SYMPTOM: False,
    INTENT_DEPARTMENT: False,
    INTENT_GENERAL: False,
}

# ================================
# Entity Extraction Pools（统一入口）
# ================================

# 用于实体抽取（统一扫描）
ENTITY_TERM_POOL = (
    SYMPTOM_TERMS
    + DRUG_TERMS
    + POLICY_TERMS
    + SPECIAL_POPULATION_TERMS
)

# ================================
# Intent Keyword Mapping（可用于打分）
# ================================

INTENT_KEYWORDS = {
    INTENT_DEPARTMENT: DEPARTMENT_QUERY_TERMS,
    INTENT_POLICY: POLICY_TERMS,
    INTENT_DRUG: DRUG_TERMS + DRUG_QUERY_TERMS,
    INTENT_SYMPTOM: SYMPTOM_TERMS,
}

# ================================
# Fallback Strategy（给未来 LLM 用）
# ================================

# 当规则无法确定时的兜底标志
UNCERTAIN_INTENT = "uncertain"
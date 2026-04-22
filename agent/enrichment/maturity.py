"""
Rule-based AI maturity pre-scorer (0–3).
Provides a first-pass score before the LLM brief; the LLM may refine it.
"""

_AI_STACK_SIGNALS = {
    "databricks", "snowflake", "dbt", "wandb", "mlflow", "ray", "vllm",
    "hugging face", "huggingface", "sagemaker", "vertex ai", "tensorflow",
    "pytorch", "cuda", "triton", "langchain", "llamaindex", "pinecone",
    "weaviate", "qdrant", "chroma",
}

_AI_TITLE_SIGNALS = {
    "machine learning", "ml engineer", "applied scientist", "llm", "ai engineer",
    "data scientist", "nlp engineer", "computer vision", "deep learning",
    "ai product manager", "ml platform", "mlops", "head of ai", "vp data",
    "chief scientist", "director of ai", "principal scientist",
}

_EXEC_AI_KEYWORDS = {
    "generative ai", "large language model", "llm", "ai-first", "ai strategy",
    "ai roadmap", "foundation model", "machine learning platform",
}


_AI_INDUSTRY_SIGNALS = {
    "artificial intelligence", "machine learning", "deep learning", "nlp",
    "computer vision", "data science", "generative ai", "llm", "mlops",
    "ai", "ml", "analytics", "big data", "data platform",
}


def score(
    tech_stack: list[str],
    ai_roles: list[str],
    has_named_ai_leadership: bool = False,
    exec_commentary_keywords: list[str] | None = None,
    industries: list[str] | None = None,
) -> tuple[int, dict]:
    """
    Returns (score, rationale_dict).
    score: 0–3 integer
    rationale: breakdown of contributing signals
    """
    points = 0
    rationale: dict = {
        "ml_stack_hits": [],
        "ai_role_hits": [],
        "named_ai_leadership": has_named_ai_leadership,
        "exec_ai_commentary": False,
    }

    # ML stack (low weight — contributes max 1 point)
    stack_lower = {t.lower() for t in tech_stack}
    ml_hits = [s for s in _AI_STACK_SIGNALS if any(s in t for t in stack_lower)]
    rationale["ml_stack_hits"] = ml_hits
    if ml_hits:
        points += 1

    # AI roles (high weight — each distinct role type adds)
    role_titles = " ".join(r.lower() for r in ai_roles)
    role_hits = [kw for kw in _AI_TITLE_SIGNALS if kw in role_titles]
    rationale["ai_role_hits"] = role_hits[:5]
    if len(role_hits) >= 3:
        points += 2
    elif role_hits:
        points += 1

    # Named AI leadership (high weight)
    if has_named_ai_leadership:
        points += 1
        rationale["named_ai_leadership"] = True

    # Executive AI commentary (medium weight)
    if exec_commentary_keywords:
        kw_lower = " ".join(k.lower() for k in exec_commentary_keywords)
        exec_hits = [kw for kw in _EXEC_AI_KEYWORDS if kw in kw_lower]
        if exec_hits:
            points += 1
            rationale["exec_ai_commentary"] = True

    # Industry signal (medium weight — companies in AI/ML/Data industries get +1)
    if industries:
        industry_text = " ".join(i.lower() for i in industries)
        industry_hits = [s for s in _AI_INDUSTRY_SIGNALS if s in industry_text]
        if industry_hits:
            points += 1
            rationale.setdefault("industry_ai_signals", industry_hits)

    return min(points, 3), rationale

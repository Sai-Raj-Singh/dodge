"""Query executor — runs the execution plan against Neo4j and/or ChromaDB.

Routes queries based on the strategy from the enhancer:
  - "graph"  → Cypher against Neo4j
  - "rag"    → semantic search against ChromaDB
  - "hybrid" → both, then merge
"""

from app.graph.connection import get_session
from app.rag.vector_store import search as vector_search


def _run_cypher(cypher: str, params: dict) -> list[dict]:
    """Execute a single Cypher query and return rows as dicts."""
    with get_session() as session:
        result = session.run(cypher, params)
        return [dict(record) for record in result]


def _run_rag(
    search_text: str, n_results: int = 8, where: dict | None = None
) -> list[dict]:
    """Run a semantic search against ChromaDB."""
    return vector_search(query=search_text, n_results=n_results, where=where)


def execute(plan: dict) -> dict:
    """Execute a query plan and return structured results.

    Args:
        plan: dict from enhancer.enhance() with strategy, cypher, search_text, etc.

    Returns:
        dict with:
            strategy: str
            description: str
            graph_results: list[dict] | None
            rag_results: list[dict] | None
            error: str | None
    """
    strategy = plan["strategy"]
    result = {
        "strategy": strategy,
        "description": plan.get("description", ""),
        "graph_results": None,
        "rag_results": None,
        "error": None,
    }

    try:
        # ── Graph-only ───────────────────────────────────────────
        if strategy == "graph":
            cypher = plan.get("cypher")
            params = plan.get("cypher_params", {})

            if isinstance(cypher, list):
                # Multiple queries (e.g. broken flow: both types)
                all_rows = []
                param_list = plan.get("cypher_params", [{}] * len(cypher))
                for i, q in enumerate(cypher):
                    p = param_list[i] if i < len(param_list) else {}
                    rows = _run_cypher(q, p)
                    all_rows.extend(rows)
                result["graph_results"] = all_rows
            else:
                result["graph_results"] = _run_cypher(cypher, params)

        # ── RAG-only ─────────────────────────────────────────────
        elif strategy == "rag":
            search_text = plan.get("search_text", "")
            n_results = plan.get("n_results", 8)
            where = plan.get("search_filter")
            result["rag_results"] = _run_rag(search_text, n_results, where)

        # ── Hybrid (graph + RAG) ─────────────────────────────────
        elif strategy == "hybrid":
            # Run graph if cypher is provided
            cypher = plan.get("cypher")
            if cypher:
                params = plan.get("cypher_params", {})
                result["graph_results"] = _run_cypher(cypher, params)

            # Run RAG search
            search_text = plan.get("search_text", "")
            if search_text:
                n_results = plan.get("n_results", 8)
                where = plan.get("search_filter")
                result["rag_results"] = _run_rag(search_text, n_results, where)

    except Exception as e:
        result["error"] = str(e)

    return result

"""Query pipeline — classify, enhance, execute, respond.

Usage:
    from app.query import ask
    answer = ask("Trace the flow for sales order 740506")
"""

from app.query.classifier import classify
from app.query.enhancer import enhance
from app.query.executor import execute
from app.query.response import generate


def ask(query: str) -> dict:
    """Full query pipeline: classify → enhance → execute → generate response.

    Args:
        query: Natural language question from the user.

    Returns:
        dict with keys: answer, category, strategy, description, raw_results
    """
    classified = classify(query)
    plan = enhance(classified)
    results = execute(plan)
    answer = generate(query, results, plan.get("description", ""))

    return {
        "answer": answer,
        "category": classified.category,
        "subcategory": classified.subcategory,
        "strategy": plan["strategy"],
        "description": plan.get("description", ""),
        "entity_ids": classified.entity_ids,
        "raw_results": results,
    }

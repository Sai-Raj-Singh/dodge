"""Guardrail validator for dataset-scope queries.

Rejects unrelated questions and only allows queries about the provided
SAP Order-to-Cash dataset and entities.
"""

import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str = ""
    message: str = ""


_ALLOW_KEYWORDS = [
    "sales order",
    "order",
    "delivery",
    "billing",
    "invoice",
    "payment",
    "journal",
    "customer",
    "business partner",
    "product",
    "material",
    "plant",
    "document flow",
    "o2c",
    "order to cash",
    "revenue",
    "status",
    "sap",
]

_REJECT_KEYWORDS = [
    "weather",
    "sports",
    "movie",
    "music",
    "recipe",
    "politics",
    "stock market",
    "bitcoin",
    "travel",
    "translate",
    "joke",
    "poem",
    "story",
    "code interview",
]

_DEFAULT_REJECTION = (
    "This system only answers questions about the provided business dataset"
)


def validate_query(query: str) -> ValidationResult:
    """Validate whether a query is in scope for this system."""
    q = (query or "").strip().lower()
    if not q:
        return ValidationResult(
            is_valid=False,
            reason="empty_query",
            message=_DEFAULT_REJECTION,
        )

    if any(kw in q for kw in _REJECT_KEYWORDS):
        return ValidationResult(
            is_valid=False,
            reason="explicitly_unrelated",
            message=_DEFAULT_REJECTION,
        )

    # Allow numeric ID style queries like "740506 status"
    has_id_like = bool(re.search(r"\b\d{5,10}\b", q))
    has_domain_keyword = any(kw in q for kw in _ALLOW_KEYWORDS)

    if has_domain_keyword or has_id_like:
        return ValidationResult(is_valid=True)

    return ValidationResult(
        is_valid=False,
        reason="out_of_scope",
        message=_DEFAULT_REJECTION,
    )

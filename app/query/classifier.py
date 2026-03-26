"""Query classifier — determines the best execution strategy for a user query.

Categories:
  flow_trace     — trace a specific document flow (user provides an order/delivery/billing ID)
  broken_flow    — find broken flows (delivered-not-billed, billed-not-paid)
  entity_lookup  — get details about a specific entity (order, customer, product)
  aggregation    — counts, totals, rankings, top-N
  contextual     — general / exploratory question → RAG semantic search
"""

import re
from dataclasses import dataclass, field


@dataclass
class ClassifiedQuery:
    """Result of query classification."""

    category: str  # one of the 5 categories above
    subcategory: str = ""  # e.g. "delivered_not_billed"
    entity_ids: dict = field(default_factory=dict)  # extracted IDs
    confidence: str = "high"  # high / medium / low
    raw_query: str = ""


# ── Regex patterns for entity ID extraction ──────────────────────

_SALES_ORDER_RE = re.compile(
    r"(?:sales\s*order|SO|order)\s*#?\s*(\d{5,7})", re.IGNORECASE
)
_DELIVERY_RE = re.compile(r"(?:delivery|DL|shipment)\s*#?\s*(\d{7,9})", re.IGNORECASE)
_BILLING_RE = re.compile(
    r"(?:billing|invoice|bill)\s*(?:doc(?:ument)?)?\s*#?\s*(\d{7,9})", re.IGNORECASE
)
_CUSTOMER_RE = re.compile(r"(?:customer|partner|BP)\s*#?\s*(\d{8,10})", re.IGNORECASE)
_PRODUCT_RE = re.compile(
    r"(?:product|material)\s*#?\s*([A-Z0-9_-]{3,20})", re.IGNORECASE
)
# Journal entry / accounting document number (exact digits; must appear with journal context)
_JOURNAL_ENTRY_INLINE = re.compile(
    r"(?:journal\s*entry|journal|JE|accounting\s*document)\s*(?:number|no\.?|#)?\s*[:\s]*(\d{8,12})",
    re.IGNORECASE,
)
_LINKED_TO_NUM = re.compile(
    r"(?:linked\s+to|link(?:ed)?\s+to|reference|for)\s*(?:this\s*)?[:\s]*(\d{8,12})",
    re.IGNORECASE,
)

# ── Keyword groups ───────────────────────────────────────────────

_BROKEN_FLOW_KEYWORDS = [
    "not billed",
    "not invoiced",
    "unbilled",
    "not paid",
    "unpaid",
    "outstanding",
    "pending payment",
    "overdue",
    "delivered but",
    "billed but",
    "broken flow",
    "incomplete flow",
    "missing billing",
    "missing payment",
    "open items",
]

_AGGREGATION_KEYWORDS = [
    "how many",
    "total",
    "count",
    "sum",
    "average",
    "top ",
    "highest",
    "lowest",
    "most",
    "least",
    "revenue",
    "rank",
    "statistics",
    "stats",
    "overview",
    "summary",
    "breakdown",
    "by customer",
    "by product",
    "by status",
    "per customer",
    "per product",
]

_FLOW_TRACE_KEYWORDS = [
    "trace",
    "track",
    "flow",
    "document flow",
    "path",
    "journey",
    "lifecycle",
    "end to end",
    "e2e",
    "full flow",
    "status of order",
    "what happened to",
    "where is",
]


def _journal_context(query_lower: str) -> bool:
    return bool(
        re.search(
            r"\bjournal\b|journal\s+entry|accounting\s+document|\bJE\b",
            query_lower,
        )
    )


def _extract_entity_ids(query: str) -> dict:
    """Extract entity IDs from the query string."""
    ids: dict = {}
    q_lower = query.lower()

    # Journal entry / reference number (exact ID) — only when question is about journals
    if _journal_context(q_lower):
        m = _JOURNAL_ENTRY_INLINE.search(query)
        if m:
            ids["journalEntry"] = m.group(1)
        else:
            m = _LINKED_TO_NUM.search(query)
            if m:
                ids["journalEntry"] = m.group(1)
            else:
                m = re.search(r":\s*(\d{8,12})\s*$", query.strip())
                if m:
                    ids["journalEntry"] = m.group(1)
                else:
                    m = re.search(r"\bfor\s+(\d{8,12})\b", query, re.IGNORECASE)
                    if m:
                        ids["journalEntry"] = m.group(1)
                    else:
                        nums = re.findall(r"\b(\d{8,12})\b", query)
                        if len(nums) == 1:
                            ids["journalEntry"] = nums[0]

    m = _SALES_ORDER_RE.search(query)
    if m:
        ids["salesOrder"] = m.group(1)
    m = _DELIVERY_RE.search(query)
    if m:
        ids["deliveryDocument"] = m.group(1)
    m = _BILLING_RE.search(query)
    if m:
        ids["billingDocument"] = m.group(1)
    m = _CUSTOMER_RE.search(query)
    if m:
        ids["businessPartner"] = m.group(1)
    m = _PRODUCT_RE.search(query)
    if m:
        ids["product"] = m.group(1)
    return ids


def _has_keyword(query_lower: str, keywords: list[str]) -> bool:
    return any(kw in query_lower for kw in keywords)


def classify(query: str) -> ClassifiedQuery:
    """Classify a natural language query into an execution category.

    Uses rule-based heuristics (regex + keywords). No LLM call needed —
    fast and deterministic.
    """
    q = query.strip()
    q_lower = q.lower()
    entity_ids = _extract_entity_ids(q)

    # ── 1. Broken flow detection ─────────────────────────────────
    if _has_keyword(q_lower, _BROKEN_FLOW_KEYWORDS):
        sub = ""
        if any(
            kw in q_lower
            for kw in ["not billed", "unbilled", "missing billing", "delivered but"]
        ):
            sub = "delivered_not_billed"
        elif any(
            kw in q_lower
            for kw in [
                "not paid",
                "unpaid",
                "outstanding",
                "pending payment",
                "overdue",
                "billed but",
                "missing payment",
                "open items",
            ]
        ):
            sub = "billed_not_paid"
        return ClassifiedQuery(
            category="broken_flow",
            subcategory=sub,
            entity_ids=entity_ids,
            raw_query=q,
        )

    # ── 2. Flow trace (with a specific entity ID) ────────────────
    if entity_ids and _has_keyword(q_lower, _FLOW_TRACE_KEYWORDS):
        return ClassifiedQuery(
            category="flow_trace",
            entity_ids=entity_ids,
            raw_query=q,
        )

    # ── 3. Entity lookup (ID present, but no flow keywords) ──────
    if entity_ids:
        return ClassifiedQuery(
            category="entity_lookup",
            entity_ids=entity_ids,
            raw_query=q,
        )

    # ── 4. Flow trace without ID (general flow question) ─────────
    if _has_keyword(q_lower, _FLOW_TRACE_KEYWORDS):
        return ClassifiedQuery(
            category="flow_trace",
            entity_ids=entity_ids,
            confidence="medium",
            raw_query=q,
        )

    # ── 5. Aggregation ───────────────────────────────────────────
    if _has_keyword(q_lower, _AGGREGATION_KEYWORDS):
        return ClassifiedQuery(
            category="aggregation",
            entity_ids=entity_ids,
            raw_query=q,
        )

    # ── 6. Fallback → contextual (RAG) ───────────────────────────
    return ClassifiedQuery(
        category="contextual",
        entity_ids=entity_ids,
        confidence="medium",
        raw_query=q,
    )

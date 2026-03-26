"""Prompt enhancer — converts classified queries into execution-ready parameters.

Takes a ClassifiedQuery and prepares:
  - Cypher query + parameters for graph-based queries
  - Search text + filters for RAG queries
  - Combined strategy for hybrid queries
"""

from app.query.classifier import ClassifiedQuery
from app.graph import queries as Q


def enhance(classified: ClassifiedQuery) -> dict:
    """Convert a classified query into an execution plan.

    Returns a dict with:
        strategy: "graph" | "rag" | "hybrid"
        cypher: optional Cypher query string
        cypher_params: optional dict of Cypher parameters
        search_text: optional text for RAG search
        search_filter: optional metadata filter for ChromaDB
        description: human-readable description of what we're doing
    """
    cat = classified.category
    sub = classified.subcategory
    ids = classified.entity_ids

    # ── Broken flow detection → graph ────────────────────────────
    if cat == "broken_flow":
        if sub == "delivered_not_billed":
            return {
                "strategy": "graph",
                "cypher": Q.DELIVERED_NOT_BILLED,
                "cypher_params": {},
                "description": "Finding deliveries that have not been billed",
            }
        elif sub == "billed_not_paid":
            return {
                "strategy": "graph",
                "cypher": Q.BILLED_NOT_PAID,
                "cypher_params": {},
                "description": "Finding billing documents that have not been paid",
            }
        else:
            # Generic broken flow — run both
            return {
                "strategy": "graph",
                "cypher": [Q.DELIVERED_NOT_BILLED, Q.BILLED_NOT_PAID],
                "cypher_params": [{}, {}],
                "description": "Finding all broken flows (delivered-not-billed and billed-not-paid)",
            }

    # ── Flow trace → graph ───────────────────────────────────────
    if cat == "flow_trace":
        if "salesOrder" in ids:
            return {
                "strategy": "graph",
                "cypher": Q.FULL_FLOW_BY_SALES_ORDER,
                "cypher_params": {"salesOrder": ids["salesOrder"]},
                "description": f"Tracing full document flow for Sales Order {ids['salesOrder']}",
            }
        elif "deliveryDocument" in ids:
            return {
                "strategy": "graph",
                "cypher": Q.FULL_FLOW_BY_DELIVERY,
                "cypher_params": {"deliveryDocument": ids["deliveryDocument"]},
                "description": f"Tracing document flow for Delivery {ids['deliveryDocument']}",
            }
        elif "billingDocument" in ids:
            return {
                "strategy": "graph",
                "cypher": Q.FULL_FLOW_BY_BILLING,
                "cypher_params": {"billingDocument": ids["billingDocument"]},
                "description": f"Tracing document flow for Billing Document {ids['billingDocument']}",
            }
        elif "journalEntry" in ids:
            return {
                "strategy": "graph",
                "cypher": Q.JOURNAL_ENTRY_LOOKUP,
                "cypher_params": {"documentId": ids["journalEntry"]},
                "description": f"Exact lookup for journal / reference document {ids['journalEntry']}",
            }
        else:
            # No specific ID — fall back to RAG
            return {
                "strategy": "rag",
                "search_text": classified.raw_query,
                "search_filter": {"type": "flow"},
                "n_results": 10,
                "description": "Searching flow information via semantic search",
            }

    # ── Entity lookup → graph ────────────────────────────────────
    if cat == "entity_lookup":
        if "journalEntry" in ids:
            return {
                "strategy": "graph",
                "cypher": Q.JOURNAL_ENTRY_LOOKUP,
                "cypher_params": {"documentId": ids["journalEntry"]},
                "description": f"Exact lookup for journal / reference document {ids['journalEntry']}",
            }
        elif "salesOrder" in ids:
            return {
                "strategy": "graph",
                "cypher": Q.SALES_ORDER_DETAILS,
                "cypher_params": {"salesOrder": ids["salesOrder"]},
                "description": f"Looking up Sales Order {ids['salesOrder']}",
            }
        elif "businessPartner" in ids:
            return {
                "strategy": "graph",
                "cypher": Q.CUSTOMER_ORDERS,
                "cypher_params": {"businessPartner": ids["businessPartner"]},
                "description": f"Looking up orders for Customer {ids['businessPartner']}",
            }
        elif "product" in ids:
            return {
                "strategy": "graph",
                "cypher": Q.PRODUCT_ORDERS,
                "cypher_params": {"product": ids["product"]},
                "description": f"Looking up orders for Product {ids['product']}",
            }
        else:
            # Has IDs but no matching query template — hybrid
            return {
                "strategy": "hybrid",
                "search_text": classified.raw_query,
                "n_results": 8,
                "description": "Looking up entity via semantic search",
            }

    # ── Aggregation → graph ──────────────────────────────────────
    if cat == "aggregation":
        q_lower = classified.raw_query.lower()
        if "revenue" in q_lower and "customer" in q_lower:
            return {
                "strategy": "graph",
                "cypher": Q.TOTAL_REVENUE_BY_CUSTOMER,
                "cypher_params": {},
                "description": "Calculating total revenue by customer",
            }
        elif "status" in q_lower:
            return {
                "strategy": "graph",
                "cypher": Q.ORDER_COUNT_BY_STATUS,
                "cypher_params": {},
                "description": "Counting orders by delivery status",
            }
        elif "product" in q_lower or "top" in q_lower:
            return {
                "strategy": "graph",
                "cypher": Q.TOP_PRODUCTS_BY_REVENUE,
                "cypher_params": {"limit": 10},
                "description": "Finding top products by revenue",
            }
        elif "how many" in q_lower or "count" in q_lower:
            return {
                "strategy": "graph",
                "cypher": Q.NODE_COUNTS,
                "cypher_params": {},
                "description": "Getting graph node counts",
            }
        else:
            # Generic aggregation — try hybrid
            return {
                "strategy": "hybrid",
                "cypher": Q.NODE_COUNTS,
                "cypher_params": {},
                "search_text": classified.raw_query,
                "n_results": 8,
                "description": "Running aggregation with supplemental context",
            }

    # ── Contextual → RAG ─────────────────────────────────────────
    return {
        "strategy": "rag",
        "search_text": classified.raw_query,
        "n_results": 8,
        "description": "Searching knowledge base via semantic search",
    }

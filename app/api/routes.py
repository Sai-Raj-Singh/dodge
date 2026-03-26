"""API routes for query execution, graph visualization, and flow inspection."""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.flow.detector import detect_all
from app.flow.tracer import trace_by_billing, trace_by_delivery, trace_by_sales_order
from app.graph.connection import get_session
from app.guardrails import validate_query
from app.query import ask


router = APIRouter()


class AskRequest(BaseModel):
    query: str = Field(min_length=1, description="Natural language question")


class AskResponse(BaseModel):
    ok: bool
    answer: str
    category: str = ""
    strategy: str = ""
    details: dict = Field(default_factory=dict)


def _pick_entity_id(label: str, props: dict[str, Any]) -> str:
    candidates = {
        "Customer": ["businessPartner"],
        "SalesOrder": ["salesOrder"],
        "SalesOrderItem": ["salesOrderItem", "material"],
        "Delivery": ["deliveryDocument"],
        "DeliveryItem": ["deliveryDocumentItem", "referenceSdDocument"],
        "BillingDocument": ["billingDocument"],
        "BillingItem": ["billingDocumentItem", "billingDocument"],
        "JournalEntry": ["accountingDocument"],
        "Payment": ["accountingDocument"],
        "Product": ["product"],
        "Plant": ["plant", "plantName"],
        "Address": ["addressId", "cityName"],
    }
    for key in candidates.get(label, []):
        if props.get(key) is not None:
            return str(props[key])
    for key in ["id", "name", "description"]:
        if props.get(key) is not None:
            return str(props[key])
    return label


def _node_payload(node: Any, element_id: str) -> dict:
    labels = list(getattr(node, "labels", []))
    label = labels[0] if labels else "Entity"
    props = dict(node)
    entity_id = _pick_entity_id(label, props)
    return {
        "id": element_id,
        "type": label,
        "entityId": entity_id,
        "label": f"{label} {entity_id}",
        "properties": props,
    }


def _edge_payload(source: str, target: str, rel_type: str) -> dict:
    return {
        "id": f"{source}|{target}|{rel_type}",
        "source": source,
        "target": target,
        "type": rel_type,
    }


def _merge_overview_into(
    session,
    nodes: dict[str, dict],
    edges: dict[str, dict],
    overview_limit: int,
) -> None:
    """Sample a broad subgraph so the canvas stays full; focused path merges on top."""
    rows = session.run(
        """
        MATCH (n)-[r]->(m)
        WITH n, r, m LIMIT $limit
        RETURN elementId(n) AS s_id, n AS s, type(r) AS rel_type,
               elementId(m) AS t_id, m AS t
        """,
        {"limit": overview_limit},
    )
    for row in rows:
        sid = row.get("s_id")
        tid = row.get("t_id")
        s = row.get("s")
        t = row.get("t")
        rel_type = row.get("rel_type")
        if sid and s and sid not in nodes:
            nodes[sid] = _node_payload(s, sid)
        if tid and t and tid not in nodes:
            nodes[tid] = _node_payload(t, tid)
        if sid and tid and rel_type:
            edge = _edge_payload(sid, tid, rel_type)
            edges[edge["id"]] = edge


def _extract_evidence(raw_results: dict[str, Any]) -> dict:
    graph_rows = raw_results.get("graph_results") or []
    evidence_ids: dict[str, list[str]] = {
        "salesOrders": [],
        "deliveries": [],
        "billingDocuments": [],
        "journalEntries": [],
        "payments": [],
    }
    flow_paths: list[str] = []

    for row in graph_rows:
        so = row.get("salesOrder")
        d = row.get("delivery")
        bd = row.get("billingDoc")
        je = row.get("journalEntry")
        pay = row.get("payment")

        if so:
            evidence_ids["salesOrders"].append(str(so))
        if d:
            evidence_ids["deliveries"].append(str(d))
        if bd:
            evidence_ids["billingDocuments"].append(str(bd))
        if je:
            evidence_ids["journalEntries"].append(str(je))
        if pay:
            evidence_ids["payments"].append(str(pay))

        parts = []
        if so:
            parts.append(f"SalesOrder {so}")
        if d:
            parts.append(f"Delivery {d}")
        if bd:
            parts.append(f"BillingDocument {bd}")
        if je:
            parts.append(f"JournalEntry {je}")
        if pay:
            parts.append(f"Payment {pay}")
        if parts:
            flow_paths.append(" -> ".join(parts))

    for key in evidence_ids:
        evidence_ids[key] = sorted(set(evidence_ids[key]))
    flow_paths = sorted(set(flow_paths))

    return {
        "entity_ids": evidence_ids,
        "flow_paths": flow_paths,
        "graph_row_count": len(graph_rows),
    }


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/ask", response_model=AskResponse)
def ask_route(payload: AskRequest) -> AskResponse:
    validation = validate_query(payload.query)
    if not validation.is_valid:
        return AskResponse(ok=False, answer=validation.message)

    result = ask(payload.query)
    evidence = _extract_evidence(result.get("raw_results", {}))
    return AskResponse(
        ok=True,
        answer=result.get("answer", ""),
        category=result.get("category", ""),
        strategy=result.get("strategy", ""),
        details={
            "subcategory": result.get("subcategory", ""),
            "entity_ids": result.get("entity_ids", {}),
            "description": result.get("description", ""),
            "evidence": evidence,
        },
    )


@router.get("/graph/subgraph")
def graph_subgraph(
    sales_order: str | None = None,
    delivery_document: str | None = None,
    billing_document: str | None = None,
    journal_document: str | None = None,
    limit: int = Query(default=220, ge=20, le=1200),
) -> dict:
    """Return graph payload for visualization.

    Always includes a sampled overview subgraph. When an entity id is provided, the
    matching O2C chain is merged in and marked in ``highlightNodeIds`` /
    ``highlightEdgeIds`` (the rest of the graph stays visible).
    """
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}
    highlight_node_ids: set[str] = set()
    highlight_edge_ids: set[str] = set()

    with get_session() as session:
        _merge_overview_into(session, nodes, edges, limit)

        if sales_order:
            rows = session.run(
                """
                MATCH (c:Customer)-[:PLACED]->(so:SalesOrder {salesOrder: $salesOrder})
                OPTIONAL MATCH (so)-[:HAS_ITEM]->(soi:SalesOrderItem)
                OPTIONAL MATCH (soi)-[:MAPS_TO]->(di:DeliveryItem)-[:PART_OF]->(d:Delivery)
                OPTIONAL MATCH (d)-[:BILLED_AS]->(bd:BillingDocument)
                OPTIONAL MATCH (bd)-[:RECORDED_AS]->(je:JournalEntry)
                OPTIONAL MATCH (je)-[:CLEARED_BY]->(pay:Payment)
                RETURN elementId(c) AS c_id, c,
                       elementId(so) AS so_id, so,
                       elementId(soi) AS soi_id, soi,
                       elementId(di) AS di_id, di,
                       elementId(d) AS d_id, d,
                       elementId(bd) AS bd_id, bd,
                       elementId(je) AS je_id, je,
                       elementId(pay) AS pay_id, pay
                LIMIT $limit
                """,
                {"salesOrder": sales_order, "limit": limit},
            )

            for row in rows:
                row_nodes = [
                    (row.get("c_id"), row.get("c")),
                    (row.get("so_id"), row.get("so")),
                    (row.get("soi_id"), row.get("soi")),
                    (row.get("di_id"), row.get("di")),
                    (row.get("d_id"), row.get("d")),
                    (row.get("bd_id"), row.get("bd")),
                    (row.get("je_id"), row.get("je")),
                    (row.get("pay_id"), row.get("pay")),
                ]
                for node_id, node_obj in row_nodes:
                    if node_id and node_obj and node_id not in nodes:
                        nodes[node_id] = _node_payload(node_obj, node_id)

                rels = [
                    (row.get("c_id"), row.get("so_id"), "PLACED"),
                    (row.get("so_id"), row.get("soi_id"), "HAS_ITEM"),
                    (row.get("soi_id"), row.get("di_id"), "MAPS_TO"),
                    (row.get("di_id"), row.get("d_id"), "PART_OF"),
                    (row.get("d_id"), row.get("bd_id"), "BILLED_AS"),
                    (row.get("bd_id"), row.get("je_id"), "RECORDED_AS"),
                    (row.get("je_id"), row.get("pay_id"), "CLEARED_BY"),
                ]
                for src, tgt, rel_type in rels:
                    if src and tgt:
                        edge = _edge_payload(src, tgt, rel_type)
                        edges[edge["id"]] = edge

                path_node_ids = [
                    row.get("so_id"),
                    row.get("d_id"),
                    row.get("bd_id"),
                    row.get("je_id"),
                    row.get("pay_id"),
                ]
                for node_id in path_node_ids:
                    if node_id:
                        highlight_node_ids.add(node_id)

                path_edges = [
                    (row.get("so_id"), row.get("soi_id"), "HAS_ITEM"),
                    (row.get("soi_id"), row.get("di_id"), "MAPS_TO"),
                    (row.get("di_id"), row.get("d_id"), "PART_OF"),
                    (row.get("d_id"), row.get("bd_id"), "BILLED_AS"),
                    (row.get("bd_id"), row.get("je_id"), "RECORDED_AS"),
                    (row.get("je_id"), row.get("pay_id"), "CLEARED_BY"),
                ]
                for src, tgt, rel_type in path_edges:
                    if src and tgt:
                        highlight_edge_ids.add(f"{src}|{tgt}|{rel_type}")

        elif delivery_document:
            rows = session.run(
                """
                MATCH (di:DeliveryItem)-[:PART_OF]->(d:Delivery {deliveryDocument: $deliveryDocument})
                OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
                OPTIONAL MATCH (so:SalesOrder)-[:HAS_ITEM]->(soi)
                OPTIONAL MATCH (c:Customer)-[:PLACED]->(so)
                OPTIONAL MATCH (d)-[:BILLED_AS]->(bd:BillingDocument)
                OPTIONAL MATCH (bd)-[:RECORDED_AS]->(je:JournalEntry)
                OPTIONAL MATCH (je)-[:CLEARED_BY]->(pay:Payment)
                RETURN elementId(c) AS c_id, c,
                       elementId(so) AS so_id, so,
                       elementId(soi) AS soi_id, soi,
                       elementId(di) AS di_id, di,
                       elementId(d) AS d_id, d,
                       elementId(bd) AS bd_id, bd,
                       elementId(je) AS je_id, je,
                       elementId(pay) AS pay_id, pay
                LIMIT $limit
                """,
                {"deliveryDocument": delivery_document, "limit": limit},
            )
            for row in rows:
                row_nodes = [
                    (row.get("c_id"), row.get("c")),
                    (row.get("so_id"), row.get("so")),
                    (row.get("soi_id"), row.get("soi")),
                    (row.get("di_id"), row.get("di")),
                    (row.get("d_id"), row.get("d")),
                    (row.get("bd_id"), row.get("bd")),
                    (row.get("je_id"), row.get("je")),
                    (row.get("pay_id"), row.get("pay")),
                ]
                for node_id, node_obj in row_nodes:
                    if node_id and node_obj and node_id not in nodes:
                        nodes[node_id] = _node_payload(node_obj, node_id)

                rels = [
                    (row.get("c_id"), row.get("so_id"), "PLACED"),
                    (row.get("so_id"), row.get("soi_id"), "HAS_ITEM"),
                    (row.get("soi_id"), row.get("di_id"), "MAPS_TO"),
                    (row.get("di_id"), row.get("d_id"), "PART_OF"),
                    (row.get("d_id"), row.get("bd_id"), "BILLED_AS"),
                    (row.get("bd_id"), row.get("je_id"), "RECORDED_AS"),
                    (row.get("je_id"), row.get("pay_id"), "CLEARED_BY"),
                ]
                for src, tgt, rel_type in rels:
                    if src and tgt:
                        edge = _edge_payload(src, tgt, rel_type)
                        edges[edge["id"]] = edge

                for node_id in [
                    row.get("so_id"),
                    row.get("d_id"),
                    row.get("bd_id"),
                    row.get("je_id"),
                    row.get("pay_id"),
                ]:
                    if node_id:
                        highlight_node_ids.add(node_id)

                path_edges = [
                    (row.get("so_id"), row.get("soi_id"), "HAS_ITEM"),
                    (row.get("soi_id"), row.get("di_id"), "MAPS_TO"),
                    (row.get("di_id"), row.get("d_id"), "PART_OF"),
                    (row.get("d_id"), row.get("bd_id"), "BILLED_AS"),
                    (row.get("bd_id"), row.get("je_id"), "RECORDED_AS"),
                    (row.get("je_id"), row.get("pay_id"), "CLEARED_BY"),
                ]
                for src, tgt, rel_type in path_edges:
                    if src and tgt:
                        highlight_edge_ids.add(f"{src}|{tgt}|{rel_type}")

        elif billing_document:
            rows = session.run(
                """
                MATCH (bd:BillingDocument {billingDocument: $billingDocument})
                OPTIONAL MATCH (d:Delivery)-[:BILLED_AS]->(bd)
                OPTIONAL MATCH (di:DeliveryItem)-[:PART_OF]->(d)
                OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
                OPTIONAL MATCH (so:SalesOrder)-[:HAS_ITEM]->(soi)
                OPTIONAL MATCH (c:Customer)-[:PLACED]->(so)
                OPTIONAL MATCH (bd)-[:RECORDED_AS]->(je:JournalEntry)
                OPTIONAL MATCH (je)-[:CLEARED_BY]->(pay:Payment)
                RETURN elementId(c) AS c_id, c,
                       elementId(so) AS so_id, so,
                       elementId(soi) AS soi_id, soi,
                       elementId(di) AS di_id, di,
                       elementId(d) AS d_id, d,
                       elementId(bd) AS bd_id, bd,
                       elementId(je) AS je_id, je,
                       elementId(pay) AS pay_id, pay
                LIMIT $limit
                """,
                {"billingDocument": billing_document, "limit": limit},
            )
            for row in rows:
                row_nodes = [
                    (row.get("c_id"), row.get("c")),
                    (row.get("so_id"), row.get("so")),
                    (row.get("soi_id"), row.get("soi")),
                    (row.get("di_id"), row.get("di")),
                    (row.get("d_id"), row.get("d")),
                    (row.get("bd_id"), row.get("bd")),
                    (row.get("je_id"), row.get("je")),
                    (row.get("pay_id"), row.get("pay")),
                ]
                for node_id, node_obj in row_nodes:
                    if node_id and node_obj and node_id not in nodes:
                        nodes[node_id] = _node_payload(node_obj, node_id)

                rels = [
                    (row.get("c_id"), row.get("so_id"), "PLACED"),
                    (row.get("so_id"), row.get("soi_id"), "HAS_ITEM"),
                    (row.get("soi_id"), row.get("di_id"), "MAPS_TO"),
                    (row.get("di_id"), row.get("d_id"), "PART_OF"),
                    (row.get("d_id"), row.get("bd_id"), "BILLED_AS"),
                    (row.get("bd_id"), row.get("je_id"), "RECORDED_AS"),
                    (row.get("je_id"), row.get("pay_id"), "CLEARED_BY"),
                ]
                for src, tgt, rel_type in rels:
                    if src and tgt:
                        edge = _edge_payload(src, tgt, rel_type)
                        edges[edge["id"]] = edge

                for node_id in [
                    row.get("so_id"),
                    row.get("d_id"),
                    row.get("bd_id"),
                    row.get("je_id"),
                    row.get("pay_id"),
                ]:
                    if node_id:
                        highlight_node_ids.add(node_id)

                path_edges = [
                    (row.get("so_id"), row.get("soi_id"), "HAS_ITEM"),
                    (row.get("soi_id"), row.get("di_id"), "MAPS_TO"),
                    (row.get("di_id"), row.get("d_id"), "PART_OF"),
                    (row.get("d_id"), row.get("bd_id"), "BILLED_AS"),
                    (row.get("bd_id"), row.get("je_id"), "RECORDED_AS"),
                    (row.get("je_id"), row.get("pay_id"), "CLEARED_BY"),
                ]
                for src, tgt, rel_type in path_edges:
                    if src and tgt:
                        highlight_edge_ids.add(f"{src}|{tgt}|{rel_type}")

        elif journal_document:
            rows = session.run(
                """
                MATCH (je:JournalEntry)
                WHERE je.accountingDocument = $journalDocument
                   OR toString(je.referenceDocument) = $journalDocument
                   OR je.referenceDocument = $journalDocument
                WITH je LIMIT 1
                OPTIONAL MATCH (bd:BillingDocument)-[:RECORDED_AS]->(je)
                OPTIONAL MATCH (d:Delivery)-[:BILLED_AS]->(bd)
                OPTIONAL MATCH (di:DeliveryItem)-[:PART_OF]->(d)
                OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
                OPTIONAL MATCH (so:SalesOrder)-[:HAS_ITEM]->(soi)
                OPTIONAL MATCH (c:Customer)-[:PLACED]->(so)
                OPTIONAL MATCH (je)-[:CLEARED_BY]->(pay:Payment)
                RETURN elementId(c) AS c_id, c,
                       elementId(so) AS so_id, so,
                       elementId(soi) AS soi_id, soi,
                       elementId(di) AS di_id, di,
                       elementId(d) AS d_id, d,
                       elementId(bd) AS bd_id, bd,
                       elementId(je) AS je_id, je,
                       elementId(pay) AS pay_id, pay
                LIMIT $limit
                """,
                {"journalDocument": journal_document, "limit": limit},
            )
            for row in rows:
                row_nodes = [
                    (row.get("c_id"), row.get("c")),
                    (row.get("so_id"), row.get("so")),
                    (row.get("soi_id"), row.get("soi")),
                    (row.get("di_id"), row.get("di")),
                    (row.get("d_id"), row.get("d")),
                    (row.get("bd_id"), row.get("bd")),
                    (row.get("je_id"), row.get("je")),
                    (row.get("pay_id"), row.get("pay")),
                ]
                for node_id, node_obj in row_nodes:
                    if node_id and node_obj and node_id not in nodes:
                        nodes[node_id] = _node_payload(node_obj, node_id)

                rels = [
                    (row.get("c_id"), row.get("so_id"), "PLACED"),
                    (row.get("so_id"), row.get("soi_id"), "HAS_ITEM"),
                    (row.get("soi_id"), row.get("di_id"), "MAPS_TO"),
                    (row.get("di_id"), row.get("d_id"), "PART_OF"),
                    (row.get("d_id"), row.get("bd_id"), "BILLED_AS"),
                    (row.get("bd_id"), row.get("je_id"), "RECORDED_AS"),
                    (row.get("je_id"), row.get("pay_id"), "CLEARED_BY"),
                ]
                for src, tgt, rel_type in rels:
                    if src and tgt:
                        edge = _edge_payload(src, tgt, rel_type)
                        edges[edge["id"]] = edge

                for node_id in [
                    row.get("so_id"),
                    row.get("d_id"),
                    row.get("bd_id"),
                    row.get("je_id"),
                    row.get("pay_id"),
                ]:
                    if node_id:
                        highlight_node_ids.add(node_id)

                path_edges = [
                    (row.get("so_id"), row.get("soi_id"), "HAS_ITEM"),
                    (row.get("soi_id"), row.get("di_id"), "MAPS_TO"),
                    (row.get("di_id"), row.get("d_id"), "PART_OF"),
                    (row.get("d_id"), row.get("bd_id"), "BILLED_AS"),
                    (row.get("bd_id"), row.get("je_id"), "RECORDED_AS"),
                    (row.get("je_id"), row.get("pay_id"), "CLEARED_BY"),
                ]
                for src, tgt, rel_type in path_edges:
                    if src and tgt:
                        highlight_edge_ids.add(f"{src}|{tgt}|{rel_type}")

    return {
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
        "highlightNodeIds": sorted(highlight_node_ids),
        "highlightEdgeIds": sorted(highlight_edge_ids),
        "meta": {
            "focused": {
                "salesOrder": sales_order,
                "deliveryDocument": delivery_document,
                "billingDocument": billing_document,
                "journalDocument": journal_document,
            },
            "counts": {
                "nodes": len(nodes),
                "edges": len(edges),
            },
        },
    }


@router.get("/flow/sales-order/{sales_order}")
def flow_by_sales_order(sales_order: str) -> dict:
    flows = trace_by_sales_order(sales_order)
    return {
        "salesOrder": sales_order,
        "count": len(flows),
        "flows": [f.to_dict() for f in flows],
    }


@router.get("/flow/delivery/{delivery_document}")
def flow_by_delivery(delivery_document: str) -> dict:
    flows = trace_by_delivery(delivery_document)
    return {
        "deliveryDocument": delivery_document,
        "count": len(flows),
        "flows": [f.to_dict() for f in flows],
    }


@router.get("/flow/billing/{billing_document}")
def flow_by_billing(billing_document: str) -> dict:
    flows = trace_by_billing(billing_document)
    return {
        "billingDocument": billing_document,
        "count": len(flows),
        "flows": [f.to_dict() for f in flows],
    }


@router.get("/flow/broken")
def broken_flows() -> dict:
    return detect_all()

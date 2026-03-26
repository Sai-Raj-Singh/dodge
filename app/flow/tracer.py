"""Flow tracer — traces complete document flow paths through the Neo4j graph.

Provides structured flow tracing for the core O2C path:
  SalesOrder → Delivery → Billing → JournalEntry → Payment
"""

from dataclasses import dataclass, field

from app.graph.connection import get_session
from app.graph import queries as Q


@dataclass
class FlowStep:
    """A single step in a document flow."""

    entity_type: str
    entity_id: str
    properties: dict = field(default_factory=dict)


@dataclass
class FlowPath:
    """A complete document flow path."""

    sales_order: str
    customer: str
    customer_name: str
    steps: list[FlowStep] = field(default_factory=list)
    status: str = ""  # COMPLETE, DELIVERED_NOT_BILLED, BILLED_NOT_PAID, ORDERED_ONLY

    @property
    def is_complete(self) -> bool:
        return self.status == "COMPLETE"

    def to_arrow_string(self) -> str:
        """Render the flow as an arrow path string."""
        parts = []
        for step in self.steps:
            parts.append(f"{step.entity_type} {step.entity_id}")
        return " -> ".join(parts)

    def to_dict(self) -> dict:
        return {
            "salesOrder": self.sales_order,
            "customer": self.customer,
            "customerName": self.customer_name,
            "status": self.status,
            "flowPath": self.to_arrow_string(),
            "steps": [
                {
                    "entityType": s.entity_type,
                    "entityId": s.entity_id,
                    "properties": s.properties,
                }
                for s in self.steps
            ],
        }


def trace_by_sales_order(sales_order: str) -> list[FlowPath]:
    """Trace all document flow paths originating from a sales order.

    A single sales order can produce multiple flow paths (one per item
    that maps to a different delivery/billing chain).

    Returns:
        List of FlowPath objects.
    """
    with get_session() as session:
        result = session.run(Q.FULL_FLOW_BY_SALES_ORDER, {"salesOrder": sales_order})
        rows = [dict(r) for r in result]

    if not rows:
        return []

    # Group by unique flow chain to deduplicate
    seen = set()
    flows: list[FlowPath] = []

    for row in rows:
        delivery = row.get("delivery") or ""
        billing = row.get("billingDoc") or ""
        je = row.get("journalEntry") or ""
        payment = row.get("payment") or ""

        flow_key = f"{sales_order}_{delivery}_{billing}_{je}_{payment}"
        if flow_key in seen:
            continue
        seen.add(flow_key)

        steps = [
            FlowStep(
                entity_type="SalesOrder",
                entity_id=sales_order,
                properties={
                    "amount": row.get("orderAmount"),
                    "currency": row.get("currency"),
                },
            )
        ]

        if delivery:
            steps.append(
                FlowStep(
                    entity_type="Delivery",
                    entity_id=delivery,
                    properties={
                        "goodsMovementDate": row.get("goodsMovementDate"),
                        "deliveredQty": row.get("deliveredQty"),
                    },
                )
            )
        if billing:
            steps.append(
                FlowStep(
                    entity_type="BillingDocument",
                    entity_id=billing,
                    properties={
                        "billedAmount": row.get("billedAmount"),
                        "isCancelled": row.get("billingCancelled"),
                    },
                )
            )
        if je:
            steps.append(
                FlowStep(
                    entity_type="JournalEntry",
                    entity_id=je,
                    properties={"postingDate": row.get("jePostingDate")},
                )
            )
        if payment:
            steps.append(
                FlowStep(
                    entity_type="Payment",
                    entity_id=payment,
                    properties={
                        "postingDate": row.get("paymentDate"),
                        "amount": row.get("paymentAmount"),
                    },
                )
            )

        # Determine status
        if payment:
            status = "COMPLETE"
        elif je:
            status = "BILLED_NOT_PAID"
        elif billing:
            cancelled = row.get("billingCancelled", False)
            status = "BILLING_CANCELLED" if cancelled else "BILLED"
        elif delivery:
            status = "DELIVERED_NOT_BILLED"
        else:
            status = "ORDERED_ONLY"

        flows.append(
            FlowPath(
                sales_order=sales_order,
                customer=row.get("customer", ""),
                customer_name=row.get("customerName", ""),
                steps=steps,
                status=status,
            )
        )

    return flows


def trace_by_delivery(delivery_document: str) -> list[FlowPath]:
    """Trace document flow paths involving a specific delivery."""
    with get_session() as session:
        result = session.run(
            Q.FULL_FLOW_BY_DELIVERY, {"deliveryDocument": delivery_document}
        )
        rows = [dict(r) for r in result]

    if not rows:
        return []

    seen = set()
    flows: list[FlowPath] = []

    for row in rows:
        so = row.get("salesOrder") or ""
        billing = row.get("billingDoc") or ""
        je = row.get("journalEntry") or ""
        payment = row.get("payment") or ""

        flow_key = f"{so}_{delivery_document}_{billing}_{je}_{payment}"
        if flow_key in seen:
            continue
        seen.add(flow_key)

        steps = []
        if so:
            steps.append(FlowStep(entity_type="SalesOrder", entity_id=so))
        steps.append(FlowStep(entity_type="Delivery", entity_id=delivery_document))
        if billing:
            steps.append(FlowStep(entity_type="BillingDocument", entity_id=billing))
        if je:
            steps.append(FlowStep(entity_type="JournalEntry", entity_id=je))
        if payment:
            steps.append(FlowStep(entity_type="Payment", entity_id=payment))

        if payment:
            status = "COMPLETE"
        elif je:
            status = "BILLED_NOT_PAID"
        elif billing:
            status = "BILLED"
        else:
            status = "DELIVERED_NOT_BILLED"

        flows.append(
            FlowPath(
                sales_order=so,
                customer=row.get("customer", ""),
                customer_name=row.get("customerName", ""),
                steps=steps,
                status=status,
            )
        )

    return flows


def trace_by_billing(billing_document: str) -> list[FlowPath]:
    """Trace document flow paths involving a specific billing document."""
    with get_session() as session:
        result = session.run(
            Q.FULL_FLOW_BY_BILLING, {"billingDocument": billing_document}
        )
        rows = [dict(r) for r in result]

    if not rows:
        return []

    seen = set()
    flows: list[FlowPath] = []

    for row in rows:
        so = row.get("salesOrder") or ""
        delivery = row.get("delivery") or ""
        je = row.get("journalEntry") or ""
        payment = row.get("payment") or ""

        flow_key = f"{so}_{delivery}_{billing_document}_{je}_{payment}"
        if flow_key in seen:
            continue
        seen.add(flow_key)

        steps = []
        if so:
            steps.append(FlowStep(entity_type="SalesOrder", entity_id=so))
        if delivery:
            steps.append(FlowStep(entity_type="Delivery", entity_id=delivery))
        steps.append(
            FlowStep(
                entity_type="BillingDocument",
                entity_id=billing_document,
                properties={"billedAmount": row.get("billedAmount")},
            )
        )
        if je:
            steps.append(FlowStep(entity_type="JournalEntry", entity_id=je))
        if payment:
            steps.append(FlowStep(entity_type="Payment", entity_id=payment))

        if payment:
            status = "COMPLETE"
        elif je:
            status = "BILLED_NOT_PAID"
        else:
            status = "BILLED"

        flows.append(
            FlowPath(
                sales_order=so,
                customer=row.get("customer", ""),
                customer_name=row.get("customerName", ""),
                steps=steps,
                status=status,
            )
        )

    return flows

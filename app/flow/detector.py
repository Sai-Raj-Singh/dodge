"""Broken flow detector — finds incomplete document flows in the graph.

Detects:
  - Delivered but not billed (goods shipped, no invoice raised)
  - Billed but not paid (invoice exists, no payment clearing)
  - Ordered but not delivered (order placed, no shipment)
"""

from dataclasses import dataclass

from app.graph.connection import get_session
from app.graph import queries as Q


@dataclass
class BrokenFlow:
    """A single broken flow entry."""

    break_type: str  # delivered_not_billed, billed_not_paid, ordered_not_delivered
    sales_order: str
    delivery: str
    billing_document: str
    journal_entry: str
    amount: str
    currency: str
    extra: dict

    def to_dict(self) -> dict:
        return {
            "breakType": self.break_type,
            "salesOrder": self.sales_order,
            "delivery": self.delivery,
            "billingDocument": self.billing_document,
            "journalEntry": self.journal_entry,
            "amount": self.amount,
            "currency": self.currency,
            **self.extra,
        }


def find_delivered_not_billed() -> list[BrokenFlow]:
    """Find deliveries that have no corresponding billing document."""
    with get_session() as session:
        result = session.run(Q.DELIVERED_NOT_BILLED, {})
        rows = [dict(r) for r in result]

    flows = []
    for row in rows:
        flows.append(
            BrokenFlow(
                break_type="delivered_not_billed",
                sales_order=row.get("salesOrder") or "",
                delivery=row.get("delivery") or "",
                billing_document="",
                journal_entry="",
                amount="",
                currency="",
                extra={
                    "deliveryDate": row.get("deliveryDate") or "",
                    "goodsMovementStatus": row.get("goodsMovementStatus") or "",
                },
            )
        )
    return flows


def find_billed_not_paid() -> list[BrokenFlow]:
    """Find billing documents with journal entries but no clearing payment."""
    with get_session() as session:
        result = session.run(Q.BILLED_NOT_PAID, {})
        rows = [dict(r) for r in result]

    flows = []
    for row in rows:
        flows.append(
            BrokenFlow(
                break_type="billed_not_paid",
                sales_order=row.get("salesOrder") or "",
                delivery=row.get("delivery") or "",
                billing_document=row.get("billingDoc") or "",
                journal_entry=row.get("journalEntry") or "",
                amount=row.get("billedAmount") or "",
                currency=row.get("currency") or "",
                extra={
                    "jePostingDate": row.get("jePostingDate") or "",
                },
            )
        )
    return flows


ORDERED_NOT_DELIVERED = """
MATCH (c:Customer)-[:PLACED]->(so:SalesOrder)
WHERE NOT (so)-[:HAS_ITEM]->(:SalesOrderItem)-[:MAPS_TO]->(:DeliveryItem)
RETURN DISTINCT
       so.salesOrder AS salesOrder,
       so.totalNetAmount AS amount,
       so.transactionCurrency AS currency,
       so.creationDate AS orderDate,
       so.overallDeliveryStatus AS deliveryStatus,
       c.businessPartner AS customer,
       c.fullName AS customerName
ORDER BY so.salesOrder
"""


def find_ordered_not_delivered() -> list[BrokenFlow]:
    """Find sales orders with no delivery items mapped."""
    with get_session() as session:
        result = session.run(ORDERED_NOT_DELIVERED, {})
        rows = [dict(r) for r in result]

    flows = []
    for row in rows:
        flows.append(
            BrokenFlow(
                break_type="ordered_not_delivered",
                sales_order=row.get("salesOrder") or "",
                delivery="",
                billing_document="",
                journal_entry="",
                amount=row.get("amount") or "",
                currency=row.get("currency") or "",
                extra={
                    "orderDate": row.get("orderDate") or "",
                    "deliveryStatus": row.get("deliveryStatus") or "",
                    "customer": row.get("customer") or "",
                    "customerName": row.get("customerName") or "",
                },
            )
        )
    return flows


def detect_all() -> dict:
    """Run all broken flow detections and return a summary.

    Returns:
        dict with keys: delivered_not_billed, billed_not_paid,
                        ordered_not_delivered, summary
    """
    dnb = find_delivered_not_billed()
    bnp = find_billed_not_paid()
    ond = find_ordered_not_delivered()

    return {
        "delivered_not_billed": [f.to_dict() for f in dnb],
        "billed_not_paid": [f.to_dict() for f in bnp],
        "ordered_not_delivered": [f.to_dict() for f in ond],
        "summary": {
            "delivered_not_billed_count": len(dnb),
            "billed_not_paid_count": len(bnp),
            "ordered_not_delivered_count": len(ond),
            "total_broken": len(dnb) + len(bnp) + len(ond),
        },
    }

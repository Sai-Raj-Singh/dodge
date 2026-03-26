"""Create Neo4j indexes for fast lookups on key entity properties."""

from app.graph.connection import get_session


# Index definitions: (index_name, label, property)
INDEX_DEFINITIONS = [
    ("idx_salesorder_id", "SalesOrder", "salesOrder"),
    ("idx_delivery_id", "Delivery", "deliveryDocument"),
    ("idx_billing_id", "BillingDocument", "billingDocument"),
    ("idx_customer_bp", "Customer", "businessPartner"),
    ("idx_product_id", "Product", "product"),
    ("idx_plant_id", "Plant", "plant"),
    ("idx_journal_acctdoc", "JournalEntry", "accountingDocument"),
    ("idx_payment_acctdoc", "Payment", "accountingDocument"),
    ("idx_salesorderitem_so", "SalesOrderItem", "salesOrder"),
    ("idx_deliveryitem_del", "DeliveryItem", "deliveryDocument"),
    ("idx_deliveryitem_refsd", "DeliveryItem", "referenceSdDocument"),
    ("idx_billingitem_bd", "BillingItem", "billingDocument"),
    ("idx_billingitem_refsd", "BillingItem", "referenceSdDocument"),
]


def create_indexes() -> int:
    """Create all indexes in Neo4j. Skips if they already exist.

    Returns:
        Number of indexes created.
    """
    created = 0
    with get_session() as session:
        for idx_name, label, prop in INDEX_DEFINITIONS:
            try:
                cypher = (
                    f"CREATE INDEX {idx_name} IF NOT EXISTS "
                    f"FOR (n:{label}) ON (n.{prop})"
                )
                session.run(cypher)
                created += 1
                print(f"  [IDX] {idx_name}: {label}.{prop}")
            except Exception as e:
                print(f"  [WARN] Index {idx_name} failed: {e}")

    print(f"\n[INDEX] {created}/{len(INDEX_DEFINITIONS)} indexes ensured.")
    return created


def drop_indexes() -> None:
    """Drop all project indexes."""
    with get_session() as session:
        for idx_name, _, _ in INDEX_DEFINITIONS:
            try:
                session.run(f"DROP INDEX {idx_name} IF EXISTS")
            except Exception:
                pass
    print("[INDEX] All indexes dropped.")

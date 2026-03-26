"""Normalize raw JSONL records into typed Pydantic entity instances.

This module takes the raw dict output from loader.py and produces
clean, validated entity objects ready for graph construction.
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.ingestion.loader import load_all_folders
from app.ingestion.schemas import (
    Address,
    BillingDocument,
    BillingItem,
    Customer,
    Delivery,
    DeliveryItem,
    JournalEntry,
    Payment,
    Plant,
    Product,
    SalesOrder,
    SalesOrderItem,
)


@dataclass
class NormalizedData:
    """Container holding all normalized entities."""

    # Core transactional
    sales_orders: list[SalesOrder] = field(default_factory=list)
    sales_order_items: list[SalesOrderItem] = field(default_factory=list)
    deliveries: list[Delivery] = field(default_factory=list)
    delivery_items: list[DeliveryItem] = field(default_factory=list)
    billing_documents: list[BillingDocument] = field(default_factory=list)
    billing_items: list[BillingItem] = field(default_factory=list)
    journal_entries: list[JournalEntry] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)

    # Supporting / master data
    customers: list[Customer] = field(default_factory=list)
    addresses: list[Address] = field(default_factory=list)
    products: list[Product] = field(default_factory=list)
    plants: list[Plant] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        return {
            "SalesOrder": len(self.sales_orders),
            "SalesOrderItem": len(self.sales_order_items),
            "Delivery": len(self.deliveries),
            "DeliveryItem": len(self.delivery_items),
            "BillingDocument": len(self.billing_documents),
            "BillingItem": len(self.billing_items),
            "JournalEntry": len(self.journal_entries),
            "Payment": len(self.payments),
            "Customer": len(self.customers),
            "Address": len(self.addresses),
            "Product": len(self.products),
            "Plant": len(self.plants),
        }


def _parse_list(model_cls, records: list[dict], label: str) -> list:
    """Validate a list of raw dicts into Pydantic model instances."""
    results = []
    errors = 0
    for rec in records:
        try:
            results.append(model_cls.model_validate(rec))
        except Exception as e:
            errors += 1
            if errors <= 3:  # only print first few
                print(f"  [WARN] {label} parse error: {e}")
    if errors:
        print(f"  [WARN] {label}: {errors}/{len(records)} records skipped")
    return results


def _build_product_description_map(
    product_descriptions: list[dict],
) -> dict[str, str]:
    """Build product -> English description lookup."""
    desc_map: dict[str, str] = {}
    for rec in product_descriptions:
        pid = rec.get("product", "")
        lang = rec.get("language", "")
        desc = rec.get("productDescription", "")
        # Prefer English, but take any if English not available
        if lang.upper() == "EN" or pid not in desc_map:
            if desc:
                desc_map[pid] = desc
    return desc_map


def normalize(raw: dict[str, list[dict]]) -> NormalizedData:
    """Convert raw dataset dicts into validated entity objects.

    Args:
        raw: Output of loader.load_all_folders().

    Returns:
        NormalizedData with all entity lists populated.
    """
    print("\n[NORMALIZE] Starting normalization...")
    data = NormalizedData()

    # ── Supporting / master data ──────────────────────────────────
    data.customers = _parse_list(Customer, raw.get("business_partners", []), "Customer")
    data.addresses = _parse_list(
        Address, raw.get("business_partner_addresses", []), "Address"
    )
    data.plants = _parse_list(Plant, raw.get("plants", []), "Plant")

    # Products: merge with descriptions
    desc_map = _build_product_description_map(raw.get("product_descriptions", []))
    product_records = raw.get("products", [])
    for rec in product_records:
        pid = rec.get("product", "")
        if pid in desc_map:
            rec["product_description"] = desc_map[pid]
    data.products = _parse_list(Product, product_records, "Product")

    # ── Core transactional ────────────────────────────────────────
    data.sales_orders = _parse_list(
        SalesOrder, raw.get("sales_order_headers", []), "SalesOrder"
    )
    data.sales_order_items = _parse_list(
        SalesOrderItem, raw.get("sales_order_items", []), "SalesOrderItem"
    )
    data.deliveries = _parse_list(
        Delivery, raw.get("outbound_delivery_headers", []), "Delivery"
    )
    data.delivery_items = _parse_list(
        DeliveryItem, raw.get("outbound_delivery_items", []), "DeliveryItem"
    )

    # Billing: merge headers + cancellations into one list
    billing_headers = raw.get("billing_document_headers", [])
    billing_cancellations = raw.get("billing_document_cancellations", [])
    all_billing = billing_headers + billing_cancellations
    data.billing_documents = _parse_list(
        BillingDocument, all_billing, "BillingDocument"
    )
    data.billing_items = _parse_list(
        BillingItem, raw.get("billing_document_items", []), "BillingItem"
    )

    data.journal_entries = _parse_list(
        JournalEntry,
        raw.get("journal_entry_items_accounts_receivable", []),
        "JournalEntry",
    )
    data.payments = _parse_list(
        Payment, raw.get("payments_accounts_receivable", []), "Payment"
    )

    # ── Summary ───────────────────────────────────────────────────
    print("\n[NORMALIZE] Entity counts:")
    for entity, count in data.summary().items():
        print(f"  {entity:20s} {count:>6,}")
    total = sum(data.summary().values())
    print(f"  {'TOTAL':20s} {total:>6,}")

    return data


def ingest(dataset_path: Path) -> NormalizedData:
    """Full ingestion pipeline: load files → normalize into entities.

    Args:
        dataset_path: Path to the sap-o2c-data/ root folder.

    Returns:
        NormalizedData with all parsed entities.
    """
    raw = load_all_folders(dataset_path)
    return normalize(raw)

"""Build Neo4j graph nodes and relationships from normalized entities.

Uses MERGE with batch operations via UNWIND for performance.
"""

from neo4j import Session

from app.graph.connection import get_session
from app.ingestion.normalizer import NormalizedData


# ─── Node Creation ────────────────────────────────────────────────


def _create_customers(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (c:Customer {businessPartner: r.business_partner})
    SET c.customer = r.customer,
        c.fullName = r.business_partner_full_name,
        c.name = r.business_partner_name,
        c.category = r.business_partner_category,
        c.firstName = r.first_name,
        c.lastName = r.last_name,
        c.industry = r.industry,
        c.orgName1 = r.organization_bp_name1,
        c.isBlocked = r.is_blocked
    """
    rows = [c.model_dump() for c in data.customers]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  Customer nodes: {count} created")
    return count


def _create_addresses(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (a:Address {businessPartner: r.business_partner, addressId: r.address_id})
    SET a.cityName = r.city_name,
        a.country = r.country,
        a.postalCode = r.postal_code,
        a.region = r.region,
        a.streetName = r.street_name
    """
    rows = [a.model_dump() for a in data.addresses]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  Address nodes: {count} created")
    return count


def _create_products(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (p:Product {product: r.product})
    SET p.productType = r.product_type,
        p.productGroup = r.product_group,
        p.description = r.product_description,
        p.baseUnit = r.base_unit,
        p.grossWeight = r.gross_weight,
        p.netWeight = r.net_weight,
        p.weightUnit = r.weight_unit,
        p.division = r.division
    """
    rows = [p.model_dump() for p in data.products]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  Product nodes: {count} created")
    return count


def _create_plants(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (pl:Plant {plant: r.plant})
    SET pl.plantName = r.plant_name,
        pl.salesOrganization = r.sales_organization,
        pl.distributionChannel = r.distribution_channel,
        pl.division = r.division,
        pl.plantCategory = r.plant_category
    """
    rows = [p.model_dump() for p in data.plants]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  Plant nodes: {count} created")
    return count


def _create_sales_orders(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (so:SalesOrder {salesOrder: r.sales_order})
    SET so.salesOrderType = r.sales_order_type,
        so.salesOrganization = r.sales_organization,
        so.distributionChannel = r.distribution_channel,
        so.soldToParty = r.sold_to_party,
        so.creationDate = r.creation_date,
        so.totalNetAmount = r.total_net_amount,
        so.transactionCurrency = r.transaction_currency,
        so.requestedDeliveryDate = r.requested_delivery_date,
        so.overallDeliveryStatus = r.overall_delivery_status,
        so.customerPaymentTerms = r.customer_payment_terms,
        so.headerBillingBlockReason = r.header_billing_block_reason,
        so.deliveryBlockReason = r.delivery_block_reason
    """
    rows = [so.model_dump() for so in data.sales_orders]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  SalesOrder nodes: {count} created")
    return count


def _create_sales_order_items(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (soi:SalesOrderItem {salesOrder: r.sales_order, salesOrderItem: r.sales_order_item})
    SET soi.material = r.material,
        soi.requestedQuantity = r.requested_quantity,
        soi.requestedQuantityUnit = r.requested_quantity_unit,
        soi.netAmount = r.net_amount,
        soi.transactionCurrency = r.transaction_currency,
        soi.materialGroup = r.material_group,
        soi.productionPlant = r.production_plant,
        soi.storageLocation = r.storage_location
    """
    rows = [soi.model_dump() for soi in data.sales_order_items]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  SalesOrderItem nodes: {count} created")
    return count


def _create_deliveries(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (d:Delivery {deliveryDocument: r.delivery_document})
    SET d.shippingPoint = r.shipping_point,
        d.creationDate = r.creation_date,
        d.actualGoodsMovementDate = r.actual_goods_movement_date,
        d.overallGoodsMovementStatus = r.overall_goods_movement_status,
        d.overallPickingStatus = r.overall_picking_status,
        d.deliveryBlockReason = r.delivery_block_reason,
        d.headerBillingBlockReason = r.header_billing_block_reason
    """
    rows = [d.model_dump() for d in data.deliveries]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  Delivery nodes: {count} created")
    return count


def _create_delivery_items(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (di:DeliveryItem {deliveryDocument: r.delivery_document,
                            deliveryDocumentItem: r.delivery_document_item})
    SET di.referenceSdDocument = r.reference_sd_document,
        di.referenceSdDocumentItem = r.reference_sd_document_item,
        di.actualDeliveryQuantity = r.actual_delivery_quantity,
        di.deliveryQuantityUnit = r.delivery_quantity_unit,
        di.plant = r.plant,
        di.storageLocation = r.storage_location,
        di.batch = r.batch
    """
    rows = [di.model_dump() for di in data.delivery_items]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  DeliveryItem nodes: {count} created")
    return count


def _create_billing_documents(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (bd:BillingDocument {billingDocument: r.billing_document})
    SET bd.billingDocumentType = r.billing_document_type,
        bd.creationDate = r.creation_date,
        bd.billingDocumentDate = r.billing_document_date,
        bd.isCancelled = r.billing_document_is_cancelled,
        bd.cancelledBillingDocument = r.cancelled_billing_document,
        bd.totalNetAmount = r.total_net_amount,
        bd.transactionCurrency = r.transaction_currency,
        bd.companyCode = r.company_code,
        bd.fiscalYear = r.fiscal_year,
        bd.accountingDocument = r.accounting_document,
        bd.soldToParty = r.sold_to_party
    """
    rows = [bd.model_dump() for bd in data.billing_documents]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  BillingDocument nodes: {count} created")
    return count


def _create_billing_items(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (bi:BillingItem {billingDocument: r.billing_document,
                           billingDocumentItem: r.billing_document_item})
    SET bi.material = r.material,
        bi.billingQuantity = r.billing_quantity,
        bi.billingQuantityUnit = r.billing_quantity_unit,
        bi.netAmount = r.net_amount,
        bi.transactionCurrency = r.transaction_currency,
        bi.referenceSdDocument = r.reference_sd_document,
        bi.referenceSdDocumentItem = r.reference_sd_document_item
    """
    rows = [bi.model_dump() for bi in data.billing_items]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  BillingItem nodes: {count} created")
    return count


def _create_journal_entries(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (je:JournalEntry {companyCode: r.company_code,
                            fiscalYear: r.fiscal_year,
                            accountingDocument: r.accounting_document})
    ON CREATE SET
        je.accountingDocumentType = r.accounting_document_type,
        je.glAccount = r.gl_account,
        je.customer = r.customer,
        je.referenceDocument = r.reference_document,
        je.amountInTransactionCurrency = r.amount_in_transaction_currency,
        je.transactionCurrency = r.transaction_currency,
        je.postingDate = r.posting_date,
        je.documentDate = r.document_date,
        je.clearingDate = r.clearing_date,
        je.clearingAccountingDocument = r.clearing_accounting_document,
        je.clearingDocFiscalYear = r.clearing_doc_fiscal_year,
        je.profitCenter = r.profit_center,
        je.assignmentReference = r.assignment_reference
    """
    rows = [je.model_dump() for je in data.journal_entries]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  JournalEntry nodes: {count} created")
    return count


def _create_payments(session: Session, data: NormalizedData) -> int:
    query = """
    UNWIND $rows AS r
    MERGE (p:Payment {companyCode: r.company_code,
                      fiscalYear: r.fiscal_year,
                      accountingDocument: r.accounting_document})
    ON CREATE SET
        p.customer = r.customer,
        p.invoiceReference = r.invoice_reference,
        p.invoiceReferenceFiscalYear = r.invoice_reference_fiscal_year,
        p.salesDocument = r.sales_document,
        p.amountInTransactionCurrency = r.amount_in_transaction_currency,
        p.transactionCurrency = r.transaction_currency,
        p.postingDate = r.posting_date,
        p.documentDate = r.document_date,
        p.clearingDate = r.clearing_date,
        p.clearingAccountingDocument = r.clearing_accounting_document,
        p.glAccount = r.gl_account,
        p.profitCenter = r.profit_center,
        p.assignmentReference = r.assignment_reference
    """
    rows = [p.model_dump() for p in data.payments]
    result = session.run(query, rows=rows)
    summary = result.consume()
    count = summary.counters.nodes_created
    print(f"  Payment nodes: {count} created")
    return count


# ─── Relationship Creation ────────────────────────────────────────


def _create_relationships(session: Session) -> None:
    """Create all relationships between existing nodes."""

    rels = [
        # (Customer)-[:PLACED]->(SalesOrder)
        (
            "Customer PLACED SalesOrder",
            """
            MATCH (c:Customer), (so:SalesOrder)
            WHERE c.businessPartner = so.soldToParty
            MERGE (c)-[:PLACED]->(so)
            """,
        ),
        # (SalesOrder)-[:HAS_ITEM]->(SalesOrderItem)
        (
            "SalesOrder HAS_ITEM SalesOrderItem",
            """
            MATCH (so:SalesOrder), (soi:SalesOrderItem)
            WHERE so.salesOrder = soi.salesOrder
            MERGE (so)-[:HAS_ITEM]->(soi)
            """,
        ),
        # (SalesOrderItem)-[:MAPS_TO]->(DeliveryItem)
        # Item numbers have zero-padding mismatch: SOI uses "10", DI uses "000010"
        (
            "SalesOrderItem MAPS_TO DeliveryItem",
            """
            MATCH (soi:SalesOrderItem), (di:DeliveryItem)
            WHERE soi.salesOrder = di.referenceSdDocument
              AND toInteger(soi.salesOrderItem) = toInteger(di.referenceSdDocumentItem)
            MERGE (soi)-[:MAPS_TO]->(di)
            """,
        ),
        # (DeliveryItem)-[:PART_OF]->(Delivery)
        (
            "DeliveryItem PART_OF Delivery",
            """
            MATCH (di:DeliveryItem), (d:Delivery)
            WHERE di.deliveryDocument = d.deliveryDocument
            MERGE (di)-[:PART_OF]->(d)
            """,
        ),
        # (Delivery)-[:BILLED_AS]->(BillingDocument)
        # Link via billing items: billing item references delivery document
        (
            "Delivery BILLED_AS BillingDocument",
            """
            MATCH (d:Delivery), (bi:BillingItem), (bd:BillingDocument)
            WHERE bi.referenceSdDocument = d.deliveryDocument
              AND bi.billingDocument = bd.billingDocument
            MERGE (d)-[:BILLED_AS]->(bd)
            """,
        ),
        # (BillingDocument)-[:RECORDED_AS]->(JournalEntry)
        (
            "BillingDocument RECORDED_AS JournalEntry",
            """
            MATCH (bd:BillingDocument), (je:JournalEntry)
            WHERE bd.accountingDocument = je.accountingDocument
              AND bd.fiscalYear = je.fiscalYear
              AND bd.companyCode = je.companyCode
            MERGE (bd)-[:RECORDED_AS]->(je)
            """,
        ),
        # (JournalEntry)-[:CLEARED_BY]->(Payment)
        (
            "JournalEntry CLEARED_BY Payment",
            """
            MATCH (je:JournalEntry), (p:Payment)
            WHERE je.clearingAccountingDocument = p.accountingDocument
              AND je.clearingDocFiscalYear = p.fiscalYear
              AND je.companyCode = p.companyCode
              AND je.clearingAccountingDocument IS NOT NULL
              AND je.clearingAccountingDocument <> ''
            MERGE (je)-[:CLEARED_BY]->(p)
            """,
        ),
        # (SalesOrderItem)-[:CONTAINS]->(Product)
        (
            "SalesOrderItem CONTAINS Product",
            """
            MATCH (soi:SalesOrderItem), (p:Product)
            WHERE soi.material = p.product
            MERGE (soi)-[:CONTAINS]->(p)
            """,
        ),
        # (Product)-[:LOCATED_AT]->(Plant)
        (
            "Product LOCATED_AT Plant",
            """
            MATCH (soi:SalesOrderItem), (p:Product), (pl:Plant)
            WHERE soi.material = p.product
              AND soi.productionPlant = pl.plant
            MERGE (p)-[:LOCATED_AT]->(pl)
            """,
        ),
        # (Customer)-[:HAS_ADDRESS]->(Address)
        (
            "Customer HAS_ADDRESS Address",
            """
            MATCH (c:Customer), (a:Address)
            WHERE c.businessPartner = a.businessPartner
            MERGE (c)-[:HAS_ADDRESS]->(a)
            """,
        ),
    ]

    for label, cypher in rels:
        result = session.run(cypher)
        summary = result.consume()
        count = summary.counters.relationships_created
        print(f"  {label}: {count} relationships")


# ─── Public API ───────────────────────────────────────────────────


def build_graph(data: NormalizedData) -> dict[str, int]:
    """Create all nodes and relationships in Neo4j.

    Args:
        data: Normalized entity data from the ingestion pipeline.

    Returns:
        Summary dict with node and relationship counts.
    """
    print("\n[GRAPH] Creating nodes...")
    total_nodes = 0

    with get_session() as session:
        total_nodes += _create_customers(session, data)
        total_nodes += _create_addresses(session, data)
        total_nodes += _create_products(session, data)
        total_nodes += _create_plants(session, data)
        total_nodes += _create_sales_orders(session, data)
        total_nodes += _create_sales_order_items(session, data)
        total_nodes += _create_deliveries(session, data)
        total_nodes += _create_delivery_items(session, data)
        total_nodes += _create_billing_documents(session, data)
        total_nodes += _create_billing_items(session, data)
        total_nodes += _create_journal_entries(session, data)
        total_nodes += _create_payments(session, data)

    print(f"\n[GRAPH] Total nodes created: {total_nodes}")

    print("\n[GRAPH] Creating relationships...")
    with get_session() as session:
        _create_relationships(session)

    print("\n[GRAPH] Graph construction complete.")
    return {"total_nodes": total_nodes}

"""Reusable Cypher query templates for the SAP O2C graph.

These are used by the query pipeline (Step 5) and flow engine (Step 6).
"""


# ─── Flow Tracing ────────────────────────────────────────────────

FULL_FLOW_BY_SALES_ORDER = """
MATCH (c:Customer)-[:PLACED]->(so:SalesOrder {salesOrder: $salesOrder})
OPTIONAL MATCH (so)-[:HAS_ITEM]->(soi:SalesOrderItem)
OPTIONAL MATCH (soi)-[:MAPS_TO]->(di:DeliveryItem)-[:PART_OF]->(d:Delivery)
OPTIONAL MATCH (d)-[:BILLED_AS]->(bd:BillingDocument)
OPTIONAL MATCH (bd)-[:RECORDED_AS]->(je:JournalEntry)
OPTIONAL MATCH (je)-[:CLEARED_BY]->(p:Payment)
RETURN c.businessPartner AS customer,
       c.fullName AS customerName,
       so.salesOrder AS salesOrder,
       so.totalNetAmount AS orderAmount,
       so.transactionCurrency AS currency,
       soi.salesOrderItem AS itemNumber,
       soi.material AS material,
       soi.netAmount AS itemAmount,
       d.deliveryDocument AS delivery,
       d.actualGoodsMovementDate AS goodsMovementDate,
       di.actualDeliveryQuantity AS deliveredQty,
       bd.billingDocument AS billingDoc,
       bd.totalNetAmount AS billedAmount,
       bd.isCancelled AS billingCancelled,
       je.accountingDocument AS journalEntry,
       je.postingDate AS jePostingDate,
       p.accountingDocument AS payment,
       p.postingDate AS paymentDate,
       p.amountInTransactionCurrency AS paymentAmount
ORDER BY soi.salesOrderItem
"""

FULL_FLOW_BY_DELIVERY = """
MATCH (di:DeliveryItem)-[:PART_OF]->(d:Delivery {deliveryDocument: $deliveryDocument})
OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
OPTIONAL MATCH (so:SalesOrder)-[:HAS_ITEM]->(soi)
OPTIONAL MATCH (c:Customer)-[:PLACED]->(so)
OPTIONAL MATCH (d)-[:BILLED_AS]->(bd:BillingDocument)
OPTIONAL MATCH (bd)-[:RECORDED_AS]->(je:JournalEntry)
OPTIONAL MATCH (je)-[:CLEARED_BY]->(p:Payment)
RETURN c.businessPartner AS customer,
       c.fullName AS customerName,
       so.salesOrder AS salesOrder,
       d.deliveryDocument AS delivery,
       bd.billingDocument AS billingDoc,
       je.accountingDocument AS journalEntry,
       p.accountingDocument AS payment
"""

FULL_FLOW_BY_BILLING = """
MATCH (bd:BillingDocument {billingDocument: $billingDocument})
OPTIONAL MATCH (d:Delivery)-[:BILLED_AS]->(bd)
OPTIONAL MATCH (di:DeliveryItem)-[:PART_OF]->(d)
OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
OPTIONAL MATCH (so:SalesOrder)-[:HAS_ITEM]->(soi)
OPTIONAL MATCH (c:Customer)-[:PLACED]->(so)
OPTIONAL MATCH (bd)-[:RECORDED_AS]->(je:JournalEntry)
OPTIONAL MATCH (je)-[:CLEARED_BY]->(p:Payment)
RETURN c.businessPartner AS customer,
       c.fullName AS customerName,
       so.salesOrder AS salesOrder,
       d.deliveryDocument AS delivery,
       bd.billingDocument AS billingDoc,
       bd.totalNetAmount AS billedAmount,
       je.accountingDocument AS journalEntry,
       p.accountingDocument AS payment
"""


# ─── Broken Flow Detection ───────────────────────────────────────

DELIVERED_NOT_BILLED = """
MATCH (d:Delivery)
WHERE NOT (d)-[:BILLED_AS]->(:BillingDocument)
OPTIONAL MATCH (di:DeliveryItem)-[:PART_OF]->(d)
OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
OPTIONAL MATCH (so:SalesOrder)-[:HAS_ITEM]->(soi)
RETURN DISTINCT
       so.salesOrder AS salesOrder,
       d.deliveryDocument AS delivery,
       d.creationDate AS deliveryDate,
       d.overallGoodsMovementStatus AS goodsMovementStatus
ORDER BY d.deliveryDocument
"""

BILLED_NOT_PAID = """
MATCH (bd:BillingDocument)-[:RECORDED_AS]->(je:JournalEntry)
WHERE NOT (je)-[:CLEARED_BY]->(:Payment)
  AND bd.isCancelled <> true
OPTIONAL MATCH (d:Delivery)-[:BILLED_AS]->(bd)
OPTIONAL MATCH (di:DeliveryItem)-[:PART_OF]->(d)
OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
OPTIONAL MATCH (so:SalesOrder)-[:HAS_ITEM]->(soi)
RETURN DISTINCT
       so.salesOrder AS salesOrder,
       d.deliveryDocument AS delivery,
       bd.billingDocument AS billingDoc,
       bd.totalNetAmount AS billedAmount,
       bd.transactionCurrency AS currency,
       je.accountingDocument AS journalEntry,
       je.postingDate AS jePostingDate
ORDER BY bd.billingDocument
"""


# ─── Entity Lookups ──────────────────────────────────────────────

CUSTOMER_ORDERS = """
MATCH (c:Customer {businessPartner: $businessPartner})-[:PLACED]->(so:SalesOrder)
RETURN so.salesOrder AS salesOrder,
       so.creationDate AS creationDate,
       so.totalNetAmount AS totalNetAmount,
       so.transactionCurrency AS currency,
       so.overallDeliveryStatus AS deliveryStatus
ORDER BY so.creationDate DESC
"""

SALES_ORDER_DETAILS = """
MATCH (so:SalesOrder {salesOrder: $salesOrder})
OPTIONAL MATCH (c:Customer)-[:PLACED]->(so)
OPTIONAL MATCH (so)-[:HAS_ITEM]->(soi:SalesOrderItem)
OPTIONAL MATCH (soi)-[:CONTAINS]->(prod:Product)
RETURN so.salesOrder AS salesOrder,
       so.totalNetAmount AS totalNetAmount,
       so.transactionCurrency AS currency,
       so.creationDate AS creationDate,
       so.overallDeliveryStatus AS deliveryStatus,
       c.businessPartner AS customer,
       c.fullName AS customerName,
       collect({
           item: soi.salesOrderItem,
           material: soi.material,
           product: prod.description,
           quantity: soi.requestedQuantity,
           unit: soi.requestedQuantityUnit,
           amount: soi.netAmount
       }) AS items
"""

PRODUCT_ORDERS = """
MATCH (p:Product {product: $product})<-[:CONTAINS]-(soi:SalesOrderItem)<-[:HAS_ITEM]-(so:SalesOrder)
OPTIONAL MATCH (c:Customer)-[:PLACED]->(so)
RETURN so.salesOrder AS salesOrder,
       soi.salesOrderItem AS itemNumber,
       soi.requestedQuantity AS quantity,
       soi.netAmount AS amount,
       c.fullName AS customerName,
       so.creationDate AS orderDate
ORDER BY so.creationDate DESC
"""

# Exact match only — no prefix / CONTAINS (avoids returning every doc starting with 91150…)
JOURNAL_ENTRY_LOOKUP = """
MATCH (je:JournalEntry)
WHERE je.accountingDocument = $documentId
   OR toString(je.referenceDocument) = $documentId
   OR je.referenceDocument = $documentId
WITH je LIMIT 1
OPTIONAL MATCH (bd:BillingDocument)-[:RECORDED_AS]->(je)
OPTIONAL MATCH (d:Delivery)-[:BILLED_AS]->(bd)
OPTIONAL MATCH (di:DeliveryItem)-[:PART_OF]->(d)
OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
OPTIONAL MATCH (so:SalesOrder)-[:HAS_ITEM]->(soi)
OPTIONAL MATCH (c:Customer)-[:PLACED]->(so)
OPTIONAL MATCH (je)-[:CLEARED_BY]->(p:Payment)
RETURN je.accountingDocument AS journalEntryNumber,
       je.referenceDocument AS referenceDocument,
       je.companyCode AS companyCode,
       je.fiscalYear AS fiscalYear,
       bd.billingDocument AS billingDocument,
       so.salesOrder AS salesOrder,
       d.deliveryDocument AS delivery,
       p.accountingDocument AS payment,
       c.fullName AS customerName
LIMIT 1
"""


# ─── Aggregation Queries ─────────────────────────────────────────

TOTAL_REVENUE_BY_CUSTOMER = """
MATCH (c:Customer)-[:PLACED]->(so:SalesOrder)
RETURN c.businessPartner AS customer,
       c.fullName AS customerName,
       count(so) AS orderCount,
       sum(toFloat(so.totalNetAmount)) AS totalRevenue,
       so.transactionCurrency AS currency
ORDER BY totalRevenue DESC
"""

ORDER_COUNT_BY_STATUS = """
MATCH (so:SalesOrder)
RETURN so.overallDeliveryStatus AS deliveryStatus,
       count(so) AS orderCount,
       sum(toFloat(so.totalNetAmount)) AS totalAmount
ORDER BY orderCount DESC
"""

TOP_PRODUCTS_BY_REVENUE = """
MATCH (soi:SalesOrderItem)-[:CONTAINS]->(p:Product)
RETURN p.product AS product,
       p.description AS productDescription,
       count(soi) AS timesOrdered,
       sum(toFloat(soi.netAmount)) AS totalRevenue
ORDER BY totalRevenue DESC
LIMIT $limit
"""


# ─── Graph Statistics ─────────────────────────────────────────────

NODE_COUNTS = """
CALL {
    MATCH (n:Customer) RETURN 'Customer' AS label, count(n) AS count
    UNION ALL
    MATCH (n:SalesOrder) RETURN 'SalesOrder' AS label, count(n) AS count
    UNION ALL
    MATCH (n:SalesOrderItem) RETURN 'SalesOrderItem' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Delivery) RETURN 'Delivery' AS label, count(n) AS count
    UNION ALL
    MATCH (n:DeliveryItem) RETURN 'DeliveryItem' AS label, count(n) AS count
    UNION ALL
    MATCH (n:BillingDocument) RETURN 'BillingDocument' AS label, count(n) AS count
    UNION ALL
    MATCH (n:BillingItem) RETURN 'BillingItem' AS label, count(n) AS count
    UNION ALL
    MATCH (n:JournalEntry) RETURN 'JournalEntry' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Payment) RETURN 'Payment' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Product) RETURN 'Product' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Plant) RETURN 'Plant' AS label, count(n) AS count
    UNION ALL
    MATCH (n:Address) RETURN 'Address' AS label, count(n) AS count
}
RETURN label, count
ORDER BY count DESC
"""

RELATIONSHIP_COUNTS = """
MATCH ()-[r]->()
RETURN type(r) AS relType, count(r) AS count
ORDER BY count DESC
"""

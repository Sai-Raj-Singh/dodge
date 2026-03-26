"""Generate text chunks from the Neo4j graph for RAG embedding.

Produces two types of chunks:
1. Entity summaries — one chunk per key entity (order, delivery, billing, etc.)
2. Flow chains — one chunk per end-to-end document flow path
"""

from app.graph.connection import get_session


def generate_entity_chunks() -> list[dict]:
    """Create descriptive text chunks for each major entity in the graph.

    Returns:
        List of dicts with keys: id, text, metadata
    """
    chunks: list[dict] = []

    with get_session() as session:
        # ── Sales Orders ──────────────────────────────────────
        results = session.run("""
            MATCH (c:Customer)-[:PLACED]->(so:SalesOrder)
            OPTIONAL MATCH (so)-[:HAS_ITEM]->(soi:SalesOrderItem)
            WITH so, c,
                 collect({item: soi.salesOrderItem, material: soi.material,
                          amount: soi.netAmount}) AS items
            RETURN so, c, items
        """)
        for rec in results:
            so = rec["so"]
            c = rec["c"]
            items = rec["items"]
            item_lines = "; ".join(
                f"Item {i['item']}: material {i['material']}, amount {i['amount']}"
                for i in items
                if i.get("item")
            )
            text = (
                f"Sales Order {so['salesOrder']} was placed by customer "
                f"{c['businessPartner']} ({c.get('fullName', 'N/A')}). "
                f"Order type: {so.get('salesOrderType', 'N/A')}, "
                f"total amount: {so.get('totalNetAmount', 'N/A')} "
                f"{so.get('transactionCurrency', '')}. "
                f"Created on {so.get('creationDate', 'N/A')}. "
                f"Delivery status: {so.get('overallDeliveryStatus', 'N/A')}. "
                f"Items: [{item_lines}]."
            )
            chunks.append(
                {
                    "id": f"so_{so['salesOrder']}",
                    "text": text,
                    "metadata": {
                        "type": "sales_order",
                        "salesOrder": so["salesOrder"],
                        "customer": c["businessPartner"],
                    },
                }
            )

        # ── Deliveries ────────────────────────────────────────
        results = session.run("""
            MATCH (di:DeliveryItem)-[:PART_OF]->(d:Delivery)
            OPTIONAL MATCH (soi:SalesOrderItem)-[:MAPS_TO]->(di)
            WITH d, collect(DISTINCT soi.salesOrder) AS salesOrders,
                 collect({item: di.deliveryDocumentItem,
                          qty: di.actualDeliveryQuantity,
                          plant: di.plant}) AS items
            RETURN d, salesOrders, items
        """)
        for rec in results:
            d = rec["d"]
            sos = [s for s in rec["salesOrders"] if s]
            items = rec["items"]
            item_lines = "; ".join(
                f"Item {i['item']}: qty {i['qty']}, plant {i['plant']}"
                for i in items
                if i.get("item")
            )
            text = (
                f"Delivery {d['deliveryDocument']} was created on "
                f"{d.get('creationDate', 'N/A')}. "
                f"Shipping point: {d.get('shippingPoint', 'N/A')}. "
                f"Goods movement date: {d.get('actualGoodsMovementDate', 'N/A')}. "
                f"Goods movement status: {d.get('overallGoodsMovementStatus', 'N/A')}. "
                f"Related sales orders: {', '.join(sos) if sos else 'N/A'}. "
                f"Items: [{item_lines}]."
            )
            chunks.append(
                {
                    "id": f"del_{d['deliveryDocument']}",
                    "text": text,
                    "metadata": {
                        "type": "delivery",
                        "deliveryDocument": d["deliveryDocument"],
                        "salesOrders": ",".join(sos),
                    },
                }
            )

        # ── Billing Documents ─────────────────────────────────
        results = session.run("""
            MATCH (bd:BillingDocument)
            OPTIONAL MATCH (d:Delivery)-[:BILLED_AS]->(bd)
            RETURN bd,
                   collect(DISTINCT d.deliveryDocument) AS deliveries
        """)
        for rec in results:
            bd = rec["bd"]
            dels = [d for d in rec["deliveries"] if d]
            text = (
                f"Billing Document {bd['billingDocument']} of type "
                f"{bd.get('billingDocumentType', 'N/A')} was created on "
                f"{bd.get('creationDate', 'N/A')}. "
                f"Total amount: {bd.get('totalNetAmount', 'N/A')} "
                f"{bd.get('transactionCurrency', '')}. "
                f"Cancelled: {bd.get('isCancelled', False)}. "
                f"Accounting document: {bd.get('accountingDocument', 'N/A')}. "
                f"Sold to: {bd.get('soldToParty', 'N/A')}. "
                f"Related deliveries: {', '.join(dels) if dels else 'N/A'}."
            )
            chunks.append(
                {
                    "id": f"bill_{bd['billingDocument']}",
                    "text": text,
                    "metadata": {
                        "type": "billing_document",
                        "billingDocument": bd["billingDocument"],
                    },
                }
            )

        # ── Journal Entries ───────────────────────────────────
        results = session.run("""
            MATCH (je:JournalEntry)
            OPTIONAL MATCH (bd:BillingDocument)-[:RECORDED_AS]->(je)
            OPTIONAL MATCH (je)-[:CLEARED_BY]->(p:Payment)
            RETURN je,
                   collect(DISTINCT bd.billingDocument) AS billingDocs,
                   collect(DISTINCT p.accountingDocument) AS payments
        """)
        for rec in results:
            je = rec["je"]
            bills = [b for b in rec["billingDocs"] if b]
            pays = [p for p in rec["payments"] if p]
            text = (
                f"Journal Entry {je['accountingDocument']} "
                f"(company {je['companyCode']}, FY {je['fiscalYear']}). "
                f"Reference: {je.get('referenceDocument', 'N/A')}. "
                f"Customer: {je.get('customer', 'N/A')}. "
                f"Amount: {je.get('amountInTransactionCurrency', 'N/A')} "
                f"{je.get('transactionCurrency', '')}. "
                f"Posting date: {je.get('postingDate', 'N/A')}. "
                f"Clearing document: {je.get('clearingAccountingDocument', 'N/A')}. "
                f"From billing docs: {', '.join(bills) if bills else 'N/A'}. "
                f"Cleared by payments: {', '.join(pays) if pays else 'N/A'}."
            )
            chunks.append(
                {
                    "id": f"je_{je['companyCode']}_{je['fiscalYear']}_{je['accountingDocument']}",
                    "text": text,
                    "metadata": {
                        "type": "journal_entry",
                        "accountingDocument": je["accountingDocument"],
                    },
                }
            )

        # ── Customers ─────────────────────────────────────────
        results = session.run("""
            MATCH (c:Customer)
            OPTIONAL MATCH (c)-[:PLACED]->(so:SalesOrder)
            OPTIONAL MATCH (c)-[:HAS_ADDRESS]->(a:Address)
            WITH c, collect(DISTINCT so.salesOrder) AS orders, collect(DISTINCT a) AS addrs
            RETURN c, orders, addrs
        """)
        for rec in results:
            c = rec["c"]
            orders = [o for o in rec["orders"] if o]
            addrs = rec["addrs"]
            addr_text = ""
            if addrs and addrs[0]:
                a = addrs[0]
                addr_text = (
                    f"Address: {a.get('streetName', '')}, "
                    f"{a.get('cityName', '')}, {a.get('region', '')}, "
                    f"{a.get('country', '')} {a.get('postalCode', '')}. "
                )
            text = (
                f"Customer {c['businessPartner']} — "
                f"{c.get('fullName') or c.get('name', 'N/A')}. "
                f"Category: {c.get('category', 'N/A')}. "
                f"Industry: {c.get('industry', 'N/A')}. "
                f"{addr_text}"
                f"Orders placed: {', '.join(orders) if orders else 'none'}."
            )
            chunks.append(
                {
                    "id": f"cust_{c['businessPartner']}",
                    "text": text,
                    "metadata": {
                        "type": "customer",
                        "businessPartner": c["businessPartner"],
                    },
                }
            )

        # ── Products ──────────────────────────────────────────
        results = session.run("""
            MATCH (p:Product)
            OPTIONAL MATCH (p)-[:LOCATED_AT]->(pl:Plant)
            RETURN p, collect(DISTINCT pl.plantName) AS plants
        """)
        for rec in results:
            p = rec["p"]
            plants = [pl for pl in rec["plants"] if pl]
            text = (
                f"Product {p['product']}: {p.get('description', 'N/A')}. "
                f"Type: {p.get('productType', 'N/A')}. "
                f"Group: {p.get('productGroup', 'N/A')}. "
                f"Base unit: {p.get('baseUnit', 'N/A')}. "
                f"Weight: {p.get('grossWeight', 'N/A')} {p.get('weightUnit', '')}. "
                f"Available at plants: {', '.join(plants) if plants else 'N/A'}."
            )
            chunks.append(
                {
                    "id": f"prod_{p['product']}",
                    "text": text,
                    "metadata": {
                        "type": "product",
                        "product": p["product"],
                    },
                }
            )

    print(f"[CHUNK] Generated {len(chunks)} entity chunks")
    return chunks


def generate_flow_chunks() -> list[dict]:
    """Create text chunks describing full document flow chains.

    Each chunk traces: SalesOrder -> Delivery -> Billing -> JournalEntry -> Payment

    Returns:
        List of dicts with keys: id, text, metadata
    """
    chunks: list[dict] = []

    with get_session() as session:
        results = session.run("""
            MATCH (c:Customer)-[:PLACED]->(so:SalesOrder)-[:HAS_ITEM]->(soi:SalesOrderItem)
            OPTIONAL MATCH (soi)-[:MAPS_TO]->(di:DeliveryItem)-[:PART_OF]->(d:Delivery)
            OPTIONAL MATCH (d)-[:BILLED_AS]->(bd:BillingDocument)
            OPTIONAL MATCH (bd)-[:RECORDED_AS]->(je:JournalEntry)
            OPTIONAL MATCH (je)-[:CLEARED_BY]->(p:Payment)
            RETURN DISTINCT
                   c.businessPartner AS customer,
                   c.fullName AS customerName,
                   so.salesOrder AS salesOrder,
                   so.totalNetAmount AS orderAmount,
                   d.deliveryDocument AS delivery,
                   bd.billingDocument AS billingDoc,
                   bd.totalNetAmount AS billedAmount,
                   bd.isCancelled AS billingCancelled,
                   je.accountingDocument AS journalEntry,
                   p.accountingDocument AS payment
            ORDER BY so.salesOrder
        """)

        seen_flows = set()
        for rec in results:
            so = rec["salesOrder"]
            delivery = rec["delivery"] or "NONE"
            billing = rec["billingDoc"] or "NONE"
            je = rec["journalEntry"] or "NONE"
            pay = rec["payment"] or "NONE"

            flow_key = f"{so}_{delivery}_{billing}_{je}_{pay}"
            if flow_key in seen_flows:
                continue
            seen_flows.add(flow_key)

            # Determine flow status
            if pay != "NONE":
                status = "COMPLETE (fully paid)"
            elif je != "NONE":
                status = "BILLED_NOT_PAID (journal entry exists but no payment)"
            elif billing != "NONE":
                cancelled = rec.get("billingCancelled", False)
                if cancelled:
                    status = "BILLING_CANCELLED"
                else:
                    status = "BILLED (no journal entry linked)"
            elif delivery != "NONE":
                status = "DELIVERED_NOT_BILLED"
            else:
                status = "ORDERED_ONLY (no delivery)"

            flow_path = f"SalesOrder {so}"
            if delivery != "NONE":
                flow_path += f" -> Delivery {delivery}"
            if billing != "NONE":
                flow_path += f" -> Billing {billing}"
            if je != "NONE":
                flow_path += f" -> JournalEntry {je}"
            if pay != "NONE":
                flow_path += f" -> Payment {pay}"

            text = (
                f"Document flow for customer {rec['customer']} "
                f"({rec.get('customerName', 'N/A')}): {flow_path}. "
                f"Order amount: {rec.get('orderAmount', 'N/A')} INR. "
                f"Flow status: {status}."
            )

            chunks.append(
                {
                    "id": f"flow_{so}_{delivery}_{billing}",
                    "text": text,
                    "metadata": {
                        "type": "flow",
                        "salesOrder": so,
                        "delivery": delivery,
                        "billingDocument": billing,
                        "journalEntry": je,
                        "payment": pay,
                        "status": status,
                    },
                }
            )

    print(f"[CHUNK] Generated {len(chunks)} flow chunks")
    return chunks


def generate_all_chunks() -> list[dict]:
    """Generate all text chunks (entity + flow).

    Returns:
        Combined list of all chunks.
    """
    entity_chunks = generate_entity_chunks()
    flow_chunks = generate_flow_chunks()
    all_chunks = entity_chunks + flow_chunks
    print(f"[CHUNK] Total: {len(all_chunks)} chunks")
    return all_chunks

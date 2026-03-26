"""Pydantic models for all SAP O2C entities."""

from typing import Optional
from pydantic import BaseModel, Field


# ─── Supporting Entities ───────────────────────────────────────────


class Customer(BaseModel):
    """Business partner / customer master."""

    business_partner: str = Field(..., alias="businessPartner")
    customer: Optional[str] = Field(None)
    business_partner_full_name: Optional[str] = Field(
        None, alias="businessPartnerFullName"
    )
    business_partner_name: Optional[str] = Field(None, alias="businessPartnerName")
    business_partner_category: Optional[str] = Field(
        None, alias="businessPartnerCategory"
    )
    business_partner_grouping: Optional[str] = Field(
        None, alias="businessPartnerGrouping"
    )
    correspondence_language: Optional[str] = Field(None, alias="correspondenceLanguage")
    created_by_user: Optional[str] = Field(None, alias="createdByUser")
    creation_date: Optional[str] = Field(None, alias="creationDate")
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    form_of_address: Optional[str] = Field(None, alias="formOfAddress")
    industry: Optional[str] = Field(None, alias="industry")
    organization_bp_name1: Optional[str] = Field(None, alias="organizationBpName1")
    organization_bp_name2: Optional[str] = Field(None, alias="organizationBpName2")
    is_blocked: Optional[bool] = Field(None, alias="businessPartnerIsBlocked")

    model_config = {"populate_by_name": True}


class Address(BaseModel):
    """Business partner address."""

    business_partner: str = Field(..., alias="businessPartner")
    address_id: Optional[str] = Field(None, alias="addressId")
    city_name: Optional[str] = Field(None, alias="cityName")
    country: Optional[str] = Field(None)
    postal_code: Optional[str] = Field(None, alias="postalCode")
    region: Optional[str] = Field(None)
    street_name: Optional[str] = Field(None, alias="streetName")
    po_box: Optional[str] = Field(None, alias="poBox")
    transport_zone: Optional[str] = Field(None, alias="transportZone")

    model_config = {"populate_by_name": True}


class Product(BaseModel):
    """Material / product master."""

    product: str = Field(...)
    product_type: Optional[str] = Field(None, alias="productType")
    product_group: Optional[str] = Field(None, alias="productGroup")
    product_description: Optional[str] = Field(None)  # joined from product_descriptions
    base_unit: Optional[str] = Field(None, alias="baseUnit")
    gross_weight: Optional[str] = Field(None, alias="grossWeight")
    net_weight: Optional[str] = Field(None, alias="netWeight")
    weight_unit: Optional[str] = Field(None, alias="weightUnit")
    division: Optional[str] = Field(None)
    industry_sector: Optional[str] = Field(None, alias="industrySector")
    is_marked_for_deletion: Optional[bool] = Field(None, alias="isMarkedForDeletion")
    creation_date: Optional[str] = Field(None, alias="creationDate")

    model_config = {"populate_by_name": True}


class Plant(BaseModel):
    """Plant master data."""

    plant: str = Field(...)
    plant_name: Optional[str] = Field(None, alias="plantName")
    valuation_area: Optional[str] = Field(None, alias="valuationArea")
    factory_calendar: Optional[str] = Field(None, alias="factoryCalendar")
    sales_organization: Optional[str] = Field(None, alias="salesOrganization")
    distribution_channel: Optional[str] = Field(None, alias="distributionChannel")
    division: Optional[str] = Field(None)
    language: Optional[str] = Field(None)
    plant_category: Optional[str] = Field(None, alias="plantCategory")

    model_config = {"populate_by_name": True}


# ─── Core Transactional Entities ──────────────────────────────────


class SalesOrder(BaseModel):
    """Sales order header."""

    sales_order: str = Field(..., alias="salesOrder")
    sales_order_type: Optional[str] = Field(None, alias="salesOrderType")
    sales_organization: Optional[str] = Field(None, alias="salesOrganization")
    distribution_channel: Optional[str] = Field(None, alias="distributionChannel")
    organization_division: Optional[str] = Field(None, alias="organizationDivision")
    sold_to_party: Optional[str] = Field(None, alias="soldToParty")
    creation_date: Optional[str] = Field(None, alias="creationDate")
    created_by_user: Optional[str] = Field(None, alias="createdByUser")
    total_net_amount: Optional[str] = Field(None, alias="totalNetAmount")
    transaction_currency: Optional[str] = Field(None, alias="transactionCurrency")
    requested_delivery_date: Optional[str] = Field(None, alias="requestedDeliveryDate")
    overall_delivery_status: Optional[str] = Field(None, alias="overallDeliveryStatus")
    header_billing_block_reason: Optional[str] = Field(
        None, alias="headerBillingBlockReason"
    )
    delivery_block_reason: Optional[str] = Field(None, alias="deliveryBlockReason")
    customer_payment_terms: Optional[str] = Field(None, alias="customerPaymentTerms")
    incoterms_classification: Optional[str] = Field(
        None, alias="incotermsClassification"
    )
    incoterms_location1: Optional[str] = Field(None, alias="incotermsLocation1")
    pricing_date: Optional[str] = Field(None, alias="pricingDate")

    model_config = {"populate_by_name": True}


class SalesOrderItem(BaseModel):
    """Sales order line item."""

    sales_order: str = Field(..., alias="salesOrder")
    sales_order_item: str = Field(..., alias="salesOrderItem")
    sales_order_item_category: Optional[str] = Field(
        None, alias="salesOrderItemCategory"
    )
    material: Optional[str] = Field(None)
    requested_quantity: Optional[str] = Field(None, alias="requestedQuantity")
    requested_quantity_unit: Optional[str] = Field(None, alias="requestedQuantityUnit")
    transaction_currency: Optional[str] = Field(None, alias="transactionCurrency")
    net_amount: Optional[str] = Field(None, alias="netAmount")
    material_group: Optional[str] = Field(None, alias="materialGroup")
    production_plant: Optional[str] = Field(None, alias="productionPlant")
    storage_location: Optional[str] = Field(None, alias="storageLocation")

    model_config = {"populate_by_name": True}


class Delivery(BaseModel):
    """Outbound delivery header."""

    delivery_document: str = Field(..., alias="deliveryDocument")
    shipping_point: Optional[str] = Field(None, alias="shippingPoint")
    creation_date: Optional[str] = Field(None, alias="creationDate")
    actual_goods_movement_date: Optional[str] = Field(
        None, alias="actualGoodsMovementDate"
    )
    overall_goods_movement_status: Optional[str] = Field(
        None, alias="overallGoodsMovementStatus"
    )
    overall_picking_status: Optional[str] = Field(None, alias="overallPickingStatus")
    delivery_block_reason: Optional[str] = Field(None, alias="deliveryBlockReason")
    header_billing_block_reason: Optional[str] = Field(
        None, alias="headerBillingBlockReason"
    )

    model_config = {"populate_by_name": True}


class DeliveryItem(BaseModel):
    """Outbound delivery line item."""

    delivery_document: str = Field(..., alias="deliveryDocument")
    delivery_document_item: str = Field(..., alias="deliveryDocumentItem")
    reference_sd_document: Optional[str] = Field(None, alias="referenceSdDocument")
    reference_sd_document_item: Optional[str] = Field(
        None, alias="referenceSdDocumentItem"
    )
    actual_delivery_quantity: Optional[str] = Field(
        None, alias="actualDeliveryQuantity"
    )
    delivery_quantity_unit: Optional[str] = Field(None, alias="deliveryQuantityUnit")
    plant: Optional[str] = Field(None)
    storage_location: Optional[str] = Field(None, alias="storageLocation")
    batch: Optional[str] = Field(None)

    model_config = {"populate_by_name": True}


class BillingDocument(BaseModel):
    """Billing document header."""

    billing_document: str = Field(..., alias="billingDocument")
    billing_document_type: Optional[str] = Field(None, alias="billingDocumentType")
    creation_date: Optional[str] = Field(None, alias="creationDate")
    billing_document_date: Optional[str] = Field(None, alias="billingDocumentDate")
    billing_document_is_cancelled: Optional[bool] = Field(
        None, alias="billingDocumentIsCancelled"
    )
    cancelled_billing_document: Optional[str] = Field(
        None, alias="cancelledBillingDocument"
    )
    total_net_amount: Optional[str] = Field(None, alias="totalNetAmount")
    transaction_currency: Optional[str] = Field(None, alias="transactionCurrency")
    company_code: Optional[str] = Field(None, alias="companyCode")
    fiscal_year: Optional[str] = Field(None, alias="fiscalYear")
    accounting_document: Optional[str] = Field(None, alias="accountingDocument")
    sold_to_party: Optional[str] = Field(None, alias="soldToParty")

    model_config = {"populate_by_name": True}


class BillingItem(BaseModel):
    """Billing document line item."""

    billing_document: str = Field(..., alias="billingDocument")
    billing_document_item: str = Field(..., alias="billingDocumentItem")
    material: Optional[str] = Field(None)
    billing_quantity: Optional[str] = Field(None, alias="billingQuantity")
    billing_quantity_unit: Optional[str] = Field(None, alias="billingQuantityUnit")
    net_amount: Optional[str] = Field(None, alias="netAmount")
    transaction_currency: Optional[str] = Field(None, alias="transactionCurrency")
    reference_sd_document: Optional[str] = Field(None, alias="referenceSdDocument")
    reference_sd_document_item: Optional[str] = Field(
        None, alias="referenceSdDocumentItem"
    )

    model_config = {"populate_by_name": True}


class JournalEntry(BaseModel):
    """Journal entry / accounting document for accounts receivable."""

    company_code: str = Field(..., alias="companyCode")
    fiscal_year: str = Field(..., alias="fiscalYear")
    accounting_document: str = Field(..., alias="accountingDocument")
    accounting_document_item: Optional[str] = Field(
        None, alias="accountingDocumentItem"
    )
    accounting_document_type: Optional[str] = Field(
        None, alias="accountingDocumentType"
    )
    gl_account: Optional[str] = Field(None, alias="glAccount")
    customer: Optional[str] = Field(None)
    reference_document: Optional[str] = Field(None, alias="referenceDocument")
    amount_in_transaction_currency: Optional[str] = Field(
        None, alias="amountInTransactionCurrency"
    )
    transaction_currency: Optional[str] = Field(None, alias="transactionCurrency")
    amount_in_company_code_currency: Optional[str] = Field(
        None, alias="amountInCompanyCodeCurrency"
    )
    posting_date: Optional[str] = Field(None, alias="postingDate")
    document_date: Optional[str] = Field(None, alias="documentDate")
    clearing_date: Optional[str] = Field(None, alias="clearingDate")
    clearing_accounting_document: Optional[str] = Field(
        None, alias="clearingAccountingDocument"
    )
    clearing_doc_fiscal_year: Optional[str] = Field(None, alias="clearingDocFiscalYear")
    profit_center: Optional[str] = Field(None, alias="profitCenter")
    cost_center: Optional[str] = Field(None, alias="costCenter")
    assignment_reference: Optional[str] = Field(None, alias="assignmentReference")

    model_config = {"populate_by_name": True}


class Payment(BaseModel):
    """Payment document for accounts receivable."""

    company_code: str = Field(..., alias="companyCode")
    fiscal_year: str = Field(..., alias="fiscalYear")
    accounting_document: str = Field(..., alias="accountingDocument")
    accounting_document_item: Optional[str] = Field(
        None, alias="accountingDocumentItem"
    )
    customer: Optional[str] = Field(None)
    invoice_reference: Optional[str] = Field(None, alias="invoiceReference")
    invoice_reference_fiscal_year: Optional[str] = Field(
        None, alias="invoiceReferenceFiscalYear"
    )
    sales_document: Optional[str] = Field(None, alias="salesDocument")
    sales_document_item: Optional[str] = Field(None, alias="salesDocumentItem")
    amount_in_transaction_currency: Optional[str] = Field(
        None, alias="amountInTransactionCurrency"
    )
    transaction_currency: Optional[str] = Field(None, alias="transactionCurrency")
    amount_in_company_code_currency: Optional[str] = Field(
        None, alias="amountInCompanyCodeCurrency"
    )
    posting_date: Optional[str] = Field(None, alias="postingDate")
    document_date: Optional[str] = Field(None, alias="documentDate")
    clearing_date: Optional[str] = Field(None, alias="clearingDate")
    clearing_accounting_document: Optional[str] = Field(
        None, alias="clearingAccountingDocument"
    )
    clearing_doc_fiscal_year: Optional[str] = Field(None, alias="clearingDocFiscalYear")
    gl_account: Optional[str] = Field(None, alias="glAccount")
    profit_center: Optional[str] = Field(None, alias="profitCenter")
    assignment_reference: Optional[str] = Field(None, alias="assignmentReference")

    model_config = {"populate_by_name": True}

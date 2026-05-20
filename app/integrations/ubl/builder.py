"""UBL XML stub builder. TODO-DIAN: conform to Anexo Técnico UBL 2.1."""

from datetime import date
from decimal import Decimal
from xml.sax.saxutils import escape


def build_invoice_ubl_stub(
    *,
    invoice_number: str,
    issue_date: date,
    supplier_nit: str,
    supplier_name: str,
    customer_doc: str,
    customer_name: str,
    currency: str,
    subtotal: Decimal,
    tax_total: Decimal,
    total: Decimal,
    lines: list[dict],
) -> bytes:
    line_xml = ""
    for i, line in enumerate(lines, 1):
        line_xml += f"""
    <cac:InvoiceLine>
      <cbc:ID>{i}</cbc:ID>
      <cbc:InvoicedQuantity>{line['quantity']}</cbc:InvoicedQuantity>
      <cbc:LineExtensionAmount currencyID="{currency}">{line['line_subtotal']}</cbc:LineExtensionAmount>
      <cac:Item><cbc:Description>{escape(str(line['description']))}</cbc:Description></cac:Item>
      <cac:Price><cbc:PriceAmount currencyID="{currency}">{line['unit_price']}</cbc:PriceAmount></cac:Price>
    </cac:InvoiceLine>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- TODO-DIAN: Replace with compliant UBL 2.1 Invoice per Anexo 1.9 -->
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>{escape(invoice_number)}</cbc:ID>
  <cbc:IssueDate>{issue_date.isoformat()}</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>{currency}</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme><cbc:CompanyID>{escape(supplier_nit)}</cbc:CompanyID></cac:PartyTaxScheme>
      <cac:PartyLegalEntity><cbc:RegistrationName>{escape(supplier_name)}</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification><cbc:ID>{escape(customer_doc)}</cbc:ID></cac:PartyIdentification>
      <cac:PartyLegalEntity><cbc:RegistrationName>{escape(customer_name)}</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="{currency}">{subtotal}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="{currency}">{subtotal}</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="{currency}">{total}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="{currency}">{total}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:TaxTotal><cbc:TaxAmount currencyID="{currency}">{tax_total}</cbc:TaxAmount></cac:TaxTotal>
  {line_xml}
</Invoice>"""
    return xml.encode("utf-8")


def build_credit_note_ubl_stub(
    *,
    credit_note_number: str,
    invoice_number: str,
    issue_date: date,
    supplier_nit: str,
    supplier_name: str,
    customer_doc: str,
    customer_name: str,
    currency: str,
    subtotal: Decimal,
    tax_total: Decimal,
    total: Decimal,
    reason_code: str,
    lines: list[dict],
) -> bytes:
    line_xml = ""
    for i, line in enumerate(lines, 1):
        line_xml += f"""
    <cac:CreditNoteLine>
      <cbc:ID>{i}</cbc:ID>
      <cbc:CreditedQuantity>{line['quantity']}</cbc:CreditedQuantity>
      <cbc:LineExtensionAmount currencyID="{currency}">{line['line_subtotal']}</cbc:LineExtensionAmount>
      <cac:Item><cbc:Description>{escape(str(line['description']))}</cbc:Description></cac:Item>
    </cac:CreditNoteLine>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- TODO-DIAN: Replace with compliant UBL 2.1 CreditNote -->
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>{escape(credit_note_number)}</cbc:ID>
  <cbc:IssueDate>{issue_date.isoformat()}</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>{currency}</cbc:DocumentCurrencyCode>
  <cac:DiscrepancyResponse><cbc:ResponseCode>{escape(reason_code)}</cbc:ResponseCode></cac:DiscrepancyResponse>
  <cac:BillingReference>
    <cac:InvoiceDocumentReference><cbc:ID>{escape(invoice_number)}</cbc:ID></cac:InvoiceDocumentReference>
  </cac:BillingReference>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme><cbc:CompanyID>{escape(supplier_nit)}</cbc:CompanyID></cac:PartyTaxScheme>
      <cac:PartyLegalEntity><cbc:RegistrationName>{escape(supplier_name)}</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification><cbc:ID>{escape(customer_doc)}</cbc:ID></cac:PartyIdentification>
      <cac:PartyLegalEntity><cbc:RegistrationName>{escape(customer_name)}</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:PayableAmount currencyID="{currency}">{total}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  {line_xml}
</CreditNote>"""
    return xml.encode("utf-8")


def build_debit_note_ubl_stub(
    *,
    debit_note_number: str,
    invoice_number: str,
    issue_date: date,
    supplier_nit: str,
    supplier_name: str,
    customer_doc: str,
    customer_name: str,
    currency: str,
    subtotal: Decimal,
    tax_total: Decimal,
    total: Decimal,
    reason_code: str,
    lines: list[dict],
) -> bytes:
    line_xml = ""
    for i, line in enumerate(lines, 1):
        line_xml += f"""
    <cac:DebitNoteLine>
      <cbc:ID>{i}</cbc:ID>
      <cbc:DebitedQuantity>{line['quantity']}</cbc:DebitedQuantity>
      <cbc:LineExtensionAmount currencyID="{currency}">{line['line_subtotal']}</cbc:LineExtensionAmount>
      <cac:Item><cbc:Description>{escape(str(line['description']))}</cbc:Description></cac:Item>
    </cac:DebitNoteLine>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- TODO-DIAN: Replace with compliant UBL 2.1 DebitNote -->
<DebitNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2"
           xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
           xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>{escape(debit_note_number)}</cbc:ID>
  <cbc:IssueDate>{issue_date.isoformat()}</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>{currency}</cbc:DocumentCurrencyCode>
  <cac:DiscrepancyResponse><cbc:ResponseCode>{escape(reason_code)}</cbc:ResponseCode></cac:DiscrepancyResponse>
  <cac:BillingReference>
    <cac:InvoiceDocumentReference><cbc:ID>{escape(invoice_number)}</cbc:ID></cac:InvoiceDocumentReference>
  </cac:BillingReference>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme><cbc:CompanyID>{escape(supplier_nit)}</cbc:CompanyID></cac:PartyTaxScheme>
      <cac:PartyLegalEntity><cbc:RegistrationName>{escape(supplier_name)}</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyIdentification><cbc:ID>{escape(customer_doc)}</cbc:ID></cac:PartyIdentification>
      <cac:PartyLegalEntity><cbc:RegistrationName>{escape(customer_name)}</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:LegalMonetaryTotal>
    <cbc:PayableAmount currencyID="{currency}">{total}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  {line_xml}
</DebitNote>"""
    return xml.encode("utf-8")

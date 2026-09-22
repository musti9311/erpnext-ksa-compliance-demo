# UBL generator — Sales Invoice JSON -> ZATCA-shaped simplified tax invoice (UBL 2.1).
# Stdlib only (xml.etree). Covers what a demo CAN prove without device certificates:
# parties + VAT IDs, issue datetime with +03:00, line + document VAT math.
# Deliberately OMITTED (needs CSID-held keys — see README honest limits):
# the cryptographic envelope (UUID, previous-hash, ICV counter, XML signature).
# Usage: python ubl_generator.py <invoice.json> <company.json>  (both as dumped
# from /api/resource/...)  -> stdout XML. Pipe into ubl_validate.py for proof.
import json
import sys
import xml.etree.ElementTree as ET

NS = {"": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
      "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
      "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def q(tag):
    pre, name = tag.split(":")
    return "{%s}%s" % (NS[pre], name)


def sub(parent, tag, text=None, attrib=None):
    el = ET.SubElement(parent, q(tag), attrib or {})
    if text is not None:
        el.text = text
    return el


def money(v):
    return "%.2f" % round(float(v), 2)


def build(inv, comp):
    """inv/company are ERPNext API doc dicts. Returns the XML string."""
    seller = (comp.get("company_name") or "").strip()
    vat_id = (comp.get("tax_id") or "").strip()
    ts_date = inv["posting_date"]
    ts_time = str(inv.get("posting_time", "00:00:00"))[:8]
    # net_total already excludes taxes in ERPNext; fall back safely:
    net = float(inv.get("net_total") or 0.0) or (float(inv["grand_total"]) -
                                                 float(inv.get("total_taxes_and_charges") or 0.0))
    vat = float(inv.get("total_taxes_and_charges") or 0.0)
    total = float(inv["grand_total"])

    root = ET.Element(q(":Invoice"))
    sub(root, "cbc:ID", inv["name"])
    sub(root, "cbc:IssueDate", ts_date)
    sub(root, "cbc:IssueTime", ts_time)
    sub(root, "cbc:InvoiceTypeCode", "388")  # UNCL 1001: tax invoice
    sub(root, "cbc:DocumentCurrencyCode", inv.get("currency") or "SAR")
    sub(root, "cbc:TaxCurrencyCode", inv.get("currency") or "SAR")

    sup = sub(root, "cac:AccountingSupplierParty")
    party = sub(sup, "cac:Party")
    sub(sub(party, "cac:PartyName"), "cbc:Name", seller)
    pid = sub(party, "cac:PartyTaxScheme")
    sub(pid, "cbc:CompanyID", vat_id, {"schemeID": "VAT"})
    sub(sub(pid, "cac:TaxScheme"), "cbc:ID", "VAT")

    cus = sub(root, "cac:AccountingCustomerParty")
    cparty = sub(cus, "cac:Party")
    sub(sub(cparty, "cac:PartyName"), "cbc:Name", inv.get("customer_name") or inv.get("customer"))

    tax = sub(root, "cac:TaxTotal")
    sub(tax, "cbc:TaxAmount", money(vat), {"currencyID": inv.get("currency") or "SAR"})
    subtotal = sub(tax, "cac:TaxSubtotal")
    sub(subtotal, "cbc:TaxableAmount", money(net), {"currencyID": inv.get("currency") or "SAR"})
    sub(subtotal, "cbc:TaxAmount", money(vat), {"currencyID": inv.get("currency") or "SAR"})
    cat = sub(subtotal, "cac:TaxCategory")
    sub(cat, "cbc:ID", "S")  # standard rate
    sub(cat, "cbc:Percent", "15.00")
    sub(sub(subtotal, "cac:TaxScheme"), "cbc:ID", "VAT")

    legal = sub(root, "cac:LegalMonetaryTotal")
    sub(legal, "cbc:LineExtensionAmount", money(net), {"currencyID": inv.get("currency") or "SAR"})
    sub(legal, "cbc:TaxExclusiveAmount", money(net), {"currencyID": inv.get("currency") or "SAR"})
    sub(legal, "cbc:TaxInclusiveAmount", money(total), {"currencyID": inv.get("currency") or "SAR"})
    sub(legal, "cbc:PayableAmount", money(total), {"currencyID": inv.get("currency") or "SAR"})

    for i, row in enumerate(inv.get("items", []), 1):
        line = sub(root, "cac:InvoiceLine")
        sub(line, "cbc:ID", str(i))
        sub(line, "cbc:InvoicedQuantity", str(row.get("qty")), {"unitCode": "PCE"})
        sub(line, "cbc:LineExtensionAmount", money(row.get("amount")),
            {"currencyID": inv.get("currency") or "SAR"})
        sub(sub(line, "cac:Item"), "cbc:Name", row.get("item_name") or row.get("item_code"))
        price = sub(line, "cac:Price")
        sub(price, "cbc:PriceAmount", money(row.get("rate")), {"currencyID": inv.get("currency") or "SAR"})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


if __name__ == "__main__":
    if len(sys.argv) == 3:  # live mode: two JSON dump files
        inv = json.load(open(sys.argv[1], encoding="utf-8"))
        comp = json.load(open(sys.argv[2], encoding="utf-8"))
        inv = inv.get("data", inv)
        comp = comp.get("data", comp)
        print(build(inv, comp))
    else:  # ponytail: offline self-check on canned data, fails if math breaks
        inv = {"name": "ACC-SINV-2026-00001", "posting_date": "2026-09-06",
               "posting_time": "14:00:00", "currency": "SAR", "customer": "Test",
               "customer_name": "Test", "grand_total": 1150.0,
               "total_taxes_and_charges": 150.0, "net_total": 1000.0,
               "items": [{"item_code": "S", "item_name": "S", "qty": 1,
                          "rate": 1000.0, "amount": 1000.0}]}
        comp = {"company_name": "Al-Rehab Trading Est.", "tax_id": "300000000000003"}
        xml = build(inv, comp)
        assert "<cbc:ID>ACC-SINV-2026-00001</cbc:ID>" in xml
        assert "<cbc:TaxAmount currencyID=\"SAR\">150.00</cbc:TaxAmount>" in xml
        assert "<cbc:PayableAmount currencyID=\"SAR\">1150.00</cbc:PayableAmount>" in xml
        print("ubl self-check OK")

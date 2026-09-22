# ubl_validate.py — three-way agreement proof for one invoice:
#   ERPNext JSON  <->  UBL XML  <->  TLV/QR payload
# An inspector's question answered in one command: do the QR, the XML that
# would clear Phase 2, and the ledger document all say the same thing?
# Stdlib only. Exits non-zero on the first disagreement.
import base64
import sys
import xml.etree.ElementTree as ET

U = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"


def txt(root, path):
    el = root.find(path, {"": U, "cbc": CBC, "cac": CAC})
    assert el is not None and (el.text or "").strip(), "missing element: " + path
    return el.text.strip()


def tlv_decode(b64):
    raw = base64.b64decode(b64)
    out, i = {}, 0
    while i < len(raw):
        tag, ln = raw[i], raw[i + 1]
        out[tag] = raw[i + 2:i + 2 + ln].decode("utf-8")
        i += 2 + ln
    return out


def main(inv_json, xml_file, qr_b64):
    import json
    inv = json.load(open(inv_json, encoding="utf-8"))
    inv = inv.get("data", inv)
    root = ET.parse(xml_file).getroot()

    # 1. XML internal arithmetic
    tax = float(txt(root, "cac:TaxTotal/cbc:TaxAmount"))
    sub = float(root.find("cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount",
                          {"": U, "cbc": CBC, "cac": CAC}).text)
    assert abs(tax - sub) < 0.01, (tax, sub)
    excl = float(txt(root, "cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount"))
    incl = float(txt(root, "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"))
    pay = float(txt(root, "cac:LegalMonetaryTotal/cbc:PayableAmount"))
    assert abs(incl - (excl + tax)) < 0.01 and abs(pay - incl) < 0.01, (excl, tax, incl, pay)
    print("PASS xml arithmetic | exclusive=%.2f tax=%.2f payable=%.2f" % (excl, tax, pay))

    # 2. XML vs ERPNext document
    assert txt(root, "cbc:ID") == inv["name"], "invoice number drift"
    assert abs(float(txt(root, "cac:LegalMonetaryTotal/cbc:PayableAmount")) -
               float(inv["grand_total"])) < 0.01, "grand_total drift"
    assert abs(float(txt(root, "cac:TaxTotal/cbc:TaxAmount")) -
               float(inv.get("total_taxes_and_charges") or 0.0)) < 0.01, "vat drift"
    assert txt(root, "cbc:IssueDate") == inv["posting_date"], "date drift"
    print("PASS xml matches ERPNext |", inv["name"])

    # 3. XML vs TLV/QR payload (tags 1-5: seller, vat, timestamp, total, vat)
    t = tlv_decode(qr_b64)
    assert t[1] == txt(root, "cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name"), t[1]
    assert t[2] == root.find(
        "cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
        {"": U, "cbc": CBC, "cac": CAC}).text, t[2]
    assert t[3].startswith(txt(root, "cbc:IssueDate")), t[3]
    assert abs(float(t[4]) - float(inv["grand_total"])) < 0.01, t[4]
    assert abs(float(t[5]) - float(inv.get("total_taxes_and_charges") or 0.0)) < 0.01, t[5]
    print("PASS qr matches xml | tags 1-5 agree")
    print("THREE-WAY AGREEMENT OK:", inv["name"])


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: python ubl_validate.py <invoice.json> <invoice.xml> <qr_base64>")
    main(sys.argv[1], sys.argv[2], sys.argv[3])

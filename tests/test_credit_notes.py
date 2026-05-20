from datetime import date


def test_create_credit_note_against_signed_invoice(client, auth_headers):
    c = client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={
            "document_type": "CC",
            "document_number": "1234567890",
            "name": "Persona Natural",
        },
    )
    customer_id = c.json()["id"]

    p = client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={"code": "P1", "name": "Producto", "unit_price": "50000"},
    )
    product_id = p.json()["id"]

    inv = client.post(
        "/api/v1/invoices",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "issue_date": str(date.today()),
            "lines": [{"product_id": product_id, "quantity": "1"}],
        },
    )
    invoice_id = inv.json()["id"]

    client.post(
        f"/api/v1/invoices/{invoice_id}/transition",
        headers=auth_headers,
        json={"action": "sign"},
    )

    cn = client.post(
        "/api/v1/credit-notes",
        headers=auth_headers,
        json={
            "invoice_id": invoice_id,
            "issue_date": str(date.today()),
            "reason_code": "1",
            "lines": [{"product_id": product_id, "quantity": "1"}],
        },
    )
    assert cn.status_code == 201
    assert cn.json()["status"] == "draft"
    assert cn.json()["number"].startswith("NC-")

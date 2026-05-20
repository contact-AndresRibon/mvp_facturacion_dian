from datetime import date


def _create_customer(client, headers):
    r = client.post(
        "/api/v1/customers",
        headers=headers,
        json={
            "document_type": "NIT",
            "document_number": "901234567",
            "name": "Cliente Test",
            "email": "cliente@test.com",
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


def _create_product(client, headers):
    r = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "code": "SRV-001",
            "name": "Consultoria",
            "unit_price": "100000.00",
            "tax_rate": "19.00",
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_create_and_sign_invoice(client, auth_headers):
    customer_id = _create_customer(client, auth_headers)
    product_id = _create_product(client, auth_headers)

    inv = client.post(
        "/api/v1/invoices",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "issue_date": str(date.today()),
            "lines": [{"product_id": product_id, "quantity": "2"}],
        },
    )
    assert inv.status_code == 201
    data = inv.json()
    assert data["status"] == "draft"
    assert data["number"].startswith("SETT-")
    invoice_id = data["id"]

    signed = client.post(
        f"/api/v1/invoices/{invoice_id}/transition",
        headers=auth_headers,
        json={"action": "sign"},
    )
    assert signed.status_code == 200
    signed_data = signed.json()
    assert signed_data["status"] == "signed"
    assert signed_data["cufe"] is not None


def test_invoice_pdf(client, auth_headers):
    customer_id = _create_customer(client, auth_headers)
    product_id = _create_product(client, auth_headers)
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
    pdf = client.get(f"/api/v1/invoices/{invoice_id}/pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"

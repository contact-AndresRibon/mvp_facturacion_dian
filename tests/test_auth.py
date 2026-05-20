def test_register_login_me(client):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "legal_name": "Test Co",
            "nit": "800111222",
            "email": "co@test.com",
            "admin_email": "user@test.com",
            "admin_password": "password12",
            "admin_full_name": "Test User",
        },
    )
    assert reg.status_code == 201
    assert "access_token" in reg.json()

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "user@test.com", "password": "password12"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@test.com"

def test_register_login_logout(client):
    r = client.post("/api/auth/register", json={"name": "Тест", "email": "t@t.ru", "password": "123456"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert data["data"]["email"] == "t@t.ru"

    r = client.post("/api/auth/logout")
    assert r.status_code == 200

    r = client.post("/api/auth/login", json={"email": "t@t.ru", "password": "123456"})
    assert r.status_code == 200

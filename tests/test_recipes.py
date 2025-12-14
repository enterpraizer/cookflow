def _register(client):
    client.post("/api/auth/register", json={"name": "Тест", "email": "u@u.ru", "password": "123456"})


def test_create_and_get_recipe(client):
    _register(client)

    payload = {
        "title": "Тест-рецепт",
        "description": "Описание",
        "cooking_time": 10,
        "difficulty": "Легко",
        "servings": 2,
        "ingredients": [{"name": "Курица", "quantity": "200 г", "order": 1}],
        "steps": [{"description": "Сделать что-то", "timer_seconds": 0, "order": 1}],
        "categories": [{"name": "Быстро"}],
    }
    r = client.post("/api/recipes", json=payload)
    assert r.status_code == 201
    recipe_id = r.get_json()["data"]["id"]

    r = client.get(f"/api/recipes/{recipe_id}")
    assert r.status_code == 200
    assert r.get_json()["data"]["title"] == "Тест-рецепт"


def test_search_by_ingredients(client):
    _register(client)
    client.post("/api/recipes", json={
        "title": "С сыром",
        "ingredients": [{"name": "Сыр", "quantity": "50 г", "order": 1}],
        "steps": [{"description": "Шаг", "timer_seconds": 0, "order": 1}],
        "categories": []
    })

    r = client.get("/api/recipes/search?q=сыр")
    assert r.status_code == 200
    assert len(r.get_json()["data"]["items"]) >= 1

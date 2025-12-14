def test_add_comment_requires_auth(client):
    r = client.post("/api/recipes/1/comments", json={"text": "hi"})
    assert r.status_code == 401  # unauthorized


def test_add_and_list_comments(client):
    client.post("/api/auth/register", json={"name": "Тест", "email": "c@c.ru", "password": "123456"})

    r = client.post("/api/recipes", json={
        "title": "Рецепт",
        "ingredients": [{"name": "Яйца", "quantity": "2", "order": 1}],
        "steps": [{"description": "Шаг", "timer_seconds": 0, "order": 1}],
        "categories": []
    })
    recipe_id = r.get_json()["data"]["id"]

    r = client.post(f"/api/recipes/{recipe_id}/comments", json={"text": "<b>ok</b><script>x</script>"})
    assert r.status_code == 201

    r = client.get(f"/api/recipes/{recipe_id}/comments")
    assert r.status_code == 200
    items = r.get_json()["data"]["items"]
    assert len(items) == 1
    assert "<" not in items[0]["text"]  # теги должны быть вычищены

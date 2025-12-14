from app import db
from app.models import Challenge, User


def test_start_challenge(client, app):
    # user
    client.post("/api/auth/register", json={"name": "Тест", "email": "x@x.ru", "password": "123456"})

    # challenge
    with app.app_context():
        ch = Challenge(title="Тест-челлендж", description="d", duration_days=3, target_count=2)
        db.session.add(ch)
        db.session.commit()
        ch_id = ch.id

    r = client.post(f"/api/challenges/{ch_id}/start")
    assert r.status_code in (200, 201)

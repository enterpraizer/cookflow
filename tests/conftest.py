import pytest

from app import create_app, db


class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    WTF_CSRF_ENABLED = False  # в тестах проще отключить CSRF
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "app/static/uploads"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()

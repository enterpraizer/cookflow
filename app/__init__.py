from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from http import HTTPStatus

from config import DevelopmentConfig
from app.api import fail

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_object=DevelopmentConfig):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # HTML redirect для страниц можно оставить, но для /api мы вернём JSON через unauthorized_handler.
    login_manager.login_view = "pages.login"

    @login_manager.unauthorized_handler
    def _unauthorized():
        # Flask‑Login позволяет переопределить ответ для неавторизованных [web:41]
        return fail("UNAUTHORIZED", "Требуется аутентификация", HTTPStatus.UNAUTHORIZED)

    from app.error_handlers import register_error_handlers
    register_error_handlers(app)

    from app.models import User  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.recipes import recipes_bp
    from app.routes.comments import comments_bp
    from app.routes.challenges import challenges_bp
    from app.routes.cooking import cooking_bp
    from app.routes.pages import pages_bp
    from app.routes.uploads import uploads_bp
    from app.cli import seed_command

    app.cli.add_command(seed_command)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(cooking_bp)
    app.register_blueprint(pages_bp)

    return app

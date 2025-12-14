from http import HTTPStatus

from flask import Blueprint, request
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.api import ApiError, ok
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name:
        raise ApiError("VALIDATION_ERROR", "Имя обязательно", HTTPStatus.BAD_REQUEST)
    if not email:
        raise ApiError("VALIDATION_ERROR", "Email обязателен", HTTPStatus.BAD_REQUEST)
    if len(password) < 6:
        raise ApiError("VALIDATION_ERROR", "Пароль должен быть не короче 6 символов", HTTPStatus.BAD_REQUEST)

    if db.session.query(User.id).filter(User.email == email).first():
        raise ApiError("EMAIL_ALREADY_EXISTS", "Пользователь с таким email уже существует", HTTPStatus.CONFLICT)

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return ok({"id": user.id, "name": user.name, "email": user.email}, HTTPStatus.CREATED)


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = db.session.query(User).filter(User.email == email).first()
    if not user or not user.check_password(password):
        raise ApiError("INVALID_CREDENTIALS", "Неверный email или пароль", HTTPStatus.UNAUTHORIZED)

    login_user(user)
    return ok({"id": user.id, "name": user.name, "email": user.email})


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return ok({"message": "OK"})


@auth_bp.get("/user")
def get_current_user():
    if not current_user.is_authenticated:
        return ok({"user": None})
    return ok({"user": {"id": current_user.id, "name": current_user.name, "email": current_user.email}})

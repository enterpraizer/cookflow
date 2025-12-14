from __future__ import annotations

from http import HTTPStatus
from typing import Any

import bleach
from flask import Blueprint, request
from flask_login import current_user, login_required

from app import db
from app.api import ApiError, ok
from app.models import Comment, Recipe


comments_bp = Blueprint("comments", __name__)


def _require_json() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("BAD_REQUEST", "Ожидается JSON-объект", HTTPStatus.BAD_REQUEST)
    return data


def _sanitize_comment_text(text: str) -> str:
    # bleach.clean предназначен для безопасной обработки фрагментов HTML в HTML-контексте [web:62]
    # strip=True удаляет неразрешённые теги вместо экранирования [web:62]
    cleaned = bleach.clean(text, tags=set(), attributes={}, strip=True, strip_comments=True)
    cleaned = " ".join(cleaned.split())  # схлопываем лишние пробелы/переводы строк
    return cleaned


def _comment_to_dict(c: Comment) -> dict[str, Any]:
    return {
        "id": c.id,
        "recipe_id": c.recipe_id,
        "user": {"id": c.user.id, "name": c.user.name},
        "text": c.text,
        "created_at": c.created_at.isoformat(),
    }


@comments_bp.get("/api/recipes/<int:recipe_id>/comments")
def get_comments(recipe_id: int):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        raise ApiError("RECIPE_NOT_FOUND", "Рецепт не найден", HTTPStatus.NOT_FOUND)

    comments = (
        db.session.query(Comment)
        .filter(Comment.recipe_id == recipe_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    return ok({"items": [_comment_to_dict(c) for c in comments]})


@comments_bp.post("/api/recipes/<int:recipe_id>/comments")
@login_required
def add_comment(recipe_id: int):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        raise ApiError("RECIPE_NOT_FOUND", "Рецепт не найден", HTTPStatus.NOT_FOUND)

    data = _require_json()
    text = (data.get("text") or "").strip()
    if not text:
        raise ApiError("VALIDATION_ERROR", "text обязателен", HTTPStatus.BAD_REQUEST)

    safe_text = _sanitize_comment_text(text)
    if not safe_text:
        raise ApiError("VALIDATION_ERROR", "Комментарий пустой после очистки", HTTPStatus.BAD_REQUEST)
    if len(safe_text) > 2000:
        raise ApiError("VALIDATION_ERROR", "Комментарий слишком длинный (макс 2000)", HTTPStatus.BAD_REQUEST)

    comment = Comment(recipe_id=recipe_id, user_id=current_user.id, text=safe_text)
    db.session.add(comment)
    db.session.commit()

    # Подтянем user для ответа (на случай если lazy поведение изменится)
    db.session.refresh(comment)

    return ok(_comment_to_dict(comment), HTTPStatus.CREATED)


@comments_bp.delete("/api/comments/<int:comment_id>")
@login_required
def delete_comment(comment_id: int):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        raise ApiError("COMMENT_NOT_FOUND", "Комментарий не найден", HTTPStatus.NOT_FOUND)

    if comment.user_id != current_user.id:
        raise ApiError("FORBIDDEN", "Нет прав на удаление комментария", HTTPStatus.FORBIDDEN)

    db.session.delete(comment)
    db.session.commit()
    return ok({"message": "Удалено"})

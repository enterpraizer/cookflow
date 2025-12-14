from __future__ import annotations

from datetime import datetime
from http import HTTPStatus

from flask import Blueprint
from flask_login import current_user, login_required
from sqlalchemy import select

from app import db
from app.api import ApiError, ok
from app.models import ChallengeProgress, Recipe, recipe_category, Challenge

cooking_bp = Blueprint("cooking", __name__, url_prefix="/api/cooking")


@cooking_bp.post("/complete/<int:recipe_id>")
@login_required
def complete_cooking(recipe_id: int):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        raise ApiError("RECIPE_NOT_FOUND", "Рецепт не найден", HTTPStatus.NOT_FOUND)

    # категории рецепта (id)
    cat_ids = {c.id for c in recipe.categories}

    # активные прогрессы пользователя
    progresses = (
        db.session.query(ChallengeProgress)
        .filter(ChallengeProgress.user_id == current_user.id)
        .filter(ChallengeProgress.completed_at.is_(None))
        .all()
    )

    updated = 0
    completed = 0

    for p in progresses:
        ch = p.challenge  # relationship
        # если категория не задана — подходит любой рецепт
        if ch.category_id is None or ch.category_id in cat_ids:
            p.completed_count += 1
            updated += 1

            if ch.target_count and p.completed_count >= int(ch.target_count):
                p.completed_at = datetime.utcnow()
                completed += 1

    db.session.commit()

    return ok({
        "message": "Готовка засчитана",
        "progress_updated": updated,
        "challenges_completed": completed,
    })

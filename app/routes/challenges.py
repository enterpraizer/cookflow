from __future__ import annotations

from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any, Optional

from flask import Blueprint, request
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import db
from app.api import ApiError, ok
from app.models import Category, Challenge, ChallengeProgress


challenges_bp = Blueprint("challenges", __name__, url_prefix="/api/challenges")


def _challenge_to_dict(ch: Challenge) -> dict[str, Any]:
    return {
        "id": ch.id,
        "title": ch.title,
        "description": ch.description,
        "image_url": ch.image_url,
        "duration_days": ch.duration_days,
        "target_count": ch.target_count,
        "category": (
            {"id": ch.category.id, "name": ch.category.name, "slug": ch.category.slug}
            if ch.category else None
        ),
    }


def _progress_to_dict(p: ChallengeProgress) -> dict[str, Any]:
    target = p.challenge.target_count or 0
    return {
        "id": p.id,
        "challenge": _challenge_to_dict(p.challenge),
        "completed_count": p.completed_count,
        "target_count": p.challenge.target_count,
        "started_at": p.started_at.isoformat(),
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        "is_completed": bool(p.completed_at) or (target > 0 and p.completed_count >= target),
    }


def _require_json() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("BAD_REQUEST", "Ожидается JSON-объект", HTTPStatus.BAD_REQUEST)
    return data


@challenges_bp.get("")
def list_challenges():
    challenges = db.session.query(Challenge).order_by(Challenge.id.desc()).all()
    return ok({"items": [_challenge_to_dict(c) for c in challenges]})


@challenges_bp.get("/<int:challenge_id>")
def get_challenge(challenge_id: int):
    ch = db.session.get(Challenge, challenge_id)
    if not ch:
        raise ApiError("CHALLENGE_NOT_FOUND", "Челлендж не найден", HTTPStatus.NOT_FOUND)
    return ok(_challenge_to_dict(ch))


@challenges_bp.post("/<int:challenge_id>/start")
@login_required
def start_challenge(challenge_id: int):
    ch = db.session.get(Challenge, challenge_id)
    if not ch:
        raise ApiError("CHALLENGE_NOT_FOUND", "Челлендж не найден", HTTPStatus.NOT_FOUND)

    existing = db.session.execute(
        select(ChallengeProgress).where(
            (ChallengeProgress.user_id == current_user.id)
            & (ChallengeProgress.challenge_id == challenge_id)
        )
    ).scalar_one_or_none()

    if existing:
        return ok(_progress_to_dict(existing))

    p = ChallengeProgress(
        user_id=current_user.id,
        challenge_id=challenge_id,
        completed_count=0,
        started_at=datetime.utcnow(),
        completed_at=None,
    )
    db.session.add(p)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # На случай гонки, уникальность задаётся UniqueConstraint [web:93]
        existing = db.session.execute(
            select(ChallengeProgress).where(
                (ChallengeProgress.user_id == current_user.id)
                & (ChallengeProgress.challenge_id == challenge_id)
            )
        ).scalar_one()
        return ok(_progress_to_dict(existing))

    db.session.refresh(p)
    return ok(_progress_to_dict(p), HTTPStatus.CREATED)


@challenges_bp.post("/<int:challenge_id>/progress")
@login_required
def update_progress(challenge_id: int):
    """
    По ТЗ: обновление прогресса (auth).
    В этой версии: клиент присылает delta или абсолютное completed_count.
    Дополнительно: если задан duration_days, после окончания срока можно запрещать инкремент (опционально).
    """
    ch = db.session.get(Challenge, challenge_id)
    if not ch:
        raise ApiError("CHALLENGE_NOT_FOUND", "Челлендж не найден", HTTPStatus.NOT_FOUND)

    p = db.session.execute(
        select(ChallengeProgress).where(
            (ChallengeProgress.user_id == current_user.id)
            & (ChallengeProgress.challenge_id == challenge_id)
        )
    ).scalar_one_or_none()

    if not p:
        raise ApiError("CHALLENGE_NOT_STARTED", "Сначала начните челлендж", HTTPStatus.BAD_REQUEST)

    data = _require_json()
    delta = data.get("delta")
    completed_count = data.get("completed_count")

    if delta is None and completed_count is None:
        raise ApiError("VALIDATION_ERROR", "Нужно передать delta или completed_count", HTTPStatus.BAD_REQUEST)

    # опционально: срок челленджа
    if ch.duration_days:
        end_at = p.started_at + timedelta(days=int(ch.duration_days))
        if datetime.utcnow() > end_at and not p.completed_at:
            raise ApiError("CHALLENGE_EXPIRED", "Срок челленджа истёк", HTTPStatus.CONFLICT)

    if completed_count is not None:
        try:
            completed_count = int(completed_count)
        except (TypeError, ValueError):
            raise ApiError("VALIDATION_ERROR", "completed_count должен быть числом", HTTPStatus.BAD_REQUEST)
        if completed_count < 0:
            raise ApiError("VALIDATION_ERROR", "completed_count должен быть >= 0", HTTPStatus.BAD_REQUEST)
        p.completed_count = completed_count

    if delta is not None:
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            raise ApiError("VALIDATION_ERROR", "delta должен быть числом", HTTPStatus.BAD_REQUEST)
        if delta <= 0:
            raise ApiError("VALIDATION_ERROR", "delta должен быть > 0", HTTPStatus.BAD_REQUEST)
        p.completed_count += delta

    # автозавершение при достижении цели
    if ch.target_count and p.completed_count >= int(ch.target_count) and not p.completed_at:
        p.completed_at = datetime.utcnow()

    db.session.commit()
    db.session.refresh(p)
    return ok(_progress_to_dict(p))


@challenges_bp.get("/my")
@login_required
def my_challenges():
    # По ТЗ: “Мои активные челленджи”
    rows = (
        db.session.query(ChallengeProgress)
        .filter(ChallengeProgress.user_id == current_user.id)
        .order_by(ChallengeProgress.started_at.desc())
        .all()
    )
    active = [p for p in rows if not p.completed_at]
    return ok({"items": [_progress_to_dict(p) for p in active]})

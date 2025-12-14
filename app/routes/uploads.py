from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, request
from flask_login import login_required

from app.api import ApiError, ok
from app.utils.uploads import save_image


uploads_bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")


@uploads_bp.post("/image")
@login_required
def upload_image():
    """
    multipart/form-data:
      - file: картинка
    Response:
      { ok: true, data: { url: "/static/uploads/<uuid>.<ext>" } }
    """
    file = request.files.get("file")
    if not file:
        raise ApiError("VALIDATION_ERROR", "Нужно передать file", HTTPStatus.BAD_REQUEST)

    url = save_image(file)
    return ok({"url": url}, HTTPStatus.CREATED)

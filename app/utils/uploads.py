from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Iterable, Optional

from flask import current_app
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.api import ApiError
from http import HTTPStatus


def _allowed_ext(filename: str, allowed: Iterable[str]) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in set(allowed)


def save_image(file: FileStorage) -> str:
    """
    Сохраняет изображение в app.config['UPLOAD_FOLDER'] с UUID-именем,
    ресайзит до 1200px по большей стороне, возвращает публичный URL (/static/uploads/...).
    """
    if not file or not file.filename:
        raise ApiError("VALIDATION_ERROR", "Файл не передан", HTTPStatus.BAD_REQUEST)

    # secure_filename — рекомендуемая защита при работе с именами файлов из user input [web:19]
    original = secure_filename(file.filename)
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "webp"})

    if not _allowed_ext(original, allowed):
        raise ApiError("INVALID_IMAGE_FORMAT", "Разрешены только JPG, PNG, WebP", HTTPStatus.BAD_REQUEST)

    ext = original.rsplit(".", 1)[1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    Path(upload_folder).mkdir(parents=True, exist_ok=True)

    abs_path = os.path.join(upload_folder, new_name)

    try:
        img = Image.open(file.stream)
        img = img.convert("RGB") if ext in {"jpg", "jpeg"} else img

        # resize до 1200px по большей стороне
        max_side = 1200
        w, h = img.size
        scale = max(w, h) / max_side
        if scale > 1:
            img = img.resize((int(w / scale), int(h / scale)))

        # Сохраняем оптимизированно
        if ext in {"jpg", "jpeg"}:
            img.save(abs_path, format="JPEG", quality=85, optimize=True)
        elif ext == "png":
            img.save(abs_path, format="PNG", optimize=True)
        else:  # webp
            img.save(abs_path, format="WEBP", quality=82, method=6)

    except ApiError:
        raise
    except Exception:
        raise ApiError("IMAGE_PROCESSING_FAILED", "Не удалось обработать изображение", HTTPStatus.BAD_REQUEST)

    return f"/static/uploads/{new_name}"

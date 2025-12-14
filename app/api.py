from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Optional

from flask import jsonify


@dataclass(frozen=True)
class ApiError(Exception):
    code: str
    message: str
    status_code: int = HTTPStatus.BAD_REQUEST


def ok(data: Any = None, status_code: int = HTTPStatus.OK):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    resp = jsonify(payload)
    resp.status_code = status_code
    return resp


def fail(code: str, message: str, status_code: int):
    resp = jsonify({"ok": False, "error": {"code": code, "message": message}})
    resp.status_code = status_code
    return resp


def fail_exc(err: ApiError):
    return fail(err.code, err.message, err.status_code)

from http import HTTPStatus

from flask import Flask
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

from app.api import ApiError, fail, fail_exc


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(e: ApiError):
        return fail_exc(e)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e: CSRFError):
        # Flask‑WTF генерирует CSRFError, его принято обрабатывать errorhandler'ом [web:21]
        return fail("CSRF_FAILED", "Неверный или отсутствующий CSRF-токен", HTTPStatus.BAD_REQUEST)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        # Единый формат даже для 404/405 и т.п.
        code = {
            HTTPStatus.NOT_FOUND: "NOT_FOUND",
            HTTPStatus.METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
            HTTPStatus.UNAUTHORIZED: "UNAUTHORIZED",
            HTTPStatus.FORBIDDEN: "FORBIDDEN",
            HTTPStatus.BAD_REQUEST: "BAD_REQUEST",
        }.get(HTTPStatus(e.code), "HTTP_ERROR")
        return fail(code, "Ошибка запроса", e.code)

    @app.errorhandler(Exception)
    def handle_unexpected(e: Exception):
        # Здесь позже добавим логирование в файл
        return fail("INTERNAL_SERVER_ERROR", "Внутренняя ошибка сервера", HTTPStatus.INTERNAL_SERVER_ERROR)

from flask import jsonify
from flask_wtf.csrf import CSRFError
from http import HTTPStatus

from app import login_manager   # уже есть выше


def _json_error(code: str, message: str, status: int):
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    return response


@login_manager.unauthorized_handler
def handle_unauthorized():
    # Flask‑Login по умолчанию делает redirect, но ТЗ требует API, поэтому возвращаем JSON [web:41]
    return _json_error("UNAUTHORIZED", "Требуется аутентификация", HTTPStatus.UNAUTHORIZED)


@login_manager.needs_refresh_handler
def handle_needs_refresh():
    return _json_error("LOGIN_REFRESH_REQUIRED", "Требуется повторный вход", HTTPStatus.UNAUTHORIZED)


def register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Flask‑WTF рекомендует обрабатывать CSRFError через errorhandler [web:21]
        return _json_error("CSRF_FAILED", "Неверный или отсутствующий CSRF-токен", HTTPStatus.BAD_REQUEST)

    @app.errorhandler(HTTPStatus.NOT_FOUND)
    def handle_404(e):
        return _json_error("NOT_FOUND", "Ресурс не найден", HTTPStatus.NOT_FOUND)

    @app.errorhandler(HTTPStatus.METHOD_NOT_ALLOWED)
    def handle_405(e):
        return _json_error("METHOD_NOT_ALLOWED", "Метод не поддерживается", HTTPStatus.METHOD_NOT_ALLOWED)

    @app.errorhandler(HTTPStatus.BAD_REQUEST)
    def handle_400(e):
        return _json_error("BAD_REQUEST", "Некорректный запрос", HTTPStatus.BAD_REQUEST)

    @app.errorhandler(Exception)
    def handle_generic_error(e):
        # Здесь можно добавить логирование в файл
        return _json_error("INTERNAL_SERVER_ERROR", "Внутренняя ошибка сервера", HTTPStatus.INTERNAL_SERVER_ERROR)

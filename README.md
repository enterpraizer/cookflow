# CookFlow — платформа интерактивных рецептов (Flask)

CookFlow — полнофункциональное веб-приложение на Flask для интерактивных кулинарных рецептов: пошаговый режим готовки (100vh), таймеры, комментарии, избранное и челленджи.

## Возможности
- Аутентификация: регистрация / вход / выход (сессии).
- Рецепты: список, просмотр, поиск по ингредиентам, избранное, создание/редактирование/удаление (только автор).
- Комментарии к рецептам.
- Челленджи + прогресс.
- Загрузка изображений (локально) + обработка (resize/оптимизация).
- Единый формат ошибок API: `{ "ok": false, "error": { "code": "...", "message": "..." } }`.

---

## Требования
- Python 3.10+ (рекомендуется 3.11+).
- pip, venv.
- SQLite (по умолчанию) или PostgreSQL (через `DATABASE_URL`).

---

## Установка и запуск (SQLite, самый простой вариант)

### 1) Скачать проект
git clone https://github.com/enterpraizer/cookflow.git
cd cookflow


### 2) Создать виртуальное окружение и установить зависимости
macOS / Linux:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt


### 3) Настроить переменные окружения (обязательно)
По умолчанию в `config.py` база SQLite: `sqlite:///cookflow.db`, папка загрузок: `app/static/uploads` [file:271].

macOS / Linux:
export FLASK_APP=run.py


Windows (PowerShell):
$env:FLASK_APP="run.py"


### 4) Применить миграции БД
flask db upgrade



### 5) (Опционально) Заполнить тестовыми данными
flask seed



### 6) Запустить сервер
flask run



Открыть в браузере:
- http://127.0.0.1:5000/

---

## Полезные страницы (UI)
- Главная: `/`
- Вход: `/login`
- Регистрация: `/register`
- Добавить рецепт: `/add-recipe`
- Избранное: `/my-recipes`
- Мои рецепты (авторские): `/my-authored`
- Челленджи: `/challenges`
- Рецепт: `/recipe/<id>`
- Редактирование: `/recipe/<id>/edit`

---

## Настройка через env (SQLite / Postgres / uploads)
`config.py` поддерживает переменные окружения [file:271]:

- `SECRET_KEY` — секрет для сессий (по умолчанию `dev-secret-key`).
- `DATABASE_URL` — строка подключения SQLAlchemy (по умолчанию `sqlite:///cookflow.db`).
- `UPLOAD_FOLDER` — путь к папке загрузок (по умолчанию `app/static/uploads`).

Пример (PostgreSQL):
export DATABASE_URL="postgresql+psycopg2://USER:PASSWORD@localhost:5432/cookflow"
export SECRET_KEY="replace-me"
export FLASK_APP=run.py

flask db upgrade
flask seed
flask run


---

## Запуск тестов
pytest -q


---

## Production (Gunicorn)
1) Установить зависимости.
2) Указать переменные окружения.
3) Применить миграции.
4) Запустить Gunicorn.

Пример:
export FLASK_APP=run.py
export SECRET_KEY="replace-me"
export DATABASE_URL="postgresql+psycopg2://USER:PASSWORD@localhost:5432/cookflow"

flask db upgrade
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"


---

## Частые проблемы

### 1) Ошибка миграции SQLite `Cannot add a NOT NULL column with default value NULL`
Это ограничение SQLite при добавлении NOT NULL колонки через ALTER TABLE.
Если данные не важны (dev), проще пересоздать БД:
rm -f cookflow.db
flask db upgrade
flask seed


### 2) Не работают кнопки в режиме готовки (назад/вперёд/крестик)
Обычно причина — дублирующиеся элементы с одинаковыми `id` в DOM.
Проверьте, что на странице рецепта есть:
{% include "components/cooking_mode.html" %}

и что `app.js` не вставляет overlay второй раз.

---

## Лицензия
Учебный проект.

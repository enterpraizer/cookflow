from __future__ import annotations

from http import HTTPStatus
from typing import Any

from flask import Blueprint, request
from flask_login import current_user, login_required
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app import db
from app.api import ApiError, ok
from app.models import Category, Ingredient, Recipe, RecipeStep, user_saved_recipe
from app.utils.uploads import save_image

recipes_bp = Blueprint("recipes", __name__, url_prefix="/api/recipes")


DIFFICULTIES = {"Легко", "Средне", "Сложно"}


def _recipe_to_dict(recipe: Recipe, include_children: bool = True) -> dict[str, Any]:
    data = {
        "id": recipe.id,
        "title": recipe.title,
        "description": recipe.description,
        "image_url": recipe.image_url,
        "cooking_time": recipe.cooking_time,
        "difficulty": recipe.difficulty,
        "servings": recipe.servings,
        "author": {"id": recipe.author.id, "name": recipe.author.name},
        "created_at": recipe.created_at.isoformat(),
        "updated_at": recipe.updated_at.isoformat(),
        "categories": [{"id": c.id, "name": c.name, "slug": c.slug} for c in recipe.categories],
    }
    if include_children:
        data["ingredients"] = [
            {"id": i.id, "name": i.name, "quantity": i.quantity, "order": i.order}
            for i in recipe.ingredients
        ]
        data["steps"] = [
            {
                "id": s.id,
                "order": s.order,
                "description": s.description,
                "image_url": s.image_url,
                "timer_seconds": s.timer_seconds,
            }
            for s in recipe.steps
        ]
        data["is_saved"] = (
            current_user.is_authenticated and any(u.id == current_user.id for u in recipe.saved_by_users)
        )
    return data


def _require_json() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("BAD_REQUEST", "Ожидается JSON-объект", HTTPStatus.BAD_REQUEST)
    return data


def _get_or_create_categories(items: list[dict]) -> list[Category]:
    categories: list[Category] = []
    for obj in items:
        name = (obj.get("name") or "").strip()
        slug = (obj.get("slug") or "").strip() or None
        if not name:
            raise ApiError("VALIDATION_ERROR", "Категория: name обязателен", HTTPStatus.BAD_REQUEST)

        existing = db.session.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
        if existing:
            if slug and not existing.slug:
                existing.slug = slug
            categories.append(existing)
            continue

        cat = Category(name=name, slug=slug)
        db.session.add(cat)
        categories.append(cat)
    return categories


@recipes_bp.get("")
def get_all_recipes():
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 12)), 1), 50)

    q = db.session.query(Recipe).order_by(Recipe.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    items = [_recipe_to_dict(r, include_children=False) for r in pagination.items]
    return ok({"items": items, "page": pagination.page, "pages": pagination.pages, "total": pagination.total})


@recipes_bp.get("/<int:recipe_id>")
def get_recipe_by_id(recipe_id: int):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        raise ApiError("RECIPE_NOT_FOUND", "Рецепт не найден", HTTPStatus.NOT_FOUND)
    return ok(_recipe_to_dict(recipe, include_children=True))


@recipes_bp.post("")
@login_required
def create_recipe():
    """
    Создание рецепта:
    - JSON поля + массивы ingredients/steps/categories
    - optional: multipart/form-data с file=image (для рецепта)
    """
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        data_raw = request.form.get("data", "")
        if not data_raw:
            raise ApiError("BAD_REQUEST", "В multipart ожидается поле data (JSON строка)", HTTPStatus.BAD_REQUEST)
        import json

        try:
            data = json.loads(data_raw)
        except Exception:
            raise ApiError("BAD_REQUEST", "Невалидный JSON в поле data", HTTPStatus.BAD_REQUEST)

        file = request.files.get("image")
        image_url = save_image(file) if file else None
    else:
        data = _require_json()
        image_url = None

    title = (data.get("title") or "").strip()
    if not title:
        raise ApiError("VALIDATION_ERROR", "Название обязательно", HTTPStatus.BAD_REQUEST)

    difficulty = (data.get("difficulty") or "").strip()
    if difficulty and difficulty not in DIFFICULTIES:
        raise ApiError("VALIDATION_ERROR", "difficulty должен быть: Легко/Средне/Сложно", HTTPStatus.BAD_REQUEST)

    ingredients = data.get("ingredients") or []
    steps = data.get("steps") or []
    categories_in = data.get("categories") or []

    if not isinstance(ingredients, list) or not isinstance(steps, list) or not isinstance(categories_in, list):
        raise ApiError("VALIDATION_ERROR", "ingredients/steps/categories должны быть массивами", HTTPStatus.BAD_REQUEST)

    recipe = Recipe(
        title=title,
        description=data.get("description"),
        image_url=image_url or data.get("image_url"),
        cooking_time=data.get("cooking_time"),
        difficulty=difficulty or None,
        servings=data.get("servings"),
        author_id=current_user.id,
    )

    # дочерние записи
    for idx, ing in enumerate(ingredients, start=1):
        name = (ing.get("name") or "").strip()
        if not name:
            raise ApiError("VALIDATION_ERROR", f"Ингредиент #{idx}: name обязателен", HTTPStatus.BAD_REQUEST)

        ing_obj = Ingredient(
            quantity=(ing.get("quantity") or "").strip() or None,
            order=int(ing.get("order") or idx),
        )
        ing_obj.set_name(name)  # <-- ВОТ СЮДА
        recipe.ingredients.append(ing_obj)

    for idx, st in enumerate(steps, start=1):
        desc = (st.get("description") or "").strip()
        if not desc:
            raise ApiError("VALIDATION_ERROR", f"Шаг #{idx}: description обязателен", HTTPStatus.BAD_REQUEST)
        timer = int(st.get("timer_seconds") or 0)
        if timer < 0:
            raise ApiError("VALIDATION_ERROR", f"Шаг #{idx}: timer_seconds >= 0", HTTPStatus.BAD_REQUEST)

        recipe.steps.append(
            RecipeStep(
                order=int(st.get("order") or idx),
                description=desc,
                image_url=(st.get("image_url") or "").strip() or None,
                timer_seconds=timer,
            )
        )

    # категории
    recipe.categories = _get_or_create_categories(categories_in)

    db.session.add(recipe)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("DB_CONFLICT", "Конфликт данных при сохранении", HTTPStatus.CONFLICT)

    return ok(_recipe_to_dict(recipe, include_children=True), HTTPStatus.CREATED)


@recipes_bp.put("/<int:recipe_id>")
@login_required
def update_recipe(recipe_id: int):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        raise ApiError("RECIPE_NOT_FOUND", "Рецепт не найден", HTTPStatus.NOT_FOUND)
    if recipe.author_id != current_user.id:
        raise ApiError("FORBIDDEN", "Нет прав на изменение рецепта", HTTPStatus.FORBIDDEN)

    data = _require_json()

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            raise ApiError("VALIDATION_ERROR", "Название обязательно", HTTPStatus.BAD_REQUEST)
        recipe.title = title

    if "description" in data:
        recipe.description = data.get("description")

    if "cooking_time" in data:
        recipe.cooking_time = data.get("cooking_time")

    if "difficulty" in data:
        diff = (data.get("difficulty") or "").strip()
        if diff and diff not in DIFFICULTIES:
            raise ApiError("VALIDATION_ERROR", "difficulty должен быть: Легко/Средне/Сложно", HTTPStatus.BAD_REQUEST)
        recipe.difficulty = diff or None

    if "servings" in data:
        recipe.servings = data.get("servings")

    if "image_url" in data:
        recipe.image_url = (data.get("image_url") or "").strip() or None

    # Полная замена ингредиентов/шагов, если переданы
    if "ingredients" in data:
        ingredients = data.get("ingredients") or []
        if not isinstance(ingredients, list):
            raise ApiError("VALIDATION_ERROR", "ingredients должен быть массивом", HTTPStatus.BAD_REQUEST)
        recipe.ingredients.clear()
        for idx, ing in enumerate(ingredients, start=1):
            name = (ing.get("name") or "").strip()
            if not name:
                raise ApiError("VALIDATION_ERROR", f"Ингредиент #{idx}: name обязателен", HTTPStatus.BAD_REQUEST)

            ing_obj = Ingredient(
                quantity=(ing.get("quantity") or "").strip() or None,
                order=int(ing.get("order") or idx),
            )
            ing_obj.set_name(name)  # <-- ВОТ СЮДА
            recipe.ingredients.append(ing_obj)

    if "steps" in data:
        steps = data.get("steps") or []
        if not isinstance(steps, list):
            raise ApiError("VALIDATION_ERROR", "steps должен быть массивом", HTTPStatus.BAD_REQUEST)
        recipe.steps.clear()
        for idx, st in enumerate(steps, start=1):
            desc = (st.get("description") or "").strip()
            if not desc:
                raise ApiError("VALIDATION_ERROR", f"Шаг #{idx}: description обязателен", HTTPStatus.BAD_REQUEST)
            timer = int(st.get("timer_seconds") or 0)
            if timer < 0:
                raise ApiError("VALIDATION_ERROR", f"Шаг #{idx}: timer_seconds >= 0", HTTPStatus.BAD_REQUEST)
            recipe.steps.append(
                RecipeStep(
                    order=int(st.get("order") or idx),
                    description=desc,
                    image_url=(st.get("image_url") or "").strip() or None,
                    timer_seconds=timer,
                )
            )

    if "categories" in data:
        categories_in = data.get("categories") or []
        if not isinstance(categories_in, list):
            raise ApiError("VALIDATION_ERROR", "categories должен быть массивом", HTTPStatus.BAD_REQUEST)
        recipe.categories = _get_or_create_categories(categories_in)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("DB_CONFLICT", "Конфликт данных при сохранении", HTTPStatus.CONFLICT)

    return ok(_recipe_to_dict(recipe, include_children=True))


@recipes_bp.delete("/<int:recipe_id>")
@login_required
def delete_recipe(recipe_id: int):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        raise ApiError("RECIPE_NOT_FOUND", "Рецепт не найден", HTTPStatus.NOT_FOUND)
    if recipe.author_id != current_user.id:
        raise ApiError("FORBIDDEN", "Нет прав на удаление рецепта", HTTPStatus.FORBIDDEN)

    db.session.delete(recipe)
    db.session.commit()
    return ok({"message": "Удалено"})


@recipes_bp.get("/search")
def search_by_ingredients():
    q = (request.args.get("q") or "").strip()
    if not q:
        raise ApiError("VALIDATION_ERROR", "Параметр q обязателен", HTTPStatus.BAD_REQUEST)

    parts = [p.strip() for p in q.split(",") if p.strip()]
    if not parts:
        raise ApiError("VALIDATION_ERROR", "Не заданы ингредиенты для поиска", HTTPStatus.BAD_REQUEST)

    # Нормализуем запрос (lower) и ищем по name_norm.
    # Это нужно, потому что SQLite case-insensitive поиск для Unicode (кириллица) ненадёжен [web:91]
    parts_norm = [p.lower() for p in parts]
    conds = [Ingredient.name_norm.like(f"%{p}%") for p in parts_norm]

    recipe_ids = (
        db.session.query(Ingredient.recipe_id)
        .filter(or_(*conds))
        .distinct()
        .subquery()
    )

    recipes = (
        db.session.query(Recipe)
        .filter(Recipe.id.in_(select(recipe_ids.c.recipe_id)))
        .order_by(Recipe.created_at.desc())
        .all()
    )

    return ok({"items": [_recipe_to_dict(r, include_children=False) for r in recipes]})


@recipes_bp.get("/my")
@login_required
def my_saved_recipes():
    return ok({"items": [_recipe_to_dict(r, include_children=False) for r in current_user.saved_recipes]})


@recipes_bp.post("/<int:recipe_id>/save")
@login_required
def save_recipe(recipe_id: int):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        raise ApiError("RECIPE_NOT_FOUND", "Рецепт не найден", HTTPStatus.NOT_FOUND)

    # вставка в ассоц. таблицу (если уже есть — игнорируем)
    exists = db.session.execute(
        select(user_saved_recipe.c.user_id).where(
            (user_saved_recipe.c.user_id == current_user.id)
            & (user_saved_recipe.c.recipe_id == recipe_id)
        )
    ).first()
    if exists:
        return ok({"message": "Уже в избранном"})

    db.session.execute(
        user_saved_recipe.insert().values(user_id=current_user.id, recipe_id=recipe_id)
    )
    db.session.commit()
    return ok({"message": "Сохранено"})


@recipes_bp.delete("/<int:recipe_id>/save")
@login_required
def unsave_recipe(recipe_id: int):
    db.session.execute(
        user_saved_recipe.delete().where(
            (user_saved_recipe.c.user_id == current_user.id)
            & (user_saved_recipe.c.recipe_id == recipe_id)
        )
    )
    db.session.commit()
    return ok({"message": "Удалено из избранного"})

@recipes_bp.get("/mine")
@login_required
def my_authored_recipes():
    recipes = (
        db.session.query(Recipe)
        .filter(Recipe.author_id == current_user.id)
        .order_by(Recipe.created_at.desc())
        .all()
    )
    return ok({"items": [_recipe_to_dict(r, include_children=False) for r in recipes]})

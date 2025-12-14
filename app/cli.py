from __future__ import annotations

import random
from datetime import datetime

import click
from flask import current_app
from flask.cli import with_appcontext

from app import db
from app.models import Category, Challenge, Ingredient, Recipe, RecipeStep, User


def _get_or_create_category(name: str, slug: str | None = None) -> Category:
    cat = db.session.query(Category).filter(Category.name == name).first()
    if cat:
        if slug and not cat.slug:
            cat.slug = slug
        return cat
    cat = Category(name=name, slug=slug)
    db.session.add(cat)
    return cat


@click.command("seed")
@with_appcontext
@click.option("--drop", is_flag=True, help="Очистить таблицы перед заполнением (DANGER).")
def seed_command(drop: bool):
    """
    Заполняет БД тестовыми данными:
    - пользователи
    - категории
    - рецепты с ингредиентами/шагами
    - челленджи
    """
    if drop:
        click.echo("Dropping all tables...")
        db.drop_all()
        db.create_all()
        click.echo("Tables recreated.")
    else:
        click.echo("Seeding without dropping tables...")

    # Users
    admin = db.session.query(User).filter(User.email == "admin@cookflow.local").first()
    if not admin:
        admin = User(name="Админ", email="admin@cookflow.local")
        admin.set_password("admin123")
        db.session.add(admin)

    demo = db.session.query(User).filter(User.email == "demo@cookflow.local").first()
    if not demo:
        demo = User(name="Демо", email="demo@cookflow.local")
        demo.set_password("demo123")
        db.session.add(demo)

    # Categories
    c_breakfast = _get_or_create_category("Завтраки", "breakfast")
    c_chicken = _get_or_create_category("Курица", "chicken")
    c_quick = _get_or_create_category("Быстро", "quick")
    c_dessert = _get_or_create_category("Десерты", "dessert")

    # Challenges
    def ensure_challenge(title: str, category: Category | None, target: int, days: int):
        ch = db.session.query(Challenge).filter(Challenge.title == title).first()
        if ch:
            return ch
        ch = Challenge(
            title=title,
            description="Тестовый челлендж для проверки прогресса.",
            image_url=None,
            duration_days=days,
            target_count=target,
            category=category,
        )
        db.session.add(ch)
        return ch

    ensure_challenge("Куриный марафон", c_chicken, target=3, days=7)
    ensure_challenge("Быстрые рецепты", c_quick, target=5, days=10)
    ensure_challenge("Любые рецепты: старт", None, target=2, days=3)

    # Recipes
    def ensure_recipe(title: str) -> Recipe | None:
        return db.session.query(Recipe).filter(Recipe.title == title).first()

    def create_recipe(title: str, author: User, categories: list[Category], ingredients: list[tuple[str, str]], steps: list[dict]):
        r = Recipe(
            title=title,
            description="Тестовый рецепт для демонстрации CookFlow.",
            image_url=None,
            cooking_time=random.choice([10, 15, 20, 30]),
            difficulty=random.choice(["Легко", "Средне"]),
            servings=random.choice([1, 2, 3, 4]),
            author=author,
        )
        r.categories = categories

        for idx, (name, qty) in enumerate(ingredients, start=1):
            r.ingredients.append(Ingredient(name=name, quantity=qty, order=idx))

        for idx, st in enumerate(steps, start=1):
            r.steps.append(
                RecipeStep(
                    order=idx,
                    description=st["description"],
                    image_url=st.get("image_url"),
                    timer_seconds=int(st.get("timer_seconds") or 0),
                )
            )

        db.session.add(r)
        return r

    if not ensure_recipe("Омлет за 5 минут"):
        create_recipe(
            "Омлет за 5 минут",
            author=demo,
            categories=[c_breakfast, c_quick],
            ingredients=[("Яйца", "2 шт"), ("Молоко", "50 мл"), ("Соль", "по вкусу")],
            steps=[
                {"description": "Взбейте яйца с молоком и солью.", "timer_seconds": 0},
                {"description": "Разогрейте сковороду и вылейте смесь.", "timer_seconds": 60},
                {"description": "Готовьте до желаемой плотности.", "timer_seconds": 180},
            ],
        )

    if not ensure_recipe("Курица с сыром"):
        create_recipe(
            "Курица с сыром",
            author=demo,
            categories=[c_chicken],
            ingredients=[("Куриное филе", "300 г"), ("Сыр", "100 г"), ("Соль", "по вкусу")],
            steps=[
                {"description": "Нарежьте курицу и посолите.", "timer_seconds": 0},
                {"description": "Обжарьте на среднем огне.", "timer_seconds": 420},
                {"description": "Добавьте сыр и дождитесь расплавления.", "timer_seconds": 120},
            ],
        )

    if not ensure_recipe("Простой десерт"):
        create_recipe(
            "Простой десерт",
            author=admin,
            categories=[c_dessert, c_quick],
            ingredients=[("Йогурт", "200 г"), ("Мёд", "1 ст.л.")],
            steps=[
                {"description": "Смешайте йогурт и мёд.", "timer_seconds": 0},
                {"description": "Охладите перед подачей.", "timer_seconds": 300},
            ],
        )

    db.session.commit()
    click.echo("Seed completed. Users: admin@cookflow.local/admin123, demo@cookflow.local/demo123")

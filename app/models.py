from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


# Ассоциативная таблица для избранного (UserSavedRecipe)
user_saved_recipe = db.Table(
    "user_saved_recipe",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipes.id"), primary_key=True),
    db.Column("saved_at", db.DateTime, default=datetime.utcnow, nullable=False),
)

# Ассоциативная таблица Recipe <-> Category (many-to-many)
recipe_category = db.Table(
    "recipe_category",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipes.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"), primary_key=True),
)


@login_manager.user_loader
def load_user(user_id: str):
    # Flask-Login требует user_loader, возвращающий пользователя или None [web:41]
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    recipes = db.relationship(
        "Recipe",
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    comments = db.relationship(
        "Comment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    challenge_progress = db.relationship(
        "ChallengeProgress",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    saved_recipes = db.relationship(
        "Recipe",
        secondary=user_saved_recipe,
        back_populates="saved_by_users",
        lazy="selectin",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Recipe(db.Model):
    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    cooking_time = db.Column(db.Integer)  # minutes
    difficulty = db.Column(db.String(50))  # 'Легко'/'Средне'/'Сложно'
    servings = db.Column(db.Integer)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", back_populates="recipes")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    ingredients = db.relationship(
        "Ingredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="Ingredient.order",
        lazy="selectin",
    )

    steps = db.relationship(
        "RecipeStep",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeStep.order",
        lazy="selectin",
    )

    comments = db.relationship(
        "Comment",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
        lazy="selectin",
    )

    categories = db.relationship(
        "Category",
        secondary=recipe_category,
        back_populates="recipes",
        lazy="selectin",
    )

    saved_by_users = db.relationship(
        "User",
        secondary=user_saved_recipe,
        back_populates="saved_recipes",
        lazy="selectin",
    )


class Ingredient(db.Model):
    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False, index=True)
    recipe = db.relationship("Recipe", back_populates="ingredients")

    name = db.Column(db.String(200), nullable=False)
    name_norm = db.Column(db.String(200), nullable=False, index=True, default="")

    quantity = db.Column(db.String(100))
    order = db.Column(db.Integer, nullable=False, default=1)

    def set_name(self, name: str):
        self.name = name
        self.name_norm = (name or "").strip().lower()



class RecipeStep(db.Model):
    __tablename__ = "recipe_steps"

    id = db.Column(db.Integer, primary_key=True)

    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False, index=True)
    recipe = db.relationship("Recipe", back_populates="steps")

    order = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    timer_seconds = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.CheckConstraint("`order` >= 1", name="ck_recipe_steps_order_ge_1"),
        db.CheckConstraint("timer_seconds >= 0", name="ck_recipe_steps_timer_ge_0"),
    )


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)

    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    recipe = db.relationship("Recipe", back_populates="comments")
    user = db.relationship("User", back_populates="comments")


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True)

    recipes = db.relationship(
        "Recipe",
        secondary=recipe_category,
        back_populates="categories",
        lazy="selectin",
    )

    challenges = db.relationship(
        "Challenge",
        back_populates="category",
        lazy="selectin",
    )


class Challenge(db.Model):
    __tablename__ = "challenges"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))

    duration_days = db.Column(db.Integer)   # nullable допускаем
    target_count = db.Column(db.Integer)    # nullable допускаем

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True)
    category = db.relationship("Category", back_populates="challenges")

    progress_entries = db.relationship(
        "ChallengeProgress",
        back_populates="challenge",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ChallengeProgress(db.Model):
    __tablename__ = "challenge_progress"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False, index=True)

    completed_count = db.Column(db.Integer, nullable=False, default=0)

    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="challenge_progress")
    challenge = db.relationship("Challenge", back_populates="progress_entries")

    __table_args__ = (
        db.UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge_progress"),
        db.CheckConstraint("completed_count >= 0", name="ck_challenge_completed_ge_0"),
    )

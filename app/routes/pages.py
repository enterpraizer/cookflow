from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def index():
    return render_template("index.html")


@pages_bp.get("/my-recipes")
def my_recipes():
    return render_template("my_recipes.html")


@pages_bp.get("/challenges")
def challenges():
    return render_template("challenges.html")


@pages_bp.get("/recipe/<int:recipe_id>")
def recipe_detail(recipe_id: int):
    return render_template("recipe_detail.html", recipe_id=recipe_id)


@pages_bp.get("/login")
def login():
    return render_template("login.html")


@pages_bp.get("/register")
def register():
    return render_template("register.html")

@pages_bp.get("/add-recipe")
def add_recipe():
    return render_template("add_recipe.html")

@pages_bp.get("/recipe/<int:recipe_id>/edit")
def edit_recipe(recipe_id: int):
    return render_template("edit_recipe.html", recipe_id=recipe_id)

@pages_bp.get("/my-authored")
def my_authored():
    return render_template("my_authored_recipes.html")

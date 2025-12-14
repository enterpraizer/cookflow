import os

folders = [
    "app",
    "app/routes",
    "app/static/css",
    "app/static/js",
    "app/static/uploads",
    "app/templates/components",
    "migrations"
]

files = {
    "app/__init__.py": "",
    "app/models.py": "",
    "app/forms.py": "",

    "app/routes/__init__.py": "",
    "app/routes/auth.py": "",
    "app/routes/recipes.py": "",
    "app/routes/cooking.py": "",
    "app/routes/challenges.py": "",
    "app/routes/comments.py": "",

    "app/static/css/style.css": "",
    "app/static/js/app.js": "",

    "app/templates/base.html": "",
    "app/templates/index.html": "",
    "app/templates/my_recipes.html": "",
    "app/templates/challenges.html": "",
    "app/templates/recipe_detail.html": "",

    "app/templates/components/header.html": "",
    "app/templates/components/recipe_card.html": "",
    "app/templates/components/cooking_mode.html": "",

    "config.py": "",
    "requirements.txt": "",
    "run.py": ""
}

# Создание папок
for folder in folders:
    os.makedirs(folder, exist_ok=True)

# Создание файлов
for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Архитектура проекта cookflow успешно создана!")

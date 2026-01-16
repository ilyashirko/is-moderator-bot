import settings
from database import database
import hashlib
import json

class ObsceneWordFound(Exception):
    pass


async def check_obscene(text: str) -> None:
    if not text:
        return

    normalized = (
        text
        .lower()
        .replace("ё", "е")
    )

    for rx in settings._PATTERNS:
        if rx.search(normalized):
            raise ObsceneWordFound(f"Найдено матерное слово: {rx.pattern}")
        

async def extract_name(user):
    if user.username:
        return f"@{user.username}"
    if user.first_name:
        return user.first_name
    return "Неопознанный пользователь"


async def startup_task(app):
    print("Бот запускается...")
    await database.init_models()
    print("Инициализация завершена!")

async def get_user_hash(user_data: dict):
    return hashlib.md5(json.dumps(user_data, sort_keys=True).encode()).hexdigest()
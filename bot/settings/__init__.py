from environs import Env
import logging
import re

env = Env()
env.read_env()

TELEGRAM_BOT_TOKEN = env.str("TELEGRAM_BOT_TOKEN")

MODERATORS_IDS = [int(i) for i in env.list("MODERATORS_IDS", list())]

MODERATOR_TOPIC_ID = env.int("MODERATOR_TOPIC_ID", None)

POSTGRES_HOST = env.str("POSTGRES_HOST")
POSTGRES_PORT = env.int("POSTGRES_PORT", 5432)
POSTGRES_USER = env.str("POSTGRES_USER")
POSTGRES_PASSWORD = env.str("POSTGRES_PASSWORD")
POSTGRES_DB = env.str("POSTGRES_DB")

STRIKES_LIMIT = env.int("STRIKES_LIMIT", 3)
STRIKES_LIMIT_PERIOD_MONTHS = env.int("STRIKES_LIMIT_PERIOD_MONTHS", 1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


_OBSCENE_ROOTS = env.list("OBSCENE_ROOTS")

_FULL_WORD_PATTERNS = env.list("FULL_WORD_PATTERNS")

# Компилируем регулярки с границами слов
_PATTERNS = [
    re.compile(rf"\b{root}\w*\b", re.IGNORECASE)
    for root in _OBSCENE_ROOTS
] + [
    re.compile(rf"\b{root}\b", re.IGNORECASE)
    for root in _FULL_WORD_PATTERNS
]

BAN_LIMITS = {
    0: 7,
    1: 30,
    2: 180,
    3: 365
}
import json
from pathlib import Path

from .models import Dish

ROOT = Path(__file__).resolve().parents[2]
MENUS_PATH = ROOT / "data" / "menus.json"
QUESTIONS_PATH = ROOT / "eval" / "questions.json"


def load_dishes(path: Path = MENUS_PATH) -> list[Dish]:
    """Lê os cardápios fictícios e devolve uma lista plana de pratos."""
    restaurants = json.loads(path.read_text(encoding="utf-8"))
    return [
        Dish(restaurant=restaurant["name"], **dish)
        for restaurant in restaurants
        for dish in restaurant["dishes"]
    ]


def load_questions(path: Path = QUESTIONS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))

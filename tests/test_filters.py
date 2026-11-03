import pytest

from menusearch.data import load_questions
from menusearch.filters import parse_filters
from menusearch.models import Filters


def test_exemplo_do_plano():
    assert parse_filters("algo vegetariano até R$ 40 que chegue rápido") == Filters(
        max_price_cents=4000, max_prep_minutes=20
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("pizza até R$ 50,50", Filters(max_price_cents=5050, category="pizza")),
        ("pizza até R$ 50,5", Filters(max_price_cents=5050, category="pizza")),
        ("lanche em até 15 minutos", Filters(max_prep_minutes=15)),
        ("quero algo rápida", Filters(max_prep_minutes=20)),
        ("sushi ou pizza", Filters()),  # duas categorias: não filtra
        ("uma sopa quentinha", Filters()),
        ("menos de R$ 30", Filters(max_price_cents=3000)),
    ],
)
def test_casos_de_borda(text, expected):
    assert parse_filters(text) == expected


def test_pergunta_sem_filtro_fica_vazia():
    assert parse_filters("algo com cogumelos").is_empty()


@pytest.mark.parametrize("question", load_questions(), ids=lambda q: q["id"])
def test_parser_bate_com_o_filtro_esperado_de_cada_pergunta(question):
    assert parse_filters(question["text"]) == Filters(**question["expected_filters"])

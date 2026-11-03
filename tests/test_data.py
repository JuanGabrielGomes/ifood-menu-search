from menusearch.data import load_dishes, load_questions
from menusearch.models import Filters

dishes = load_dishes()
questions = load_questions()
by_id = {d.id: d for d in dishes}


def test_ids_de_pratos_sao_unicos():
    assert len(by_id) == len(dishes) == 80


def test_ids_de_perguntas_sao_unicos_e_ha_30():
    assert len({q["id"] for q in questions}) == len(questions) == 30


def test_pratos_tem_dados_validos():
    for d in dishes:
        assert d.price_cents > 0 and d.prep_minutes > 0
        assert d.description.strip() and d.category


def test_relevantes_existem_e_nao_se_repetem():
    for q in questions:
        assert q["relevant"], q["id"]
        assert len(set(q["relevant"])) == len(q["relevant"]), q["id"]
        assert all(r in by_id for r in q["relevant"]), q["id"]


def test_relevantes_respeitam_as_restricoes_da_pergunta():
    """Protege os rótulos feitos à mão contra erro de digitação."""
    for q in questions:
        filters = Filters(**q["expected_filters"])
        for dish_id in q["relevant"]:
            dish = by_id[dish_id]
            assert filters.matches(dish), f"{q['id']}: {dish_id} viola os filtros"
            if q.get("requires_vegetarian"):
                assert dish.vegetarian, f"{q['id']}: {dish_id} não é vegetariano"


def test_chunk_traz_nome_descricao_e_restaurante():
    chunk = by_id["burger-04"].chunk()
    assert "Burger vegetariano" in chunk and "Burger Norte" in chunk and "grão-de-bico" in chunk

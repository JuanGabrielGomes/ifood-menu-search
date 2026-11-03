import pytest

from menusearch.data import load_dishes
from menusearch.embed import HashEmbedder
from menusearch.filters import parse_filters
from menusearch.search import search
from menusearch.store import MemoryStore

dishes = load_dishes()
by_id = {d.id: d for d in dishes}
embedder = HashEmbedder()
store = MemoryStore()
store.upsert(dishes, embedder.embed([d.chunk() for d in dishes]))


def test_devolve_k_resultados():
    assert len(search(store, embedder, "pizza", k=5)) == 5


def test_resultado_mais_proximo_e_o_prato_com_as_mesmas_palavras():
    top = search(store, embedder, "Onion rings anéis de cebola empanados", k=1)
    assert top == ["burger-07"]


@pytest.mark.parametrize(
    "query",
    ["algo vegetariano até R$ 40 que chegue rápido", "sushi barato, até R$ 25", "pizza que chegue em até 25 minutos"],
)
def test_com_filtros_todo_resultado_respeita_a_pergunta(query):
    filters = parse_filters(query)
    ids = search(store, embedder, query, k=5, use_filters=True)
    assert ids and all(filters.matches(by_id[i]) for i in ids)


def test_sem_filtros_o_ranking_ignora_preco():
    ids = search(store, embedder, "sushi barato, até R$ 25", k=10, use_filters=False)
    assert any(by_id[i].price_cents > 2500 for i in ids)


def test_filtro_sem_candidatos_devolve_lista_vazia():
    assert search(store, embedder, "pizza até R$ 1", k=5, use_filters=True) == []

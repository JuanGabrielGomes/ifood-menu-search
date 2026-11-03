from types import SimpleNamespace

from fastapi.testclient import TestClient

from menusearch.answer import cited_ids, format_dishes, generate_answer
from menusearch.api import create_app
from menusearch.data import load_dishes
from menusearch.embed import HashEmbedder
from menusearch.store import MemoryStore

dishes = load_dishes()
embedder = HashEmbedder()
store = MemoryStore()
store.upsert(dishes, embedder.embed([d.chunk() for d in dishes]))


def test_cited_ids_na_ordem_e_sem_repetir():
    assert cited_ids("Recomendo [burger-04] e [verde-03]. O [burger-04] é bom. [texto]") == ["burger-04", "verde-03"]


def test_format_dishes_traz_id_preco_e_tempo():
    line = format_dishes([dishes[0]])
    assert line.startswith("[cantina-01]") and "R$ 39.00" in line and "35 min" in line


def test_generate_answer_monta_pedido_e_junta_texto():
    seen = {}

    class FakeMessages:
        def create(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=" Peça o [cantina-01]. ")])

    client = SimpleNamespace(messages=FakeMessages())
    answer = generate_answer(client, "algo com carne", dishes[:2], model="modelo-fake")
    assert answer == "Peça o [cantina-01]."
    assert seen["model"] == "modelo-fake"
    assert "Pergunta do cliente: algo com carne" in seen["messages"][0]["content"]
    assert "[cantina-01]" in seen["messages"][0]["content"]


def test_search_endpoint():
    client = TestClient(create_app(store, embedder, dishes))
    response = client.post("/search", json={"query": "pizza até R$ 30", "k": 5})
    assert response.status_code == 200
    body = response.json()["dishes"]
    # Só duas pizzas custam até R$ 30 no cardápio de teste.
    assert {d["id"] for d in body} == {"pizza-07", "pizza-08"}


def test_search_valida_a_entrada():
    client = TestClient(create_app(store, embedder, dishes))
    assert client.post("/search", json={"query": "a"}).status_code == 422
    assert client.post("/search", json={"query": "pizza", "k": 99}).status_code == 422


def test_ask_sem_chave_devolve_503():
    client = TestClient(create_app(store, embedder, dishes))
    assert client.post("/ask", json={"query": "pizza"}).status_code == 503


def test_ask_descarta_citacao_fora_dos_pratos_recuperados():
    def answerer(query, found):
        return f"Peça o [{found[0].id}] ou o [inventado-99]."

    client = TestClient(create_app(store, embedder, dishes, answerer))
    body = client.post("/ask", json={"query": "pizza margherita", "k": 3}).json()
    assert body["citations"] == [body["dishes"][0]["id"]]
    assert "inventado-99" in body["answer"] and "inventado-99" not in body["citations"]

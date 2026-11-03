import os
from typing import Callable, Sequence

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .answer import cited_ids, generate_answer
from .data import load_dishes
from .embed import Embedder
from .models import Dish
from .search import search
from .store import Store

Answerer = Callable[[str, Sequence[Dish]], str]


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    k: int = Field(default=5, ge=1, le=20)
    use_filters: bool = True


class DishOut(BaseModel):
    id: str
    name: str
    restaurant: str
    price_cents: int
    prep_minutes: int
    category: str


class SearchResponse(BaseModel):
    dishes: list[DishOut]


class AskResponse(SearchResponse):
    answer: str
    citations: list[str]
    """Ids citados na resposta que estão entre os pratos recuperados. Ids fora da lista são descartados."""


def create_app(store: Store, embedder: Embedder, dishes: Sequence[Dish], answerer: Answerer | None = None) -> FastAPI:
    app = FastAPI(title="Busca semântica em cardápios")
    by_id = {d.id: d for d in dishes}

    def retrieve(request: SearchRequest) -> list[Dish]:
        ids = search(store, embedder, request.query, request.k, request.use_filters)
        return [by_id[i] for i in ids]

    def to_out(found: Sequence[Dish]) -> list[DishOut]:
        return [DishOut(**{f: getattr(d, f) for f in DishOut.model_fields}) for d in found]

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/search", response_model=SearchResponse)
    def search_endpoint(request: SearchRequest) -> SearchResponse:
        return SearchResponse(dishes=to_out(retrieve(request)))

    @app.post("/ask", response_model=AskResponse)
    def ask_endpoint(request: SearchRequest) -> AskResponse:
        if answerer is None:
            raise HTTPException(status_code=503, detail="Resposta gerada indisponível: defina ANTHROPIC_API_KEY.")
        found = retrieve(request)
        answer = answerer(request.query, found)
        valid = {d.id for d in found}
        return AskResponse(dishes=to_out(found), answer=answer, citations=[c for c in cited_ids(answer) if c in valid])

    return app


def build_default_app() -> FastAPI:
    """Monta a aplicação com configuração de ambiente. Uso: uvicorn menusearch.api:build_default_app --factory"""
    from .embed import FastEmbedder
    from .store import MemoryStore, PgVectorStore

    dishes = load_dishes()
    embedder = FastEmbedder()
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        store: Store = PgVectorStore(database_url)
    else:
        store = MemoryStore()
        store.upsert(dishes, embedder.embed([d.chunk() for d in dishes]))

    answerer: Answerer | None = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        from anthropic import Anthropic

        client = Anthropic()
        answerer = lambda query, found: generate_answer(client, query, found)  # noqa: E731
    return create_app(store, embedder, dishes, answerer)

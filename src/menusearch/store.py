from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

from .models import Dish, Filters

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


class Store(Protocol):
    def upsert(self, dishes: Sequence[Dish], vectors: np.ndarray) -> None: ...

    def search(self, vector: np.ndarray, k: int, filters: Filters) -> list[str]:
        """Ids dos `k` pratos mais próximos (cosseno) entre os que passam nos filtros."""
        ...


class MemoryStore:
    """Mesma lógica do pgvector, em numpy. Usado nos testes e na avaliação sem banco."""

    def __init__(self) -> None:
        self._dishes: list[Dish] = []
        self._vectors = np.empty((0, 0), dtype=np.float32)

    def upsert(self, dishes: Sequence[Dish], vectors: np.ndarray) -> None:
        self._dishes = list(dishes)
        self._vectors = vectors

    def search(self, vector: np.ndarray, k: int, filters: Filters) -> list[str]:
        scores = self._vectors @ vector
        order = np.argsort(-scores, kind="stable")
        return [self._dishes[i].id for i in order if filters.matches(self._dishes[i])][:k]


class PgVectorStore:
    """Postgres com a extensão pgvector (local via Docker ou Supabase)."""

    def __init__(self, conninfo: str) -> None:
        import psycopg
        from pgvector.psycopg import register_vector

        self._conn = psycopg.connect(conninfo, autocommit=True)
        self._conn.execute("create extension if not exists vector")
        self._conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        register_vector(self._conn)

    def upsert(self, dishes: Sequence[Dish], vectors: np.ndarray) -> None:
        with self._conn.cursor() as cur:
            for dish, vector in zip(dishes, vectors, strict=True):
                cur.execute(
                    """
                    insert into dishes (id, restaurant, name, description, category, price_cents, prep_minutes, vegetarian, embedding)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      restaurant = excluded.restaurant, name = excluded.name, description = excluded.description,
                      category = excluded.category, price_cents = excluded.price_cents,
                      prep_minutes = excluded.prep_minutes, vegetarian = excluded.vegetarian,
                      embedding = excluded.embedding
                    """,
                    (dish.id, dish.restaurant, dish.name, dish.description, dish.category,
                     dish.price_cents, dish.prep_minutes, dish.vegetarian, vector),
                )

    def search(self, vector: np.ndarray, k: int, filters: Filters) -> list[str]:
        rows = self._conn.execute(
            """
            select id from dishes
            where (%(max_price)s::int is null or price_cents <= %(max_price)s::int)
              and (%(max_minutes)s::int is null or prep_minutes <= %(max_minutes)s::int)
              and (%(category)s::text is null or category = %(category)s::text)
            order by embedding <=> %(vector)s
            limit %(k)s
            """,
            {
                "max_price": filters.max_price_cents,
                "max_minutes": filters.max_prep_minutes,
                "category": filters.category,
                "vector": vector,
                "k": k,
            },
        ).fetchall()
        return [row[0] for row in rows]

"""Carrega os cardápios no Postgres com pgvector. Uso: python -m menusearch.ingest"""

import os
import sys

from .data import load_dishes
from .embed import FastEmbedder
from .store import PgVectorStore


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("Defina DATABASE_URL (veja .env.example).")
    dishes = load_dishes()
    embedder = FastEmbedder()
    store = PgVectorStore(database_url)
    store.upsert(dishes, embedder.embed([d.chunk() for d in dishes]))
    print(f"{len(dishes)} pratos carregados com o modelo {embedder.name}.")


if __name__ == "__main__":
    main()

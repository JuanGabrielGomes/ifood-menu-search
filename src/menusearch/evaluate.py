"""Compara busca só vetorial com vetorial + filtros de metadados. Uso: python -m menusearch.evaluate [--pg]"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .data import ROOT, load_dishes, load_questions
from .embed import Embedder, FastEmbedder
from .filters import parse_filters
from .metrics import hit_at_k, recall_at_k
from .search import search
from .store import MemoryStore, PgVectorStore, Store

K = 5
STRATEGIES = {"só vetor": False, "vetor + filtros": True}


def evaluate(store: Store, embedder: Embedder, questions: list[dict]) -> list[dict]:
    rows = []
    for q in questions:
        row = {
            "id": q["id"],
            "text": q["text"],
            "relevant": q["relevant"],
            "has_filters": not parse_filters(q["text"]).is_empty(),
        }
        for name, use_filters in STRATEGIES.items():
            retrieved = search(store, embedder, q["text"], K, use_filters)
            row[name] = {
                "retrieved": retrieved,
                "recall": recall_at_k(retrieved, q["relevant"], K),
                "hit": hit_at_k(retrieved, q["relevant"], K),
            }
        rows.append(row)
    return rows


def summarize(rows: list[dict]) -> dict:
    groups = {
        "todas": rows,
        "com filtros na pergunta": [r for r in rows if r["has_filters"]],
        "sem filtros na pergunta": [r for r in rows if not r["has_filters"]],
    }
    return {
        group: {
            "perguntas": len(items),
            **{
                strategy: {
                    "recall@5": sum(r[strategy]["recall"] for r in items) / len(items),
                    "acerto@5": sum(r[strategy]["hit"] for r in items) / len(items),
                }
                for strategy in STRATEGIES
            },
        }
        for group, items in groups.items()
        if items
    }


def print_report(summary: dict, rows: list[dict], model: str, backend: str) -> None:
    print(f"Modelo de embeddings: {model} | backend: {backend} | k = {K}\n")
    print("| Grupo | Perguntas | Estratégia | recall@5 | acerto@5 |\n|---|---|---|---|---|")
    for group, data in summary.items():
        for strategy in STRATEGIES:
            m = data[strategy]
            print(f"| {group} | {data['perguntas']} | {strategy} | {m['recall@5']:.3f} | {m['acerto@5']:.3f} |")

    worse = [r for r in rows if r["vetor + filtros"]["recall"] < r["só vetor"]["recall"]]
    better = [r for r in rows if r["vetor + filtros"]["recall"] > r["só vetor"]["recall"]]
    print(f"\nFiltros melhoraram o recall em {len(better)} perguntas e pioraram em {len(worse)}.")
    for r in worse:
        print(f"  piorou: {r['id']} \"{r['text']}\" ({r['só vetor']['recall']:.2f} -> {r['vetor + filtros']['recall']:.2f})")


def main() -> None:
    dishes = load_dishes()
    questions = load_questions()
    embedder = FastEmbedder()
    vectors = embedder.embed([d.chunk() for d in dishes])

    if "--pg" in sys.argv:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            sys.exit("Defina DATABASE_URL para usar --pg.")
        store: Store = PgVectorStore(database_url)
        backend = "pgvector"
    else:
        store = MemoryStore()
        backend = "memória (numpy)"
    store.upsert(dishes, vectors)

    rows = evaluate(store, embedder, questions)
    summary = summarize(rows)
    print_report(summary, rows, embedder.name, backend)

    results = ROOT / "eval" / "results"
    results.mkdir(parents=True, exist_ok=True)
    out = results / f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')}.json"
    out.write_text(
        json.dumps({"model": embedder.name, "backend": backend, "k": K, "summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nResultado completo em {Path(out).relative_to(ROOT)}")


if __name__ == "__main__":
    main()

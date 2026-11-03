from typing import Sequence


def recall_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int = 5) -> float:
    """Fração dos relevantes recuperada no top-k, limitada a k.

    O denominador é min(|relevantes|, k): com mais de k relevantes, o máximo possível é recuperar k.
    """
    hits = len(set(retrieved[:k]) & set(relevant))
    return hits / min(len(relevant), k)


def hit_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int = 5) -> bool:
    """Pelo menos um prato relevante no top-k."""
    return bool(set(retrieved[:k]) & set(relevant))

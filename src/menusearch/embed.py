import hashlib
import re
from typing import Protocol

import numpy as np

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:
        """Devolve uma matriz (n, dim) com vetores de norma 1."""
        ...


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return (vectors / np.where(norms == 0, 1, norms)).astype(np.float32)


class FastEmbedder:
    """Embeddings multilíngues locais (ONNX, sem API e sem custo). O modelo é baixado na primeira execução."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        from fastembed import TextEmbedding

        self.name = model_name
        self._model = TextEmbedding(model_name=model_name)
        self.dim = len(next(iter(self._model.embed(["teste"]))))

    def embed(self, texts: list[str]) -> np.ndarray:
        return _normalize(np.array(list(self._model.embed(texts)), dtype=np.float32))


class HashEmbedder:
    """Saco de palavras com hash. Determinístico e sem download: serve só para testes offline."""

    name = "hash-bag-of-words"

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in re.findall(r"\w+", text.lower()):
                index = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
                vectors[row, index] += 1.0
        return _normalize(vectors)

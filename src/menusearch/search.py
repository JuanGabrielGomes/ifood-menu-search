from .embed import Embedder
from .filters import parse_filters
from .models import Filters
from .store import Store


def search(store: Store, embedder: Embedder, query: str, k: int = 5, use_filters: bool = False) -> list[str]:
    """Busca vetorial. Com `use_filters`, preço, tempo e categoria da pergunta viram WHERE antes do ranking."""
    filters = parse_filters(query) if use_filters else Filters()
    vector = embedder.embed([query])[0]
    return store.search(vector, k, filters)

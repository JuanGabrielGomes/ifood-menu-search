from dataclasses import dataclass


@dataclass(frozen=True)
class Dish:
    id: str
    restaurant: str
    name: str
    description: str
    category: str
    price_cents: int
    prep_minutes: int
    vegetarian: bool

    def chunk(self) -> str:
        """Texto do trecho que vira embedding: um prato por trecho."""
        return f"{self.name}. {self.description} Restaurante: {self.restaurant}. Categoria: {self.category}."


@dataclass(frozen=True)
class Filters:
    """Filtros de metadados extraídos da pergunta. Campo `None` significa sem restrição."""

    max_price_cents: int | None = None
    max_prep_minutes: int | None = None
    category: str | None = None

    def is_empty(self) -> bool:
        return self.max_price_cents is None and self.max_prep_minutes is None and self.category is None

    def matches(self, dish: Dish) -> bool:
        if self.max_price_cents is not None and dish.price_cents > self.max_price_cents:
            return False
        if self.max_prep_minutes is not None and dish.prep_minutes > self.max_prep_minutes:
            return False
        return self.category is None or dish.category == self.category

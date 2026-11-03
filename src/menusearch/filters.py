import re

from .models import Filters

# "Rápido" nas perguntas dos clientes significa preparo de até 20 minutos.
FAST_MINUTES = 20

_PRICE = re.compile(
    r"(?:até|ate|no máximo|no maximo|menos de|abaixo de)\s*r\$\s*(\d+)(?:[.,](\d{1,2}))?",
    re.IGNORECASE,
)
_TIME = re.compile(r"(?:até|ate|no máximo|no maximo)\s*(\d+)\s*(?:min|minutos)", re.IGNORECASE)
_FAST = re.compile(r"\b(?:rápid[oa]s?|rapid[oa]s?)\b", re.IGNORECASE)

# Palavra da pergunta -> categoria do cardápio. Se a pergunta citar mais de uma categoria, não filtra.
_CATEGORIES: dict[str, re.Pattern[str]] = {
    "pizza": re.compile(r"\bpizzas?\b", re.IGNORECASE),
    "japonesa": re.compile(r"\b(?:sushi|temaki|japon[eê]s|japonesa)s?\b", re.IGNORECASE),
    "hamburguer": re.compile(r"\b(?:h[aá]mb[uú]rgue(?:r|res)|burgers?)\b", re.IGNORECASE),
    "doces": re.compile(r"\b(?:sobremesas?|doces?)\b", re.IGNORECASE),
    "italiana": re.compile(r"\bmassas?\b", re.IGNORECASE),
    "brasileira": re.compile(r"\bbrasileir[oa]s?\b", re.IGNORECASE),
    "saudavel": re.compile(r"\b(?:saud[aá]veis|saud[aá]vel|saladas?)\b", re.IGNORECASE),
    "churrasco": re.compile(r"\bchurrasco\b", re.IGNORECASE),
}


def parse_filters(question: str) -> Filters:
    """Extrai preço máximo, tempo máximo e categoria de uma pergunta em linguagem natural."""
    max_price: int | None = None
    price = _PRICE.search(question)
    if price:
        reais, centavos = int(price.group(1)), price.group(2)
        max_price = reais * 100 + (int(centavos.ljust(2, "0")) if centavos else 0)

    max_minutes: int | None = None
    time = _TIME.search(question)
    if time:
        max_minutes = int(time.group(1))
    elif _FAST.search(question):
        max_minutes = FAST_MINUTES

    found = [name for name, pattern in _CATEGORIES.items() if pattern.search(question)]
    category = found[0] if len(found) == 1 else None

    return Filters(max_price_cents=max_price, max_prep_minutes=max_minutes, category=category)

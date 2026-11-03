# ifood-menu-search

Busca semântica em cardápios de delivery: perguntas como "algo vegetariano até R$ 40 que chegue rápido" são respondidas a partir de pratos fictícios, combinando filtros de metadados (preço, tempo, categoria) com busca vetorial, e a resposta gerada cita os pratos encontrados.

> **Estado:** a avaliação abaixo foi medida primeiro com o backend em memória (numpy) e repetida contra um Postgres real com pgvector (imagem `pgvector/pgvector:pg17`, via Docker). Os números das duas execuções são idênticos. Com 80 pratos o planejador pode preferir varredura sequencial ao índice HNSW, então isto valida a consulta e a ingestão, não o desempenho do índice.

## Pipeline

1. **Ingestão:** 80 pratos fictícios de 8 restaurantes (`data/menus.json`), um trecho por prato (nome, descrição, restaurante e categoria).
2. **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões) rodando localmente via fastembed, sem API e sem custo.
3. **Armazenamento:** Postgres com pgvector (`db/schema.sql`), local via Docker ou Supabase. Uma implementação em memória com a mesma lógica serve aos testes e à avaliação.
4. **Busca:** duas estratégias comparadas.
   - **Só vetor:** ranking por similaridade de cosseno com a pergunta inteira.
   - **Vetor + filtros:** preço máximo, tempo máximo e categoria extraídos da pergunta (`src/menusearch/filters.py`) viram `WHERE` antes do ranking.
5. **Resposta:** o Claude responde só com os pratos recuperados e cita cada um pelo id. Ids citados que não estão entre os recuperados são descartados na API.

## Avaliação

30 perguntas com os pratos relevantes marcados à mão (`eval/questions.json`). Métricas:

- **recall@5**, com denominador `min(|relevantes|, 5)`: com mais de 5 relevantes, o máximo possível é recuperar 5;
- **acerto@5**: ao menos um prato relevante no top 5.

Metade das perguntas (15) tem filtros que o parser reconhece; a outra metade é puramente semântica.

| Grupo | Estratégia | recall@5 | acerto@5 |
|---|---|---|---|
| todas (30) | só vetor | 0,553 | 0,833 |
| todas (30) | vetor + filtros | **0,658** | **0,900** |
| com filtros na pergunta (15) | só vetor | 0,613 | 0,867 |
| com filtros na pergunta (15) | vetor + filtros | **0,824** | **1,000** |
| sem filtros na pergunta (15) | só vetor | 0,492 | 0,800 |
| sem filtros na pergunta (15) | vetor + filtros | 0,492 | 0,800 |

As duas últimas linhas são idênticas por construção: sem filtro reconhecido, as duas estratégias fazem a mesma consulta. Servem de verificação de sanidade.

**Onde os filtros ajudaram.** Em 5 perguntas, e em nenhuma pioraram. O vetor não enxerga preço nem tempo, então perguntas com restrição numérica ganham mais:

| Pergunta | só vetor | vetor + filtros |
|---|---|---|
| pizza que chegue em até 25 minutos | 0,00 | 1,00 |
| alguma coisa doce até R$ 20 | 0,40 | 1,00 |
| sushi barato, até R$ 25 | 0,33 | 1,00 |
| algo leve e saudável para o almoço | 0,40 | 0,80 |
| pizza de queijo até R$ 50 | 0,00 | 0,50 |

**Onde não ajudaram.** No exemplo que motivou o projeto, "algo vegetariano até R$ 40 que chegue rápido", as duas estratégias dão 0,80: o vetor sozinho já acertava 4 dos 5 primeiros resultados. Além disso, "vegetariano" não é um filtro (a coluna existe, mas o parser não a usa).

**O ponto fraco é a busca semântica pura**, com recall de 0,49 nas perguntas sem filtro:

| Pergunta | recall@5 |
|---|---|
| sopa quentinha | 0,00 |
| petisco de boteco para ver o jogo | 0,00 |
| refeição completa com arroz e feijão | 0,00 |
| carne na brasa | 0,20 |
| algo com queijo derretido | 0,20 |

Em "sopa quentinha" o top 5 trouxe parmegiana, espaguete, maminha, misto quente e poke, e deixou de fora a "Sopa de abóbora com gengibre". Um modelo pequeno (220 MB) com consultas curtas perde palavras-chave óbvias; uma busca híbrida (vetor + texto) é o próximo experimento.

### Ablação do texto do trecho (exploratória)

Testei se o sufixo "Restaurante … Categoria …" do trecho atrapalhava. recall@5:

| Texto do trecho | só vetor | vetor + filtros |
|---|---|---|
| nome + descrição + restaurante + categoria (usado) | 0,553 | 0,658 |
| nome + descrição | 0,526 | 0,700 |
| só descrição | 0,588 | 0,718 |

As diferenças são pequenas e não seguem uma direção única. Com 30 perguntas isso é ruído, e o ganho de "só descrição" não justifica trocar o formato, até porque ajustar o formato olhando a própria avaliação é um jeito fácil de se enganar. Mantive o formato original.

### Limites desta medição

- Pratos, perguntas e rótulos são fictícios e foram escritos por mim. Em perguntas como "petisco de boteco" a relevância é subjetiva.
- São 30 perguntas e um único modelo de embeddings, sem intervalo de confiança.
- O parser de filtros é por regras (regex). Extrair filtros com um LLM seria mais flexível, ao custo de uma chamada por pergunta.
- A etapa de geração da resposta tem testes com cliente falso, mas não foi avaliada em qualidade.

## Como rodar

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest          # 64 testes offline
.venv/Scripts/python -m menusearch.evaluate
```

O primeiro `evaluate` baixa o modelo de embeddings (cerca de 220 MB). Para usar pgvector: `docker compose up -d`, exporte `DATABASE_URL` (o valor está em `.env.example`; o código não lê o `.env` sozinho), rode `python -m menusearch.ingest` e depois `python -m menusearch.evaluate --pg`. A API sobe com `uvicorn menusearch.api:build_default_app --factory`; `/ask` precisa de `ANTHROPIC_API_KEY`.

## Decisões e trade-offs

- **Embeddings locais em vez de API.** A Anthropic não tem endpoint de embeddings, e um modelo multilíngue local mantém a avaliação gratuita e reproduzível. O custo é a qualidade: um modelo maior (`multilingual-e5-large`, 2,2 GB) deve melhorar a busca semântica.
- **Filtros por regras.** Preço, tempo e categoria cobrem as perguntas do plano e são fáceis de testar. Cada pergunta traz o filtro esperado, e um teste confere que o parser o produz.
- **Rótulos protegidos por teste.** Como os relevantes foram marcados à mão, um teste confere que todo prato rotulado existe e respeita as restrições da própria pergunta.
- **Dois backends com a mesma lógica.** O `MemoryStore` e o `PgVectorStore` implementam a mesma interface; os testes e a avaliação rodam sem banco.
- **Um prato por trecho.** Cardápios são curtos, e um trecho por prato mantém o resultado alinhado com o que o cliente pede.

## Próximos passos

- Medir o `PgVectorStore` com um cardápio maior, onde o índice HNSW passa a ser usado de fato.
- Busca híbrida (vetor + texto) para as perguntas semânticas que falharam.
- Comparar com um modelo de embeddings maior.
- Avaliar a qualidade da resposta gerada, por exemplo a taxa de citações válidas.

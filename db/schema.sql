-- A dimensão (384) é a do modelo paraphrase-multilingual-MiniLM-L12-v2. Outro modelo exige outra dimensão.
create table if not exists dishes (
  id text primary key,
  restaurant text not null,
  name text not null,
  description text not null,
  category text not null,
  price_cents integer not null check (price_cents > 0),
  prep_minutes integer not null check (prep_minutes >= 0),
  vegetarian boolean not null,
  embedding vector(384) not null
);

create index if not exists dishes_embedding_idx on dishes using hnsw (embedding vector_cosine_ops);
create index if not exists dishes_filters_idx on dishes (category, price_cents, prep_minutes);

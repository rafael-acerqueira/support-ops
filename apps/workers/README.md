# Workers - Celery + Redis

Processamento assíncrono para tarefas de longa duração: ingestão de documentos, chunking, geração de embeddings, etc.

## Stack

- **Task Queue**: Celery
- **Broker**: Redis
- **Python**: 3.11+
- **Document Processing**: pypdf, python-docx, python-pptx, markdown, BeautifulSoup
- **LLM Integration**: OpenAI, LangChain

## Arquitetura

```
src/
  ├── celery_app.py              # Configuração Celery
  ├── config.py                  # Settings
  ├── tasks/                     # Tarefas (adapters async in)
  │   ├── ingest_document.py     # Recebe arquivo e metadados
  │   ├── process_chunks.py      # Chunking
  │   ├── generate_embeddings.py # Embeddings
  │   ├── reindex_vectors.py     # Reindexing
  │   └── cleanup.py             # Limpeza
  ├── processors/                # Lógica de processamento
  │   ├── document_parser.py     # Extração de texto (PDF, MD, HTML)
  │   ├── chunker.py             # Estratégias de chunking
  │   └── embedder.py            # Geração de embeddings
  ├── adapters/                  # Adapters de infra
  │   ├── storage/               # Ler arquivos (S3/MinIO)
  │   ├── vector_db/             # Escrever embeddings
  │   ├── db/                    # Atualizar BD
  │   └── llm/                   # Chamar embeddings API
  ├── db/                        # Conexão e models
  │   ├── session.py
  │   └── models.py
  └── tests/
      ├── test_tasks/
      └── conftest.py
```

## Desenvolvimento

Estado atual: o worker sobe conectado ao Redis, mas ainda não registra tasks de negócio. As tasks e workflows descritos abaixo são planejados para o MVP.

```bash
# Instalar dependências
uv sync

# Rodar workers localmente
uv run celery -A src.celery_app worker --loglevel=info

# Rodar via monorepo
npm run dev:workers

# Ver tarefas na fila
uv run celery -A src.celery_app inspect active

# Purgar fila
uv run celery -A src.celery_app purge

# Flower (monitoramento Web)
uv run celery -A src.celery_app flower --port=5555

# Tests
uv run pytest
```

## Tasks planejadas (MVP)

### Ingestão

- `ingest_document_task` - Recebe arquivo + metadados, salva, enfileira processamento
- `process_document_task` - Faz download, parse, chunking, cria registros BD

### Processamento

- `generate_embeddings_task` - Gera embeddings para chunks
- `reindex_document_version_task` - Reindexação completa

### Limpeza & Manutenção

- `cleanup_old_embeddings_task` - Remove embeddings antigos
- `vacuum_vectors_task` - Otimização pgvector

## Workflow típico

1. Admin faz upload via web → POST /documents
2. Controller (api) salva arquivo em storage + cria DocumentVersion
3. Controller enfileira `ingest_document_task`
4. Worker recebe task, faz parsing, chunking
5. Worker enfileira `generate_embeddings_task`
6. Worker recebe task, chama OpenAI, salva embeddings
7. Worker atualiza status em BD para "Indexado"
8. Frontend (via polling) vê status mudou

## Variáveis de Ambiente

Ver `.env.example` na raiz.

Principais:

- `REDIS_*` - Broker. O worker carrega o `.env` da raiz do repositório.
- `DB_*` - Banco para persistência
- `MINIO_*` / `AWS_*` - Storage
- `OPENAI_API_KEY` - Embeddings

## Observabilidade

Workers emitem logs estruturados (JSON) para facilitar rastreamento.

Integração opcional com Langsmith/Langfuse para observabilidade detalhada.

# SupportOps Quickstart

## Requirements

- Docker & Docker Compose plugin (`docker compose`)
- Node.js 22.13+
- Python 3.11+
- pnpm
- uv

## Setup

```bash
cd supportops
cp .env.example .env
chmod +x scripts/setup.sh
bash scripts/setup.sh
```

Run migrations after setup:

```bash
npm run db:migrate
```

## Run Locally

```bash
npm run dev
```

This starts the frontend, API, and workers in parallel. The script also ensures Docker
infrastructure is running.

Local URLs:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- pgAdmin: http://localhost:5050
- MinIO console: http://localhost:9001

Run services separately when debugging:

```bash
npm run docker:up
npm run dev:web
npm run dev:api
npm run dev:workers
```

## Manual MVP Test Flow

Use this flow to validate the current Phase 1 MVP locally.

### 1. Prepare Infrastructure

```bash
npm run docker:up
npm run db:migrate
npm run dev
```

Keep the terminal open. The API and workers must both be running for document processing.

### 2. Upload a Knowledge Document

Open http://localhost:3000.

Create a Markdown or text file with content related to support policy. Example:

```markdown
# Billing Refund Policy

Duplicate invoice charges must be validated before promising a refund.

Enterprise customers may require SLA review when billing incidents affect access or payment
operations.

Support agents should cite the billing playbook and confirm whether the duplicate charge was
captured, settled, or already reversed.
```

Upload it in Knowledge Base:

- Document type: `Internal policy` or `Playbook`
- Product area: `Billing`
- Tags: `enterprise, refund, invoice, billing`

Expected result:

- The document appears in the table.
- Status moves from `Uploaded` or `Processing` to `Indexed`.
- The detail panel shows `Ready for retrieval`.
- `Chunks` is greater than `0`.

### 3. Verify Chunks and Embeddings

Open Postgres:

```bash
docker compose exec postgres psql -U supportops -d supportops
```

Run:

```sql
select name, status, chunk_count, failure_reason
from documents
order by created_at desc;

select
  document_id,
  chunk_index,
  embedding is not null as has_embedding,
  embedding_provider,
  embedding_model
from document_chunks
order by document_id, chunk_index;
```

Expected result:

- `documents.status` is `indexed`.
- `failure_reason` is `null`.
- `chunk_count` is greater than `0`.
- `has_embedding` is `true`.
- `embedding_provider` matches the configured provider.
- `embedding_model` matches the configured model.

### 4. Create a Ticket

Open http://localhost:3000/tickets.

Create this ticket:

```text
Ticket ID: TCK-2001
Customer: Globex Corp
Plan: Enterprise
Category: Billing
Priority: High
Subject: Duplicate invoice charge refund request

Description:
The customer reports being charged twice for the same monthly invoice. They are asking whether
the duplicate charge can be refunded immediately and if the issue affects their Enterprise SLA.
```

Expected result:

- The ticket appears in the queue.
- Selecting it opens the detail panel.
- The detail panel shows `Ready for response drafting`.

### 5. Generate a Suggested Response

Click `Suggest response`.

Expected result:

- A suggested response appears.
- The Sources section shows retrieved document chunks.
- Each source shows document name, chunk number, excerpt, and match score.
- If no source is found, the UI shows a low-confidence/no-source warning instead of a technical
  error.

### 6. Review the Suggestion

Click `Approve` or `Reject`.

Expected result:

- The suggestion status changes to `Approved` or `Rejected`.
- The review panel shows contextual feedback.
- The latest suggestion remains visible.
- Older suggestions appear in `Suggestion history` after more than one response is generated.

### 7. Verify Suggested Responses in the Database

```sql
select id, ticket_id, status, sources
from suggested_responses
order by created_at desc
limit 5;
```

Expected result:

- `status` is `draft`, `approved`, or `rejected`.
- `sources` contains source metadata when matching chunks were found.

## Common Commands

```bash
npm run docker:up      # Start infrastructure
npm run docker:down    # Stop infrastructure
npm run docker:logs    # View infrastructure logs
npm run db:migrate     # Apply database migrations
npm run db:current     # Show current migration
npm run dev            # Start web, API, and workers
npm run dev:web        # Frontend only
npm run dev:api        # API only
npm run dev:workers    # Workers only
npm run test           # Run test suites through Turbo
```

## Troubleshooting

### Postgres Table Does Not Exist

Run migrations:

```bash
npm run db:migrate
```

### Document Stays Uploaded

Check that workers are running:

```bash
npm run dev:workers
```

Then click `Reprocess` in the document detail.

### Chunks Have No Embeddings

Reprocess documents created before embedding support was added:

```text
Knowledge Base -> select document -> Reprocess
```

### Need a Fresh Local Database

This removes local database data:

```bash
docker compose down -v
npm run docker:up
npm run db:migrate
```

## Notes

The default local setup uses deterministic embeddings and deterministic response drafts. It validates
the full RAG workflow locally without requiring external AI API keys.

To use OpenAI embeddings, set `EMBEDDING_PROVIDER=openai`, define `OPENAI_API_KEY`, and keep or update
`OPENAI_EMBEDDING_MODEL`.

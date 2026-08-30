# ai-template-document

Document extraction template derived from frozen `ai-starter` at `7f91e3f394536164ffefcf320b4356ad24092702`.

`document-intelligence-mvp` is the primary reference for file validation and text extraction. This template does not copy its workers, tenants, Qdrant, or Docling stack.

One vertical slice:

upload or paste text → validate file → extract text → normalize → `ai-core` structured extraction → drop ungrounded fields → review decision → persist metadata → show the result.

Supported files: `.txt` and `.pdf`. Original files are not stored. Raw extracted text is not persisted.

## 1. Stack

Next.js, FastAPI, Pydantic, PostgreSQL, SQLAlchemy, Alembic, OpenAI through `ai-core`, optional Langfuse, `agent-eval-harness`, Docker, GitHub Actions, Railway-ready.

## 2. Local API

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set `OPENAI_API_KEY`. Default compose Postgres is on host port **5434**.

```bash
docker compose up -d postgres
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## 3. Local web

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`. The form calls `POST /api/v1/documents/extract`.

## 4. API

- `GET /health`
- `GET /ready`
- `POST /api/v1/documents/extract` — JSON `{"text":"..."}` or multipart `file`

Errors: `invalid_file` 422, `unsupported_file` 415, `invalid_request` 422, `provider_failed` 502, `openai_not_configured` 503, `database_unavailable` 503. Error bodies do not echo file contents.

## 5. Review

`requires_review` is computed on the server, not trusted from the model:

- confidence below `REVIEW_CONFIDENCE_THRESHOLD` (default 0.75)
- `document_type` is not `invoice` or `business_form`
- `reference_number`, `date`, `amount`, `currency`, or `company_name` is missing
- any extracted value was dropped because it was not in the source text

## 6. Tests

```bash
cd apps/api
ruff check .
ruff format --check .
pytest
```

Normal tests mock OpenAI.

## 7. Evals

From the repo root, with `apps/api` installed and `PYTHONPATH=apps/api`:

```bash
pip install "agent-eval-harness @ git+https://github.com/siinanXD/agent-eval-harness.git@4b2cb9b7839da8970bdbf271769cde41d7258b60"
agent-eval-harness evals/suites/extract.json \
  --target evals.target:build_target \
  --baseline extract-baseline \
  --root .evals
```

Live OpenAI evals are opt-in only:

```bash
RUN_OPENAI_EVAL=1 OPENAI_API_KEY=... agent-eval-harness evals/suites/extract.json \
  --target evals.live_target:build_target \
  --providers openai \
  --no-gate
```

## 8. Architecture

See `docs/ARCHITECTURE.md`.

- `ai-core` owns OpenAI completions, structured output, retry, wrapping, redaction, cost, and optional Langfuse.
- `pypdf` is the only extra parser. Filenames are never trusted.
- `agent-eval-harness` is the only eval runner.

## 9. Railway

See `docs/RAILWAY.md`. Dockerfiles exist for `web` and `api`. Both listen on Railway's `$PORT`. This repository does not deploy.

Pinned runtime libraries:

- `ai-core` @ `9fb7f568640346d7ba31eeb6e4d366f6a0e022f1`
- `agent-eval-harness` @ `4b2cb9b7839da8970bdbf271769cde41d7258b60`

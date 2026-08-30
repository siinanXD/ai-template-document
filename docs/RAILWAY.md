# Railway preparation

Do not deploy from this repository automatically.

`POST /api/v1/documents/extract` is unauthenticated and spends the OpenAI key. Do not expose the API on a public URL without a gateway or other access control.

Create three Railway services from the same GitHub repo:

| Service | Source | Root Directory | Notes |
| --- | --- | --- | --- |
| postgres | Railway PostgreSQL plugin | — | No `vector` extension required. Railway's `DATABASE_URL` (`postgresql://…`) is rewritten to `postgresql+psycopg://` at startup |
| api | `Dockerfile` | `apps/api` | Installs `git` so `ai-core` can be fetched. Listens on `$PORT` (fallback 8000). Runs Alembic then uvicorn. Two replicas can race on the Alembic lock. |
| web | `Dockerfile` | `apps/web` | Listens on `$PORT` (fallback 3000) at `0.0.0.0`. Set `NEXT_PUBLIC_API_URL` to the public API URL **at build time** |

API environment:

- `DATABASE_URL` (Railway Postgres plugin value is fine)
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (optional, default `gpt-4o-mini`)
- `CORS_ORIGINS` (the web origin)
- `MAX_UPLOAD_BYTES` (optional, default 1048576)
- `MAX_EXTRACT_CHARS` (optional, default 20000)
- `REVIEW_CONFIDENCE_THRESHOLD` (optional, default 0.75)
- optional Langfuse keys
- optional `OPENAI_INPUT_USD_PER_MTOK` / `OPENAI_OUTPUT_USD_PER_MTOK`

Web environment:

- `NEXT_PUBLIC_API_URL`

Migration step: `alembic upgrade head` (the API image runs this on boot).

File-size limit is enforced in the API, not in Railway. Raise `MAX_UPLOAD_BYTES` if the demo needs larger PDFs. Original files are not written to disk or object storage.

No Redis, workers, pgvector, or extra datastores. `ai-core` is public.

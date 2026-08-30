# Architecture

Derived from frozen `ai-starter` at `7f91e3f394536164ffefcf320b4356ad24092702`.

File-handling ideas (magic bytes, extension vs declared MIME, safe filename) come from `document-intelligence-mvp`. That product's workers, tenants, Qdrant, Docling, and stored originals are not used here.

One vertical slice:

```
Next.js file picker or pasted text
  → FastAPI POST /api/v1/documents/extract
  → validate size / type / magic
  → extract text (.txt or pypdf)
  → normalize
  → wrap_untrusted
  → ai-core structured OpenAI call
  → drop values that do not appear in the source
  → compute requires_review
  → persist document_runs metadata only
  → show fields + review flag
```

`ai-core` owns provider, retry, structured output, redaction, and optional Langfuse generation traces.

PostgreSQL stores `document_runs`: file hash, extracted fields, confidence, review flag, model, latency, tokens, cost. It does not store original bytes or extracted text.

`agent-eval-harness` owns scoring and the regression gate. The deterministic target uses a fake provider. Stored run files under `.evals/` contain the API JSON — do not commit live runs of real customer documents.

"use client";

import { FormEvent, useState } from "react";

import { extractDocument, type ExtractResult } from "@/lib/api";

function display(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return String(value);
}

export function ExtractPage() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onExtract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await extractDocument({ file: file ?? undefined, text }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extract failed");
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = Boolean(file) || text.trim().length > 0;

  return (
    <main className="page">
      <h1>Document extract</h1>
      <p className="lede">
        Upload a .txt or .pdf invoice, or paste text. The API extracts structured
        fields, drops values that are not in the source, and flags review.
      </p>

      <form onSubmit={onExtract}>
        <label htmlFor="file">File</label>
        <input
          id="file"
          name="file"
          type="file"
          accept=".txt,.pdf,text/plain,application/pdf"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <label htmlFor="text">Or paste text</label>
        <textarea
          id="text"
          name="text"
          rows={8}
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={20000}
        />
        <button type="submit" disabled={loading || !canSubmit}>
          {loading ? "Extracting…" : "Extract"}
        </button>
      </form>

      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}

      {result ? (
        <article className="card">
          {result.requires_review ? (
            <p className="warn">Review needed. One or more fields are missing, low-confidence, or ungrounded.</p>
          ) : (
            <p className="note">No review flag. All required business fields are present.</p>
          )}
          <p>
            <strong>Document type</strong>
            {display(result.document_type)}
          </p>
          <p>
            <strong>Reference</strong>
            {display(result.reference_number)}
          </p>
          <p>
            <strong>Date</strong>
            {display(result.date)}
          </p>
          <p>
            <strong>Amount</strong>
            {result.amount == null ? "—" : `${result.amount} ${result.currency ?? ""}`.trim()}
          </p>
          <p>
            <strong>Company</strong>
            {display(result.company_name)}
          </p>
          <p>
            <strong>Confidence</strong>
            {result.confidence}
          </p>
          <p>
            <strong>Requires review</strong>
            {result.requires_review ? "yes" : "no"}
          </p>
          <dl className="meta">
            <div>
              <dt>Model</dt>
              <dd>{result.model}</dd>
            </div>
            <div>
              <dt>Latency</dt>
              <dd>{result.latency_ms} ms</dd>
            </div>
            <div>
              <dt>Generation</dt>
              <dd>{result.generation_latency_ms} ms</dd>
            </div>
            <div>
              <dt>Tokens</dt>
              <dd>
                {result.input_tokens ?? "—"} in / {result.output_tokens ?? "—"} out
              </dd>
            </div>
            <div>
              <dt>Estimated cost</dt>
              <dd>
                {result.estimated_cost_usd == null
                  ? "unknown"
                  : `$${result.estimated_cost_usd.toFixed(6)}`}
              </dd>
            </div>
          </dl>
        </article>
      ) : null}
    </main>
  );
}

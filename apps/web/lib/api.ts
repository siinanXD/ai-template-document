export type ExtractResult = {
  id: string;
  document_type: string | null;
  reference_number: string | null;
  date: string | null;
  amount: number | null;
  currency: string | null;
  company_name: string | null;
  confidence: number;
  requires_review: boolean;
  model: string;
  latency_ms: number;
  generation_latency_ms: number;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  created_at: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function readError(response: Response): Promise<string> {
  let detail = `Request failed (${response.status})`;
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      detail = payload.detail;
    }
  } catch {
    // Keep the status message when the body is not JSON.
  }
  return detail;
}

export async function extractDocument(input: { text?: string; file?: File }): Promise<ExtractResult> {
  let response: Response;
  if (input.file) {
    const body = new FormData();
    body.append("file", input.file);
    response = await fetch(`${API_URL}/api/v1/documents/extract`, {
      method: "POST",
      body,
    });
  } else {
    response = await fetch(`${API_URL}/api/v1/documents/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: input.text ?? "" }),
    });
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as ExtractResult;
}

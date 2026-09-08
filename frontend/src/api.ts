import type { TaxSummary } from "./types";
import { getSessionId } from "./session";

export async function calculateTax(options: {
  files: File[];
  taxYear: number;
  priorLosses: number;
  accountCurrency: string;
}): Promise<TaxSummary> {
  const body = new FormData();
  for (const file of options.files) {
    body.append("files", file);
  }
  body.append("tax_year", String(options.taxYear));
  body.append("prior_losses_pln", String(options.priorLosses || 0));
  body.append("account_currency", options.accountCurrency);
  body.append("session_id", getSessionId());
  const response = await fetch("/api/calculate", { method: "POST", body });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail || "Calculation failed");
  }
  return response.json();
}

export async function fetchSample(name: string): Promise<File> {
  const response = await fetch(`/api/samples/${name}`);
  if (!response.ok) {
    throw new Error(`Could not download sample ${name}`);
  }
  const blob = await response.blob();
  return new File([blob], name, { type: blob.type || "text/csv" });
}

export type ChatTrace = { agent: string; tool: string; ok?: boolean };

export async function sendChat(options: {
  messages: { role: "user" | "assistant"; content: string }[];
  apiKey: string;
  language: "pl" | "en";
}): Promise<{ answer: string; traces: ChatTrace[]; has_report: boolean }> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: getSessionId(),
      messages: options.messages,
      api_key: options.apiKey || null,
      language: options.language,
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail || "Chat failed");
  }
  return response.json();
}

export async function fetchHealth(): Promise<{ openai_configured: boolean; nbp: string }> {
  const response = await fetch("/api/health");
  return response.json();
}

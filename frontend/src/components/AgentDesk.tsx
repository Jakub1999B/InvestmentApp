import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bot, KeyRound, Loader2, Send, Sparkles } from "lucide-react";
import { fetchHealth, sendChat, type ChatTrace } from "../api";
import { getStoredApiKey, setStoredApiKey } from "../session";

type Msg = { role: "user" | "assistant"; content: string; traces?: ChatTrace[] };

export default function AgentDesk({ lang, hasReport }: { lang: "pl" | "en"; hasReport: boolean }) {
  const t = lang === "pl" ? pl : en;
  const [apiKey, setApiKey] = useState(getStoredApiKey);
  const [envReady, setEnvReady] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchHealth()
      .then((health) => setEnvReady(health.openai_configured))
      .catch(() => setEnvReady(false));
  }, []);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) {
      return;
    }
    const next: Msg[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const result = await sendChat({
        messages: next.map(({ role, content }) => ({ role, content })),
        apiKey,
        language: lang,
      });
      setMessages([...next, { role: "assistant", content: result.answer, traces: result.traces }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="flex min-h-[520px] flex-col overflow-hidden rounded-[32px] border border-[#d7cbb6] bg-[#fffdf8]">
      <header className="border-b border-[#efe6d4] px-5 py-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[#c7922c]" />
          <h2 className="font-serif text-2xl">{t.title}</h2>
        </div>
        <p className="mt-1 text-sm text-[#5c6b66]">{t.sub}</p>
        <label className="mt-3 flex items-center gap-2 rounded-2xl bg-[#f4efe4] px-3 py-2 text-sm">
          <KeyRound className="h-4 w-4 shrink-0 text-[#2f6f5e]" />
          <input
            type="password"
            autoComplete="off"
            placeholder={envReady ? t.keyOptional : t.keyRequired}
            value={apiKey}
            onChange={(event) => {
              setApiKey(event.target.value);
              setStoredApiKey(event.target.value);
            }}
            className="w-full bg-transparent outline-none"
          />
        </label>
        <p className="mt-2 text-xs text-[#5c6b66]">{hasReport ? t.reportOn : t.reportOff}</p>
      </header>

      <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <div className="space-y-2">
            {t.prompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="block w-full rounded-2xl bg-[#f4efe4] px-3 py-2 text-left text-sm text-[#12201c]"
                onClick={() => setInput(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        )}
        {messages.map((msg, index) => (
          <div key={`${msg.role}-${index}`} className={msg.role === "user" ? "text-right" : ""}>
            <div
              className={`inline-block max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-6 ${
                msg.role === "user" ? "bg-[#12201c] text-[#f4efe4]" : "bg-[#f4efe4] text-[#12201c]"
              }`}
            >
              {msg.role === "assistant" && <Bot className="mb-1 h-3.5 w-3.5" />}
              <span className="whitespace-pre-wrap">{msg.content}</span>
            </div>
            {msg.traces && msg.traces.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {msg.traces.map((trace, i) => (
                  <span key={`${trace.agent}-${trace.tool}-${i}`} className="rounded-full bg-white px-2 py-0.5 text-[10px] uppercase tracking-wide text-[#5c6b66]">
                    {trace.agent} · {trace.tool}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && (
          <p className="flex items-center gap-2 text-sm text-[#5c6b66]">
            <Loader2 className="h-4 w-4 animate-spin" /> {t.thinking}
          </p>
        )}
      </div>

      {error && <p className="px-5 pb-2 text-sm text-[#c45c4a]">{error}</p>}

      <form onSubmit={onSubmit} className="flex gap-2 border-t border-[#efe6d4] p-3">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={t.placeholder}
          className="flex-1 rounded-full bg-[#f4efe4] px-4 py-2 text-sm outline-none"
        />
        <button
          type="submit"
          disabled={busy}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[#12201c] text-[#b7e4c7] disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </aside>
  );
}

const pl = {
  title: "Biurko agentów",
    sub: "FX pobiera żywe kursy NBP. Agent podatkowy czyta FIFO / PIT-38. Klucz użytkownika Cursor (crsr_) wystarczy — SSH do repozytorium nie.",
  keyRequired: "Klucz Cursor (crsr_) lub OpenAI",
  keyOptional: "Klucz API (albo backend/.env)",
  reportOn: "Raport z tej sesji jest podpięty do agenta podatkowego.",
  reportOff: "Najpierw policz CSV — albo pytaj o kursy NBP od razu.",
  placeholder: "Np. kurs USD z 12.03.2025 albo skąd wzięło się 19%…",
  thinking: "Agenci odpytują NBP / raport…",
  failed: "Agent nie odpowiedział.",
  prompts: [
    "Jaki był kurs USD NBP dzień przed 14.02.2025?",
    "Pokaż całą tabelę A z ostatniego dnia publikacji.",
    "Skąd w tym raporcie biorą się pola 22 i 23 PIT-38?",
  ],
};

const en = {
  title: "Agent desk",
  sub: "The FX agent fetches live NBP rates. The tax agent reads FIFO / PIT-38. A Cursor user key (crsr_) is enough — a repo SSH key is not.",
  keyRequired: "Cursor user key (crsr_) or OpenAI",
  keyOptional: "API key (or backend/.env)",
  reportOn: "This session’s report is attached to the tax agent.",
  reportOff: "Calculate a CSV first — or ask for NBP rates right away.",
  placeholder: "e.g. USD NBP rate before 14 Feb 2025, or explain field 22…",
  thinking: "Agents are calling NBP / the report…",
  failed: "The agent did not answer.",
  prompts: [
    "What was the NBP USD rate on the day before 14 Feb 2025?",
    "Show the latest published Table A.",
    "Where do PIT-38 fields 22 and 23 come from in this report?",
  ],
};

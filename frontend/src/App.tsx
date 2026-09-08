import { useMemo, useState, type DragEvent, type FormEvent } from "react";
import { Calculator, FileUp, Languages, Leaf, Loader2 } from "lucide-react";
import { calculateTax, fetchSample } from "./api";
import AgentDesk from "./components/AgentDesk";
import Report from "./components/Report";
import { brokerLabel } from "./format";
import type { TaxSummary } from "./types";

const SAMPLE_FILES = ["trading212_sample.csv", "xtb_closed_positions.csv", "xtb_cash_operations.csv", "generic_sample.csv"];

export default function App() {
  const [lang, setLang] = useState<"pl" | "en">("pl");
  const [files, setFiles] = useState<File[]>([]);
  const [taxYear, setTaxYear] = useState(2025);
  const [priorLosses, setPriorLosses] = useState("0");
  const [accountCurrency, setAccountCurrency] = useState("PLN");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<TaxSummary | null>(null);
  const years = useMemo(() => Array.from({ length: 8 }, (_, i) => 2026 - i), []);
  const t = lang === "pl" ? pl : en;

  function addFiles(list: FileList | File[]) {
    const next = Array.from(list).filter((file) => /\.(csv|xlsx|xls)$/i.test(file.name));
    setFiles((current) => {
      const names = new Set(current.map((file) => file.name));
      return [...current, ...next.filter((file) => !names.has(file.name))];
    });
    setError(null);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    if (event.dataTransfer.files.length) {
      addFiles(event.dataTransfer.files);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!files.length) {
      setError(t.needFile);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await calculateTax({
        files,
        taxYear,
        priorLosses: Number(priorLosses.replace(",", ".")) || 0,
        accountCurrency,
      });
      setReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failed);
    } finally {
      setBusy(false);
    }
  }

  async function loadSamples() {
    setBusy(true);
    setError(null);
    try {
      const downloaded = await Promise.all(SAMPLE_FILES.map((name) => fetchSample(name)));
      setFiles(downloaded);
      const result = await calculateTax({
        files: downloaded,
        taxYear: 2025,
        priorLosses: 0,
        accountCurrency: "PLN",
      });
      setTaxYear(2025);
      setReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.failed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="paper-grid min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:py-12">
        <header className="mb-10 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-[#12201c] px-3 py-1 text-xs uppercase tracking-[0.2em] text-[#b7e4c7]">
              <Leaf className="h-3.5 w-3.5" /> Belka
            </div>
            <h1 className="max-w-2xl font-serif text-4xl leading-tight sm:text-5xl">{t.headline}</h1>
            <p className="mt-3 max-w-xl text-[#5c6b66]">{t.sub}</p>
          </div>
          <button
            type="button"
            onClick={() => setLang((current) => (current === "pl" ? "en" : "pl"))}
            className="inline-flex items-center gap-2 rounded-full border border-[#d7cbb6] bg-white/80 px-4 py-2 text-sm"
          >
            <Languages className="h-4 w-4" /> {lang === "pl" ? "English" : "Polski"}
          </button>
        </header>

        <form onSubmit={onSubmit} className="mb-10 grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
          <label
            onDragOver={(event) => event.preventDefault()}
            onDrop={onDrop}
            className="flex min-h-[280px] cursor-pointer flex-col justify-between rounded-[32px] border border-dashed border-[#2f6f5e] bg-white/70 p-6"
          >
            <div>
              <FileUp className="mb-4 h-8 w-8 text-[#2f6f5e]" />
              <h2 className="font-serif text-2xl">{t.drop}</h2>
              <p className="mt-2 text-sm text-[#5c6b66]">{t.dropHint}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {["Trading 212", "XTB", "CSV"].map((name) => (
                <span key={name} className="stamp rounded-md px-2 py-1 text-[10px] text-[#2f6f5e]">
                  {name}
                </span>
              ))}
            </div>
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              multiple
              className="hidden"
              onChange={(event) => event.target.files && addFiles(event.target.files)}
            />
            {files.length > 0 && (
              <ul className="mt-4 space-y-1 text-sm">
                {files.map((file) => (
                  <li key={file.name} className="flex justify-between gap-3">
                    <span>{file.name}</span>
                    <button
                      type="button"
                      className="text-[#c45c4a]"
                      onClick={(event) => {
                        event.preventDefault();
                        setFiles((current) => current.filter((item) => item.name !== file.name));
                      }}
                    >
                      {t.remove}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </label>

          <div className="rounded-[32px] bg-[#12201c] p-6 text-[#f4efe4]">
            <label className="block text-xs uppercase tracking-[0.16em] text-[#b7e4c7]">{t.year}</label>
            <select
              value={taxYear}
              onChange={(event) => setTaxYear(Number(event.target.value))}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-3 py-3"
            >
              {years.map((year) => (
                <option key={year} value={year} className="text-black">
                  {year}
                </option>
              ))}
            </select>
            <label className="mt-5 block text-xs uppercase tracking-[0.16em] text-[#b7e4c7]">{t.losses}</label>
            <input
              value={priorLosses}
              onChange={(event) => setPriorLosses(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-3 py-3"
              inputMode="decimal"
            />
            <label className="mt-5 block text-xs uppercase tracking-[0.16em] text-[#b7e4c7]">{t.accountCcy}</label>
            <input
              value={accountCurrency}
              onChange={(event) => setAccountCurrency(event.target.value.toUpperCase())}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-3 py-3"
              maxLength={3}
            />
            <div className="mt-6 flex flex-col gap-3">
              <button
                type="submit"
                disabled={busy}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#b7e4c7] px-4 py-3 font-medium text-[#12201c] disabled:opacity-60"
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4" />}
                {t.calculate}
              </button>
              <button
                type="button"
                onClick={loadSamples}
                disabled={busy}
                className="rounded-full border border-white/20 px-4 py-3 text-sm"
              >
                {t.sample}
              </button>
            </div>
          </div>
        </form>

        {error && <p className="mb-6 rounded-2xl bg-[#f8e4df] px-4 py-3 text-sm text-[#c45c4a]">{error}</p>}

        <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <div>
            {report ? (
              <Report report={report} lang={lang} />
            ) : (
              <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-1">
                {t.steps.map((step) => (
                  <article key={step.title} className="rounded-[24px] bg-white/70 p-5">
                    <h3 className="font-serif text-xl">{step.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-[#5c6b66]">{step.body}</p>
                  </article>
                ))}
              </section>
            )}
          </div>
          <AgentDesk lang={lang} hasReport={Boolean(report)} />
        </div>

        {report && (
          <p className="mt-6 text-center text-xs text-[#5c6b66]">
            {report.imported_files.map((name) => brokerLabel(name.replace(/_sample.*$/, "").split(".")[0] || name)).join(" · ")} ·{" "}
            {report.transaction_count} {t.rows}
          </p>
        )}
      </div>
    </div>
  );
}

const pl = {
  headline: "Z eksportu brokera do PIT-38.",
  sub: "Wgraj historię z Trading 212, XTB albo uniwersalny CSV. Belka policzy FIFO, przeliczy waluty żywym kursem NBP T-1 (bez cache) i przygotuje kwoty do PIT-38 / PIT-ZG.",
  drop: "Upuść pliki CSV lub XLSX",
  dropHint: "Najlepiej pełna historia, nie tylko rok podatkowy — FIFO potrzebuje starych zakupów.",
  remove: "usuń",
  year: "Rok podatkowy",
  losses: "Straty z lat ubiegłych (PLN)",
  accountCcy: "Waluta rachunku XTB",
  calculate: "Policz podatek",
  sample: "Pokaż na danych przykładowych",
  needFile: "Dodaj przynajmniej jeden plik.",
  failed: "Nie udało się policzyć podatku.",
  rows: "wierszy",
  steps: [
    {
      title: "1. FIFO per konto",
      body: "Sprzedaż rozliczana najstarszym zakupem, osobno dla każdego brokera. Prowizje wchodzą w koszt.",
    },
    {
      title: "2. Żywy NBP z dnia T-1",
      body: "Każdy buy, sell, dywidenda i WHT przeliczane średnim kursem tabeli A/B z dnia poprzedzającego transakcję. Kursy zawsze z api.nbp.pl.",
    },
    {
      title: "3. PIT-38 i PIT/ZG",
      body: "19% podatek Belki, zaliczenie podatku u źródła i rozbicie przychodów zagranicznych według kraju ISIN.",
    },
  ],
};

const en = {
  headline: "From a broker export to PIT-38.",
  sub: "Upload Trading 212, XTB or a generic CSV. Belka applies FIFO, converts every leg at the live NBP T-1 rate (no cache), and maps totals onto PIT-38 / PIT-ZG.",
  drop: "Drop CSV or XLSX files",
  dropHint: "Prefer full history, not just the tax year — FIFO needs the original purchases.",
  remove: "remove",
  year: "Tax year",
  losses: "Prior-year losses (PLN)",
  accountCcy: "XTB account currency",
  calculate: "Calculate tax",
  sample: "Run the sample files",
  needFile: "Add at least one file.",
  failed: "Tax calculation failed.",
  rows: "rows",
  steps: [
    {
      title: "1. FIFO per account",
      body: "Each sale is matched to the oldest purchase, separately per broker. Fees increase the cost basis.",
    },
    {
      title: "2. Live NBP T-1 FX",
      body: "Every buy, sell, dividend and withholding amount is converted at Table A/B from the previous business day, fetched live from api.nbp.pl.",
    },
    {
      title: "3. PIT-38 and PIT/ZG",
      body: "19% Belka tax, foreign tax credit, and a per-country split of foreign-source income.",
    },
  ],
};

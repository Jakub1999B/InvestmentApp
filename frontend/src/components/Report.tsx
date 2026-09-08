import { useMemo, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  BookOpen,
  FileSpreadsheet,
  Globe2,
  Landmark,
  Layers3,
  PiggyBank,
  Receipt,
} from "lucide-react";
import type { TaxSummary } from "../types";
import { brokerLabel, pln, qty } from "../format";

type Tab = "fifo" | "div" | "lots" | "zg" | "notes";

const copy = {
  pl: {
    due: "Do zapłaty",
    year: "Rok podatkowy",
    brokers: "Brokerzy",
    trades: "Transakcje",
    revenue: "Przychód ze zbycia",
    costs: "Koszty uzyskania",
    income: "Dochód",
    loss: "Strata",
    cgTax: "Podatek Belki 19%",
    dividends: "Dywidendy brutto",
    credit: "Podatek u źródła",
    interest: "Odsetki",
    paper: "PIT-38 — pola pomocnicze (wariant 18)",
    tabs: {
      fifo: "FIFO / sprzedaże",
      div: "Dywidendy i odsetki",
      lots: "Otwarte loty",
      zg: "PIT/ZG",
      notes: "Uwagi",
    },
    fifoHint: "Każda sprzedaż rozliczona najstarszym zakupem, w PLN po kursie NBP z dnia poprzedzającego.",
    emptyFifo: "Brak sprzedaży w wybranym roku.",
    emptyDiv: "Brak dywidend i odsetek w tym roku.",
    emptyLots: "Brak otwartych pozycji po FIFO.",
    emptyZg: "Brak przychodów zagranicznych do PIT/ZG (albo tylko Polska).",
    gain: "Zysk",
    country: "Kraj",
    disclaimerTitle: "To nie jest porada podatkowa",
  },
  en: {
    due: "Tax due",
    year: "Tax year",
    brokers: "Brokers",
    trades: "Transactions",
    revenue: "Disposal proceeds",
    costs: "Allowable costs",
    income: "Income",
    loss: "Loss",
    cgTax: "19% Belka tax",
    dividends: "Gross dividends",
    credit: "Withholding tax",
    interest: "Interest",
    paper: "PIT-38 — helper fields (variant 18)",
    tabs: {
      fifo: "FIFO / sales",
      div: "Dividends & interest",
      lots: "Open lots",
      zg: "PIT/ZG",
      notes: "Notes",
    },
    fifoHint: "Each sale is matched to the oldest purchase, converted to PLN at the NBP rate from the previous business day.",
    emptyFifo: "No disposals in the selected year.",
    emptyDiv: "No dividends or interest this year.",
    emptyLots: "No open lots left after FIFO.",
    emptyZg: "No foreign-source income for PIT/ZG (or Poland only).",
    gain: "Gain",
    country: "Country",
    disclaimerTitle: "This is not tax advice",
  },
};

export default function Report({ report, lang }: { report: TaxSummary; lang: "pl" | "en" }) {
  const t = copy[lang];
  const [tab, setTab] = useState<Tab>("fifo");
  const pit = report.pit38;
  const fields = useMemo(
    () => [
      ["22", lang === "pl" ? "Przychód (papiery / pochodne)" : "Revenue (securities)", pit.field_22_revenue],
      ["23", lang === "pl" ? "Koszty uzyskania" : "Costs", pit.field_23_costs],
      ["28", lang === "pl" ? "Dochód" : "Income", pit.field_28_income],
      ["29", lang === "pl" ? "Strata" : "Loss", pit.field_29_loss],
      ["30", lang === "pl" ? "Straty z lat ubiegłych" : "Prior-year losses", pit.field_30_prior_losses],
      ["31", lang === "pl" ? "Podstawa opodatkowania" : "Tax base", pit.field_31_tax_base],
      ["33 / 35", lang === "pl" ? "Podatek 19% / do zapłaty" : "19% tax / due", pit.field_35_tax_due],
      ["47", lang === "pl" ? "Dywidendy i odsetki × 19%" : "Dividends & interest × 19%", pit.field_47_div_tax],
      ["48", lang === "pl" ? "Zaliczenie podatku zagranicznego" : "Foreign tax credit", pit.field_48_foreign_credit],
      ["49", lang === "pl" ? "Dopłata od dywidend/odsetek" : "Dividends/interest to pay", pit.field_49_div_to_pay],
      ["51", lang === "pl" ? "Łączny podatek" : "Total tax", pit.field_51_total_tax],
      ["72", lang === "pl" ? "Liczba załączników PIT/ZG" : "PIT/ZG attachments", pit.field_72_pit_zg_count],
    ],
    [lang, pit],
  );

  return (
    <section className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <Kpi label={t.due} value={pln.format(report.total_tax_pln)} accent />
        <Kpi label={t.income} value={pln.format(report.income_pln)} />
        <Kpi label={t.loss} value={pln.format(report.loss_pln)} />
        <Kpi label={t.cgTax} value={pln.format(report.capital_gains_tax_pln)} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Mini icon={Landmark} label={t.revenue} value={pln.format(report.revenue_pln)} />
        <Mini icon={Receipt} label={t.costs} value={pln.format(report.costs_pln)} />
        <Mini icon={PiggyBank} label={t.dividends} value={pln.format(report.dividends_gross_pln)} />
        <Mini icon={Globe2} label={t.credit} value={pln.format(report.dividends_withholding_pln)} />
      </div>

      <article className="overflow-hidden rounded-[28px] border border-[#d7cbb6] bg-[#fffdf8] shadow-[0_24px_60px_rgba(18,32,28,0.08)]">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-dashed border-[#d7cbb6] bg-[#f4efe4] px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[#c7922c]">Ministerstwo Finansów · helper</p>
            <h2 className="font-serif text-2xl">{t.paper}</h2>
          </div>
          <div className="text-right text-sm text-[#5c6b66]">
            <div>
              {t.year} {report.tax_year}
            </div>
            <div>{report.brokers.map(brokerLabel).join(" · ")}</div>
          </div>
        </header>
        <div className="grid gap-0 sm:grid-cols-2">
          {fields.map(([box, label, value]) => (
            <div key={String(box)} className="flex items-baseline justify-between gap-4 border-b border-[#efe6d4] px-6 py-3">
              <div>
                <span className="mr-2 font-serif text-lg text-[#2f6f5e]">{box}</span>
                <span className="text-sm text-[#5c6b66]">{label}</span>
              </div>
              <strong className="tabular-nums">
                {typeof value === "number" && Number(box) === 72 ? value : pln.format(Number(value))}
              </strong>
            </div>
          ))}
        </div>
      </article>

      <div className="flex flex-wrap gap-2">
        {(Object.keys(t.tabs) as Tab[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`rounded-full px-4 py-2 text-sm ${
              tab === key ? "bg-[#12201c] text-[#f4efe4]" : "bg-white/70 text-[#5c6b66]"
            }`}
          >
            {t.tabs[key]}
          </button>
        ))}
      </div>

      {tab === "fifo" && (
        <TableCard hint={t.fifoHint}>
          {report.realizations.length === 0 ? (
            <Empty text={t.emptyFifo} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wider text-[#5c6b66]">
                  <tr>
                    <th className="py-2">Symbol</th>
                    <th>FIFO</th>
                    <th className="text-right">{lang === "pl" ? "Ilość" : "Qty"}</th>
                    <th className="text-right">{t.revenue}</th>
                    <th className="text-right">{t.costs}</th>
                    <th className="text-right">{t.gain}</th>
                  </tr>
                </thead>
                <tbody>
                  {report.realizations.map((row, index) => (
                    <tr key={`${row.sell_id}-${index}`} className="border-t border-[#efe6d4]">
                      <td className="py-3">
                        <div className="font-medium">{row.symbol}</div>
                        <div className="text-xs text-[#5c6b66]">
                          {brokerLabel(row.broker)} · {row.country || "—"}
                        </div>
                      </td>
                      <td className="text-xs text-[#5c6b66]">
                        {row.buy_date || "?"} → {row.sell_date}
                        <div>
                          {qty.format(row.buy_price)} {row.buy_currency} @ {row.nbp_buy_rate} → {qty.format(row.sell_price)}{" "}
                          {row.sell_currency} @ {row.nbp_sell_rate}
                        </div>
                      </td>
                      <td className="text-right tabular-nums">{qty.format(row.quantity)}</td>
                      <td className="text-right tabular-nums">{pln.format(row.proceeds_pln)}</td>
                      <td className="text-right tabular-nums">{pln.format(row.cost_pln)}</td>
                      <td className={`text-right tabular-nums ${row.gain_pln >= 0 ? "text-[#2f6f5e]" : "text-[#c45c4a]"}`}>
                        {pln.format(row.gain_pln)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TableCard>
      )}

      {tab === "div" && (
        <TableCard>
          {report.dividends.length + report.interest.length === 0 ? (
            <Empty text={t.emptyDiv} />
          ) : (
            <div className="space-y-6">
              {report.dividends.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="text-xs uppercase tracking-wider text-[#5c6b66]">
                      <tr>
                        <th className="py-2">{lang === "pl" ? "Dywidenda" : "Dividend"}</th>
                        <th>{t.country}</th>
                        <th className="text-right">Brutto</th>
                        <th className="text-right">WHT</th>
                        <th className="text-right">19%</th>
                        <th className="text-right">{t.due}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.dividends.map((row) => (
                        <tr key={row.id} className="border-t border-[#efe6d4]">
                          <td className="py-3">
                            <div className="font-medium">{row.symbol}</div>
                            <div className="text-xs text-[#5c6b66]">
                              {row.date} · NBP {row.nbp_rate} ({row.nbp_table_date})
                            </div>
                          </td>
                          <td>{row.country || "—"}</td>
                          <td className="text-right tabular-nums">{pln.format(row.gross_pln)}</td>
                          <td className="text-right tabular-nums">{pln.format(row.withholding_pln)}</td>
                          <td className="text-right tabular-nums">{pln.format(row.polish_tax_19)}</td>
                          <td className="text-right tabular-nums">{pln.format(row.to_pay_pln)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {report.interest.map((row) => (
                <div key={row.id} className="flex items-center justify-between rounded-2xl bg-[#f4efe4] px-4 py-3 text-sm">
                  <span>
                    {t.interest} · {row.date} · {brokerLabel(row.broker)}
                  </span>
                  <strong>{pln.format(row.gross_pln)}</strong>
                </div>
              ))}
            </div>
          )}
        </TableCard>
      )}

      {tab === "lots" && (
        <TableCard>
          {report.open_lots.length === 0 ? (
            <Empty text={t.emptyLots} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wider text-[#5c6b66]">
                  <tr>
                    <th className="py-2">Symbol</th>
                    <th>{lang === "pl" ? "Zakup" : "Bought"}</th>
                    <th className="text-right">{lang === "pl" ? "Ilość" : "Qty"}</th>
                    <th className="text-right">{t.costs}</th>
                  </tr>
                </thead>
                <tbody>
                  {report.open_lots.map((row, index) => (
                    <tr key={`${row.symbol}-${row.buy_date}-${index}`} className="border-t border-[#efe6d4]">
                      <td className="py-3">
                        <div className="font-medium">{row.symbol}</div>
                        <div className="text-xs text-[#5c6b66]">{brokerLabel(row.broker)}</div>
                      </td>
                      <td>
                        {row.buy_date} · {qty.format(row.price)} {row.currency}
                      </td>
                      <td className="text-right tabular-nums">{qty.format(row.quantity)}</td>
                      <td className="text-right tabular-nums">{pln.format(row.cost_pln)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TableCard>
      )}

      {tab === "zg" && (
        <TableCard>
          {report.pit_zg.length === 0 ? (
            <Empty text={t.emptyZg} />
          ) : (
            <div className="grid gap-3">
              {report.pit_zg.map((row) => (
                <div key={row.country} className="rounded-2xl border border-[#efe6d4] p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <strong>
                      {row.country_name} ({row.country})
                    </strong>
                    <span className="text-sm text-[#5c6b66]">{pln.format(row.securities_income_pln)}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm text-[#5c6b66] sm:grid-cols-4">
                    <span>
                      {t.revenue}: {pln.format(row.securities_revenue_pln)}
                    </span>
                    <span>
                      {t.costs}: {pln.format(row.securities_costs_pln)}
                    </span>
                    <span>
                      {t.dividends}: {pln.format(row.dividends_gross_pln)}
                    </span>
                    <span>
                      WHT: {pln.format(row.dividends_withholding_pln)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </TableCard>
      )}

      {tab === "notes" && (
        <TableCard>
          <div className="space-y-3">
            {report.warnings.map((warning) => (
              <div
                key={warning.code + warning.message}
                className={`flex gap-3 rounded-2xl px-4 py-3 text-sm ${
                  warning.level === "error" ? "bg-[#f8e4df]" : warning.level === "warning" ? "bg-[#f7ecd2]" : "bg-[#e8f4ec]"
                }`}
              >
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <p>{warning.message}</p>
              </div>
            ))}
            {report.skipped.slice(0, 12).map((line) => (
              <p key={line} className="text-sm text-[#5c6b66]">
                {line}
              </p>
            ))}
            {report.warnings.length === 0 && report.skipped.length === 0 && (
              <Empty text={lang === "pl" ? "Brak uwag." : "No notes."} />
            )}
          </div>
        </TableCard>
      )}

      <aside className="rounded-[24px] border border-[#d7cbb6] bg-white/70 p-5 text-sm leading-6 text-[#5c6b66]">
        <div className="mb-1 flex items-center gap-2 font-medium text-[#12201c]">
          <BookOpen className="h-4 w-4" /> {t.disclaimerTitle}
        </div>
        {report.disclaimer}
      </aside>
    </section>
  );
}

function Kpi({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-[24px] p-5 ${accent ? "bg-[#12201c] text-[#f4efe4]" : "bg-white/80"}`}>
      <div className="text-xs uppercase tracking-[0.16em] opacity-70">{label}</div>
      <div className="mt-2 font-serif text-3xl tabular-nums">{value}</div>
    </div>
  );
}

function Mini({ icon: Icon, label, value }: { icon: typeof Landmark; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-white/60 px-4 py-3">
      <Icon className="h-4 w-4 text-[#2f6f5e]" />
      <div>
        <div className="text-xs text-[#5c6b66]">{label}</div>
        <div className="tabular-nums">{value}</div>
      </div>
    </div>
  );
}

function TableCard({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="rounded-[28px] border border-[#d7cbb6] bg-white/80 p-5">
      {hint && (
        <p className="mb-4 flex items-center gap-2 text-sm text-[#5c6b66]">
          <Layers3 className="h-4 w-4" /> {hint}
        </p>
      )}
      {children}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <p className="flex items-center gap-2 py-8 text-sm text-[#5c6b66]">
      <FileSpreadsheet className="h-4 w-4" /> {text}
    </p>
  );
}

# Belka — Polish stock-tax calculator

Upload broker exports from **Trading 212**, **XTB**, or a generic CSV. The app applies statutory **FIFO** per brokerage account, converts every leg to PLN with the **live NBP Table A/B rate from the previous business day (T-1)**, and maps totals onto **PIT-38 / PIT-ZG** helper fields.

A desk of AI agents (FX + tax) can explain the report and look up any published NBP rate. Rates are always fetched from `api.nbp.pl` — there is no FX cache.

This is an informational calculator, not tax advice. No Azure.

## Stack

- Backend: FastAPI, live NBP API, FIFO engine, OpenAI tool-calling agents
- Frontend: Vite, React, TypeScript, Tailwind CSS

## Run locally

```bash
# backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # paste OPENAI_API_KEY, or paste the key in the UI
python main.py

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` to `http://127.0.0.1:8000`.

### API key

The agents use the **OpenAI** API (not Azure). Either:

1. Put `OPENAI_API_KEY=` in `backend/.env`, or
2. Paste the key into the chat panel (stored only in your browser’s localStorage).

Optional: `OPENAI_MODEL` (default `gpt-4o`) and `OPENAI_BASE_URL` for an OpenAI-compatible endpoint.

## Agents

| Agent | Tools |
| --- | --- |
| Desk | Routes questions to the specialists |
| FX | Live NBP Table A (daily majors) and Table B (weekly others): daily table, latest table, single rate, date series, PLN conversion |
| Tax | Current FIFO report, PIT-38 fields, realizations, dividends, open lots, PIT/ZG, coded Polish tax rules |

FX tools always HTTP-GET `api.nbp.pl`. They will not invent a rate from model memory.

## Broker files

| Source | What to export |
| --- | --- |
| Trading 212 | History → Export CSV (orders, dividends, transactions). Use the **full history**, not one tax year. |
| XTB | xStation → Account history → closed positions and cash operations (CSV or XLSX). |
| Other | Generic CSV with `date,type,symbol,quantity,price,currency`. Types: `buy`, `sell`, `dividend`, `interest`. |

Sample files live in `backend/sample_data/` and can be loaded from the UI.

## What it calculates

- Capital gains: proceeds − FIFO cost − fees, in PLN
- 19% Belka tax, rounded to full zloty
- Foreign dividends / interest with withholding-tax credit (capped at 19%)
- PIT-38 boxes 22–35, 47–51, 72
- PIT/ZG split by ISIN country
- Open lots still held after FIFO
- Optional prior-year loss input (you apply the 50% / PLN 5m rules)

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

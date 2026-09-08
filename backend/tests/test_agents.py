from datetime import date
from decimal import Decimal
from pathlib import Path

from app.agents.session import Workspace
from app.agents.tax_agent import tax_handlers
from app.models import Pit38Fields, TaxSummary
from app.nbp import NbpClient


def test_t_minus_1_skips_to_last_published_day():
    client = NbpClient()
    client._tables["A"][date(2025, 2, 13)] = {"USD": Decimal("3.99")}
    lookup = client.t_minus_1("USD", date(2025, 2, 15))
    assert lookup.table_date == date(2025, 2, 13)
    assert lookup.rate == Decimal("3.99")
    assert lookup.table == "A"


def test_table_b_used_when_currency_missing_from_a():
    client = NbpClient()
    client._tables["A"][date(2025, 3, 12)] = {"USD": Decimal("4.00")}
    client._tables["B"][date(2025, 3, 12)] = {"MDL": Decimal("0.22")}
    lookup = client.rate_on_or_before("MDL", date(2025, 3, 12))
    assert lookup.table == "B"
    assert lookup.rate == Decimal("0.22")


def test_preload_never_writes_disk_cache(monkeypatch, tmp_path):
    cache_dir = Path(__file__).resolve().parent.parent / ".nbp_cache"
    before = set(cache_dir.glob("*.json")) if cache_dir.exists() else set()

    def fake_get(self, url):
        if "/tables/A/" in url:
            return [
                {
                    "no": "052/A/NBP/2025",
                    "effectiveDate": "2025-03-14",
                    "rates": [{"code": "USD", "mid": 3.91, "currency": "dolar"}],
                }
            ]
        return None

    monkeypatch.setattr(NbpClient, "_get", fake_get)
    NbpClient().preload(date(2025, 3, 14), date(2025, 3, 14))
    after = set(cache_dir.glob("*.json")) if cache_dir.exists() else set()
    assert after == before


def test_tax_agent_reads_workspace_report():
    report = TaxSummary(
        tax_year=2025,
        brokers=["trading212"],
        imported_files=["a.csv"],
        transaction_count=2,
        buy_count=1,
        sell_count=1,
        dividend_count=0,
        revenue_pln=100,
        costs_pln=80,
        income_pln=20,
        loss_pln=0,
        prior_losses_applied_pln=0,
        tax_base_pln=20,
        capital_gains_tax_pln=4,
        dividends_gross_pln=0,
        dividends_withholding_pln=0,
        dividends_tax_pln=0,
        dividends_credit_pln=0,
        dividends_to_pay_pln=0,
        interest_gross_pln=0,
        interest_tax_pln=0,
        total_tax_pln=4,
        unmatched_sold_qty=0,
        pit38=Pit38Fields(
            field_22_revenue=100,
            field_23_costs=80,
            field_28_income=20,
            field_29_loss=0,
            field_30_prior_losses=0,
            field_31_tax_base=20,
            field_33_tax=4,
            field_35_tax_due=4,
            field_47_div_tax=0,
            field_48_foreign_credit=0,
            field_49_div_to_pay=0,
            field_51_total_tax=4,
            field_72_pit_zg_count=0,
        ),
        realizations=[],
        dividends=[],
        interest=[],
        open_lots=[],
        pit_zg=[],
        warnings=[],
        skipped=[],
        disclaimer="test",
    )
    handlers = tax_handlers(Workspace(session_id="t", report=report))
    summary = handlers["get_tax_summary"]()
    assert summary["total_tax_pln"] == 4
    assert handlers["polish_tax_rules"]("nbp")["rule"].startswith("Each foreign")

from pathlib import Path

from app.engine import calculate_from_files

SAMPLES = Path(__file__).resolve().parent.parent / "sample_data"


def test_trading212_sample_tax_year_2025():
    data = (SAMPLES / "trading212_sample.csv").read_bytes()
    report = calculate_from_files([("trading212_sample.csv", data)], tax_year=2025, use_live_nbp=False)
    assert report.sell_count >= 2
    assert report.revenue_pln > 0
    assert report.total_tax_pln >= 0
    assert report.pit38.field_22_revenue == report.revenue_pln
    assert any(row.symbol == "AAPL" for row in report.realizations)


def test_combined_brokers():
    files = [
        ("trading212_sample.csv", (SAMPLES / "trading212_sample.csv").read_bytes()),
        ("xtb_closed_positions.csv", (SAMPLES / "xtb_closed_positions.csv").read_bytes()),
        ("xtb_cash_operations.csv", (SAMPLES / "xtb_cash_operations.csv").read_bytes()),
    ]
    report = calculate_from_files(files, tax_year=2025, use_live_nbp=False)
    assert set(report.brokers) >= {"trading212", "xtb"}
    assert report.dividend_count >= 1
    assert report.pit38.field_51_total_tax == report.total_tax_pln

from pathlib import Path

from app.parsers import parse_file
from app.models import TxType

SAMPLES = Path(__file__).resolve().parent.parent / "sample_data"


def test_trading212_sample_parses_trades_and_dividends():
    data = (SAMPLES / "trading212_sample.csv").read_bytes()
    parsed = parse_file("trading212_sample.csv", data)
    assert parsed.broker == "trading212"
    types = {tx.type for tx in parsed.transactions}
    assert TxType.BUY in types
    assert TxType.SELL in types
    assert TxType.DIVIDEND in types
    apple_buys = [tx for tx in parsed.transactions if tx.symbol == "AAPL" and tx.type == TxType.BUY]
    assert apple_buys[0].currency == "USD"
    shel = next(tx for tx in parsed.transactions if tx.symbol == "SHEL" and tx.type == TxType.BUY)
    assert shel.currency == "GBX"


def test_xtb_closed_positions_become_buy_and_sell():
    data = (SAMPLES / "xtb_closed_positions.csv").read_bytes()
    parsed = parse_file("xtb_closed_positions.csv", data)
    assert parsed.broker == "xtb"
    symbols = {tx.symbol for tx in parsed.transactions}
    assert "AAPL.US" in symbols
    assert "CDR.PL" in symbols
    buys = [tx for tx in parsed.transactions if tx.type == TxType.BUY]
    sells = [tx for tx in parsed.transactions if tx.type == TxType.SELL]
    assert len(buys) == len(sells) == 4


def test_generic_csv_round_trip():
    data = (SAMPLES / "generic_sample.csv").read_bytes()
    parsed = parse_file("generic_sample.csv", data)
    assert parsed.broker == "generic"
    assert len(parsed.transactions) == 4
    sell = next(tx for tx in parsed.transactions if tx.type == TxType.SELL)
    assert sell.quantity == 30

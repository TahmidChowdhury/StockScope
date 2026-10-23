"""Provider adaptation: splits outside a test range must not distort trade prices."""
import sys
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.trading import market


def test_reverse_splits_after_end_and_restore_dividend_share_basis(monkeypatch):
    frame = pd.DataFrame({"Open": [25, 24, 25], "Close": [25, 24, 25], "Dividends": [0, 1, 0], "Stock Splits": [0, 0, 4]}, index=pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]))
    ticker = SimpleNamespace(history=lambda **_: frame, history_metadata={"currency": "USD", "instrumentType": "EQUITY"})
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _: ticker))
    data = market.fetch_bars(["TEST"], date(2025, 1, 2), date(2025, 1, 3))["TEST"]
    assert [r["open"] for r in data] == [100, 96]
    assert data[1]["dividend"] == 4
    assert data[1]["split"] == 1


@pytest.mark.parametrize("metadata", [{"currency": "CAD", "instrumentType": "EQUITY"}, {"currency": "USD", "instrumentType": "CRYPTOCURRENCY"}])
def test_unsupported_currencies_and_instruments_fail_closed(monkeypatch, metadata):
    ticker = SimpleNamespace(history=lambda **_: pd.DataFrame(), history_metadata=metadata)
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _: ticker))
    with pytest.raises(ValueError, match="Usable USD price history unavailable"):
        market.fetch_bars(["TEST"], date(2025, 1, 2), date(2025, 1, 3))

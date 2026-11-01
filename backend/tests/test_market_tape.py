from datetime import datetime, timezone

import pytest

from backend.core.resources import state
from backend.services import market_tape as tape


@pytest.mark.parametrize("now, next_fetch", [
    ("2026-10-31T14:00", "2026-11-02T14:30"),  # Weekend crosses the DST change.
    ("2026-11-26T15:00", "2026-11-27T14:30"),  # Thanksgiving.
    ("2026-11-27T15:00", "2026-11-27T15:05"),
    ("2026-11-27T18:18", "2026-11-27T18:20"),  # Final delayed half-day close.
    ("2026-11-27T18:20", "2026-11-30T14:30"),
])
def test_next_batch_follows_exchange_sessions(now, next_fetch):
    start, end = [datetime.fromisoformat(dt).replace(tzinfo=timezone.utc) for dt in (now, next_fetch)]
    assert tape.refresh_delay(start) == (end - start).total_seconds()


def test_batch_keeps_missing_or_older_rows_and_survives_provider_failure(monkeypatch):
    stamp = 1793390400
    def observation(symbol, change, at=stamp):
        return {"symbol": symbol, "regularMarketChangePercent": change, "regularMarketTime": at}

    batches = iter([
        [observation("QQQ", 0), observation("SPY", -1), observation("DIA", 1)],
        [observation("SPY", 2, stamp + 60), observation("DIA", 3, stamp - 60),
         observation("AAPL", float("nan")), observation("AMZN", 2, None)],
    ])
    def load(symbols):
        assert symbols == tape.SYMBOLS
        return next(batches)

    monkeypatch.setattr(tape.market_provider, "get_quote_batch", load)
    first = tape.refresh().data
    assert [row["change"] for row in first] == [0, -1, 1]
    assert tape.refresh().data == first
    with state(tape._KEY) as record:
        record["expires_at"] = 0
    second = tape.refresh().data
    assert second[0] == first[0] and second[2] == first[2]
    assert second[1]["change"] == 2 and second[1]["as_of"] != first[1]["as_of"]
    with state(tape._KEY) as record:
        record["expires_at"] = 0
    fallback = tape.refresh()
    assert fallback.stale and fallback.data == second == tape.saved_quotes()

"""Saved SEC reads must stay authenticated, bounded, and independent of providers."""

import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.auth import verify_password_with_role
from backend.routers import fundamentals


@pytest.fixture
def api(monkeypatch):
    app = FastAPI()
    app.include_router(fundamentals.router, prefix="/api/fundamentals")
    app.dependency_overrides[verify_password_with_role] = lambda: "demo"
    monkeypatch.setattr(fundamentals, "is_sec_configured", lambda: True)
    # Any accidental provider use in this saved-data endpoint must fail the test.
    monkeypatch.setattr("backend.services.sec_facts.requests.get", lambda *args, **kwargs: pytest.fail("Saved reads must not contact SEC"))
    with TestClient(app) as client:
        yield client


def fact(identity, concept="Revenues", unit="USD", filed="2025-05-01", **values):
    return {"fact_id": identity, "taxonomy": "us-gaap", "concept": concept, "unit": unit, "label": concept,
            "filed": filed, "end": "2025-03-31", "start": "2025-01-01", "value": 0,
            "form": "10-Q", "frame": None, "fiscal_year": None, "fiscal_period": None,
            "accession": None, "filing_url": None, "period_kind": "duration", **values}


def test_no_saved_data_is_an_explicit_readable_state(api, monkeypatch):
    monkeypatch.setattr(fundamentals, "saved_sec_facts", lambda symbol: None)
    monkeypatch.setattr(fundamentals, "is_sec_configured", lambda: False)
    response = api.get("/api/fundamentals/aapl/sec-facts")
    assert response.status_code == 200
    result = response.json()
    assert result["symbol"] == "AAPL" and not result["saved"] and not result["configured"]
    assert result["status"] == "not_saved" and result["facts"] == [] and result["total"] == 0
    assert result["cik"] is None and result["concepts"] == []


def test_filters_preserve_units_amendments_nulls_and_full_options(api, monkeypatch):
    records = [fact("old"), fact("amended", filed="2025-05-20", form="10-Q/A"),
               fact("other-unit", unit="CAD"), fact("assets", concept="Assets"), fact("unknown", filed=None)]
    monkeypatch.setattr(fundamentals, "saved_sec_facts", lambda symbol: {
        "facts": records, "status": "partial", "cik": "0000320193", "entity_name": "Issuer",
        "metadata": {"retrieved_at": "2025-05-21T12:00:00Z", "as_of": "2025-05-20"}})
    response = api.get("/api/fundamentals/AAPL/sec-facts", params={"concept": "us-gaap:Revenues", "unit": "USD", "limit": 2})
    result = response.json()
    assert result["saved"] and result["status"] == "partial"
    assert result["total_saved"] == 5 and result["total"] == 3 and result["has_more"]
    assert [row["fact_id"] for row in result["facts"]] == ["amended", "old"]
    assert result["facts"][0]["value"] == 0 and result["facts"][0]["frame"] is None
    assert result["concepts"][1]["units"] == ["CAD", "USD"]
    assert result["metadata"]["as_of"] == "2025-05-20"
    page = api.get("/api/fundamentals/AAPL/sec-facts", params={"concept": "us-gaap:Revenues", "unit": "USD", "offset": 2, "limit": 2}).json()
    assert page["facts"][0]["filed"] is None and not page["has_more"]
    assert len(records) == 5  # Filtering/sorting does not mutate the saved snapshot.


@pytest.mark.parametrize("query", [{"limit": 201}, {"limit": 0}, {"offset": -1}, {"offset": 1000001}, {"concept": "x" * 201}])
def test_pagination_and_query_bounds_are_enforced(api, query):
    assert api.get("/api/fundamentals/AAPL/sec-facts", params=query).status_code == 422


def test_invalid_symbol_does_not_read_storage(api, monkeypatch):
    monkeypatch.setattr(fundamentals, "saved_sec_facts", lambda symbol: pytest.fail("Invalid symbols must not reach storage"))
    assert api.get("/api/fundamentals/AAPL!bad/sec-facts").status_code == 422


def test_storage_read_runs_off_the_event_loop(api, monkeypatch):
    threads = []
    async def user():
        threads.append(threading.get_ident())
        return "demo"
    api.app.dependency_overrides[verify_password_with_role] = user
    def read(symbol):
        threads.append(threading.get_ident())
        return None
    monkeypatch.setattr(fundamentals, "saved_sec_facts", read)
    assert api.get("/api/fundamentals/AAPL/sec-facts").status_code == 200
    assert len(threads) == 2 and threads[0] != threads[1]


def test_endpoint_requires_authentication(monkeypatch):
    app = FastAPI()
    app.include_router(fundamentals.router, prefix="/api/fundamentals")
    monkeypatch.setattr(fundamentals, "saved_sec_facts", lambda symbol: pytest.fail("Unauthenticated read must not reach storage"))
    with TestClient(app) as client:
        assert client.get("/api/fundamentals/AAPL/sec-facts").status_code == 401

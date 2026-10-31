"""HTTP, persistence, idempotency, and disclosure-to-backtest integration offline."""
import copy
import csv
import io
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.responses import JSONResponse

from backend.core.auth import create_access_token
from backend.db.engine import create_database_engine
from backend.db.repository import ResearchRepository
from backend.routers.trading import router
from backend.services import research
from backend.trading import congress, market, risk, service, storage
from backend.trading.models import PortfolioInput


@pytest.fixture(params=["file", "database"])
def context(request, monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "trading-test-signing-key-not-a-password-123456789")
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path / "data"))
    engine = None
    repo = None
    if request.param == "database":
        engine = create_database_engine(f"sqlite:///{tmp_path / 'trading.db'}", allow_sqlite=True)
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            workspace_config = Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'), ini_section='workspace')
            workspace_config.attributes['connection'] = connection
            command.upgrade(workspace_config, 'head')
        repo = ResearchRepository(engine)
        assert repo.check_ready()
    monkeypatch.setattr(research, "repository", lambda: repo)
    app = FastAPI()
    app.include_router(router, prefix="/api/trading")

    @app.exception_handler(SQLAlchemyError)
    async def unavailable(request, exc):
        return JSONResponse(status_code=503, content={"detail": "Storage unavailable"})

    # Full historical bar coverage in a controlled USD equity fixture.
    def prices(symbols, start, end):
        rows = []
        day = start
        while day <= end:
            if day.weekday() < 5:
                rows.append({"date": day.isoformat(), "open": 100.0, "close": 101.0, "split": 1.0, "dividend": 0.0})
            day += timedelta(days=1)
        return {s: copy.deepcopy(rows) for s in set(symbols)}
    monkeypatch.setattr(market, "fetch_bars", prices)
    headers = {role: {"Authorization": f"Bearer {create_access_token('fixture', role)}"} for role in ["admin", "guest", "demo"]}
    if repo:
        from backend.db.models import WorkspaceUser
        with repo.session_factory.begin() as session:
            for legacy, role in [('admin', 'admin'), ('guest', 'viewer'), ('demo', 'member')]:
                user = WorkspaceUser(email=role + '@example.test', name=role, role=role, password_hash='fixture-no-login')
                session.add(user)
                session.flush()
                headers[legacy] = {'Authorization': 'Bearer ' + create_access_token('user:' + user.id, role, session_version=user.session_version)}
    with TestClient(app) as client:
        yield client, headers, prices, tmp_path, repo
    if engine:
        engine.dispose()


def csv_text(rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=congress.COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def disclosure(**changes):
    return {"disclosure_id": "house-row-1", "member": "Example Member", "owner": "spouse", "symbol": "AAPL", "side": "buy", "transaction_date": "2025-01-02", "available_date": "2025-01-06", "asset_type": "stock", "amount_range": "$1,001 - $15,000", "source_url": "https://disclosures-clerk.house.gov/example.pdf", **changes}


def test_bearer_and_admin_boundaries(context):
    client, headers, *_ = context
    assert client.get('/api/trading/portfolios').status_code == 401
    for role in ['guest', 'demo']:
        assert client.get('/api/trading/portfolios', headers=headers[role]).status_code == 200
        assert client.post('/api/trading/portfolios', headers=headers[role], json={"name": "No"}).status_code == 403
        assert client.post('/api/trading/backtests', headers=headers[role], json={"start": "2025-01-01", "end": "2025-12-31"}).status_code == 403
        assert client.post('/api/trading/congress/import', headers=headers[role], json={"csv_text": csv_text([disclosure()])}).status_code == 403


def test_portfolio_orders_are_recorded_before_execution_and_idempotent(context):
    client, headers, *_ = context
    p = client.post('/api/trading/portfolios', headers=headers['admin'], json={"name": "Learning", "initial_cash": 5000}).json()
    key = p['id']
    request = {"client_order_id": str(uuid4()), "symbol": "AAPL", "side": "buy", "budget": 500, "thesis": "Evaluate the next earnings release"}
    response = client.post(f'/api/trading/portfolios/{key}/orders', headers=headers['admin'], json=request)
    assert response.status_code == 201
    assert response.json()['result'] is None
    assert len(response.json()['orders']) == 1
    assert 'submitted_at' in response.json()['orders'][0]
    assert client.post(f'/api/trading/portfolios/{key}/orders', headers=headers['admin'], json=request).json()['orders'] == response.json()['orders']
    assert client.post(f'/api/trading/portfolios/{key}/orders', headers=headers['admin'], json={**request, "budget": 600}).status_code == 409
    # Guests can read shared ledgers, never submit or cancel.
    assert client.get(f'/api/trading/portfolios/{key}', headers=headers['guest']).json()['name'] == 'Learning'
    assert client.post(f'/api/trading/portfolios/{key}/orders', headers=headers['guest'], json=request).status_code == 403
    order_id = response.json()['orders'][0]['id']
    cancelled = client.post(f'/api/trading/portfolios/{key}/orders/{order_id}/cancel', headers=headers['admin'], json={})
    assert cancelled.status_code == 200
    assert cancelled.json()['orders'][0]['cancelled_at']
    assert len(cancelled.json()['orders']) == 1  # Cancellation retains the original journal.
    assert client.post(f'/api/trading/portfolios/{key}/refresh', headers=headers['admin'], json={}).json()['result'] is None


def test_refresh_freezes_prior_fills_and_failed_refresh_preserves_saved_result(context, monkeypatch):
    client, headers, prices, _, _ = context
    created = service.create_portfolio(PortfolioInput(name='Frozen'))
    key = created['id']
    def seed(document):
        document['created_at'] = '2025-01-01T12:00:00+00:00'
        document['orders'] = [{"id": 'order-a', "client_order_id": 'fixture-order', "symbol": 'AAPL', "side": 'buy', "budget": 1000, "thesis": 'Saved before outcome', "submitted_at": '2025-01-02T12:00:00+00:00', "signal_date": '2025-01-02'}]
        return document
    storage.mutate(key, seed)
    monkeypatch.setattr(market, 'market_today', lambda: date(2025, 1, 8))
    first = client.post(f'/api/trading/portfolios/{key}/refresh', headers=headers['admin'], json={})
    assert first.status_code == 200
    assert first.json()['result']['fills'][0]['execution_date'] == '2025-01-03'
    def revised(symbols, start, end):
        data = prices(symbols, start, end)
        for rows in data.values():
            for row in rows:
                row['open'] = 1000.0
        return data
    monkeypatch.setattr(market, 'fetch_bars', revised)
    second = client.post(f'/api/trading/portfolios/{key}/refresh', headers=headers['admin'], json={})
    assert second.json()['result']['fills'] == first.json()['result']['fills']
    def unavailable(*_):
        raise ValueError('Fixture price outage')
    monkeypatch.setattr(market, 'fetch_bars', unavailable)
    assert client.post(f'/api/trading/portfolios/{key}/refresh', headers=headers['admin'], json={}).status_code == 422
    saved = client.get(f'/api/trading/portfolios/{key}', headers=headers['admin']).json()
    assert saved['result'] == second.json()['result']
    assert 'data' not in saved


def test_congress_import_and_disclosure_aware_backtest_with_snapshot_export(context):
    client, headers, *_ = context
    body = {"csv_text": csv_text([disclosure(), disclosure(disclosure_id='option-row', asset_type='option')])}
    imported = client.post('/api/trading/congress/import', headers=headers['admin'], json=body)
    assert imported.status_code == 200
    assert imported.json()['inserted'] == 2
    assert client.post('/api/trading/congress/import', headers=headers['admin'], json=body).json()['duplicates'] == 2
    rows = client.get('/api/trading/congress', headers=headers['guest']).json()
    assert rows['records'][0]['lag_days'] == 4
    assert rows['members'] == ['Example Member']
    backtest = {"strategy": "congress", "start": "2025-01-01", "end": "2025-01-10", "member": "Example Member", "costs": {"commission": 1}}
    response = client.post('/api/trading/backtests', headers=headers['admin'], json=backtest)
    assert response.status_code == 201, response.text
    run = response.json()
    assert len(run['result']['fills']) == 1
    assert run['result']['fills'][0]['execution_date'] == '2025-01-07'
    assert run['result']['fills'][0]['transaction_date'] == '2025-01-02'
    assert run['result']['exclusions'][0]['disclosure_id'] == 'option-row'
    assert 'data' not in run
    saved = client.get(f"/api/trading/backtests/{run['id']}/export", headers=headers['guest']).json()
    assert saved['data']['AAPL']
    assert saved['disclosures'][0]['owner'] == 'spouse'
    assert len(saved['data_sha256']) == 64
    assert client.get('/api/trading/backtests', headers=headers['admin']).json()[0]['id'] == run['id']
    delayed = client.post('/api/trading/backtests', headers=headers['admin'], json={**backtest, "disclosure_delay_days": 4}).json()
    assert delayed['result']['fills'] == []
    assert len(delayed['result']['pending']) == 1


@pytest.mark.parametrize('delay_days', [1, 7])
def test_congress_full_year_keeps_more_than_twenty_symbols_and_sales(context, delay_days):
    client, headers, *_ = context
    symbols = [f'STK{chr(65 + i)}' for i in range(25)]
    rows = [disclosure(disclosure_id=f'buy-{symbol}', symbol=symbol) for symbol in symbols]
    rows += [disclosure(disclosure_id=f'sell-{symbol}', symbol=symbol, side='sell',
                        transaction_date='2025-11-03', available_date='2025-11-05')
             for symbol in symbols]
    assert client.post('/api/trading/congress/import', headers=headers['admin'],
                       json={'csv_text': csv_text(rows)}).status_code == 200
    response = client.post('/api/trading/backtests', headers=headers['admin'], json={
        'strategy': 'congress', 'member': 'Example Member', 'symbols': [],
        'start': '2025-01-01', 'end': '2025-12-31', 'disclosure_delay_days': delay_days,
        'trade_fraction': .02, 'costs': {'slippage_bps': 5, 'spread_bps': 2, 'commission': 0},
    })
    assert response.status_code == 201, response.text
    run = response.json()
    result = run['result']
    assert run['resolved_symbols'] == symbols
    assert {row['disclosure_id'] for row in run['disclosures']} == {row['disclosure_id'] for row in rows}
    assert result['metrics']['fill_count'] == 50
    assert {fill['symbol'] for fill in result['fills'] if fill['side'] == 'buy'} == set(symbols)
    assert {fill['symbol'] for fill in result['fills'] if fill['side'] == 'sell'} == set(symbols)
    assert all(fill['execution_date'] > fill['signal_date'] for fill in result['fills'])
    assert result['positions'] == result['pending'] == result['rejected'] == result['exclusions'] == []
    assert result['metrics']['total_costs'] > 0
    assert result['metrics']['benchmark_costs'] > 0
    exported = client.get(f"/api/trading/backtests/{run['id']}/export", headers=headers['guest']).json()
    assert set(exported['data']) == {*symbols, 'SPY'}
    assert exported['resolved_symbols'] == symbols


@pytest.mark.parametrize('failure', ['unavailable', 'incomplete'])
def test_large_congress_test_cannot_drop_a_symbol_with_unusable_data(context, monkeypatch, failure):
    client, headers, prices, *_ = context
    symbols = [f'STK{chr(65 + i)}' for i in range(25)]
    # Even a sale with no pre-window holding remains part of the evidence and data checks.
    rows = [disclosure(disclosure_id=f'row-{symbol}', symbol=symbol,
                       side='sell' if symbol == symbols[-1] else 'buy') for symbol in symbols]
    assert client.post('/api/trading/congress/import', headers=headers['admin'],
                       json={'csv_text': csv_text(rows)}).status_code == 200

    def unusable_data(requested, start, end):
        assert set(requested) == {*symbols, 'SPY'}
        if failure == 'unavailable':
            raise ValueError(f'Usable USD price history unavailable for {symbols[-1]}; no test was saved')
        data = prices(requested, start, end)
        data[symbols[-1]].pop(0)
        return data

    monkeypatch.setattr(market, 'fetch_bars', unusable_data)
    response = client.post('/api/trading/backtests', headers=headers['admin'], json={
        'strategy': 'congress', 'member': 'Example Member', 'symbols': [],
        'start': '2025-01-01', 'end': '2025-12-31',
    })
    assert response.status_code == 422
    assert symbols[-1] in response.json()['detail']
    assert client.get('/api/trading/backtests', headers=headers['guest']).json() == []


def test_congress_disclosure_work_limit_precedes_price_fetch(context, monkeypatch):
    client, headers, *_ = context
    rows = [disclosure(disclosure_id=f'row-{i}') for i in range(1001)]
    assert client.post('/api/trading/congress/import', headers=headers['admin'],
                       json={'csv_text': csv_text(rows)}).status_code == 200

    def no_fetch(*_):
        raise AssertionError('Reject oversized requests before provider access')

    monkeypatch.setattr(market, 'fetch_bars', no_fetch)
    response = client.post('/api/trading/backtests', headers=headers['admin'], json={
        'strategy': 'congress', 'member': 'Example Member',
        'start': '2025-01-01', 'end': '2025-12-31',
    })
    assert response.status_code == 422
    assert response.json()['detail'] == 'Limit a Congress test to 1,000 eligible disclosures'
    assert client.get('/api/trading/backtests', headers=headers['guest']).json() == []


def test_congress_browse_filters_and_summaries_cover_records_beyond_the_page(context):
    client, headers, *_ = context
    rows = [
        disclosure(disclosure_id='row-1'),
        disclosure(disclosure_id='row-2', owner='member', symbol='MSFT', side='sell',
                   transaction_date='2025-01-03', available_date='2025-01-08'),
        disclosure(disclosure_id='row-3', member='Other Member', owner='dependent', side='sell',
                   transaction_date='2025-01-04', available_date='2025-01-10'),
        disclosure(disclosure_id='row-4', member='Other Member', symbol='NVDA',
                   transaction_date='2025-01-05', available_date='2025-01-12'),
        disclosure(disclosure_id='row-5', member='Third Member', asset_type='option',
                   transaction_date='2025-01-05', available_date='2025-01-15'),
    ]
    assert client.post('/api/trading/congress/import', headers=headers['admin'],
                       json={'csv_text': csv_text(rows)}).status_code == 200

    # Totals cover the full imported evidence, including asset types excluded from copying tests.
    response = client.get('/api/trading/congress', headers=headers['guest'],
                          params={'symbol': ' aapl ', 'limit': 1, 'offset': 1})
    assert response.status_code == 200
    data = response.json()
    assert [row['disclosure_id'] for row in data['records']] == ['row-3']
    assert (data['total'], data['offset']) == (3, 1)
    assert data['summary'] == {'total': 5, 'buys': 3, 'sells': 2, 'symbol_count': 3, 'member_count': 3,
                               'latest_available_date': '2025-01-15', 'average_lag_days': 6.4}
    assert data['filtered_summary'] == {'total': 3, 'buys': 2, 'sells': 1, 'symbol_count': 1, 'member_count': 3,
                                        'latest_available_date': '2025-01-15', 'average_lag_days': 6.67}
    assert data['members'] == ['Example Member', 'Other Member', 'Third Member']
    assert data['symbols'] == ['AAPL', 'MSFT', 'NVDA']
    profiles = {profile['member']: profile for profile in data['member_profiles']}
    assert profiles['Example Member']['total'] == 2
    assert profiles['Example Member']['buys'] == profiles['Example Member']['sells'] == 1
    assert profiles['Example Member']['average_lag_days'] == 4.5
    assert profiles['Other Member']['latest_available_date'] == '2025-01-12'
    assert profiles['Third Member']['total'] == 1
    assert data['mode'] == 'csv_import' and data['live_feed_connected'] is False
    assert data['provenance']['source'] == 'user_supplied_csv'
    assert data['provenance']['dates_verified'] is False
    assert data['provenance']['limitations']
    assert data['last_import']['inserted'] == 5

    cases = [
        ({'symbol': 'AAPL', 'side': 'sell'}, ['row-3']),
        ({'member': 'Example Member', 'side': 'sell', 'q': 'msft'}, ['row-2']),
        ({'q': '  SpOuSe  '}, ['row-5', 'row-4', 'row-1']),
        ({'q': 'row-4'}, ['row-4']),
        ({'symbol': 'AAPL', 'q': 'MSFT'}, []),
    ]
    for params, expected in cases:
        filtered = client.get('/api/trading/congress', headers=headers['demo'], params=params).json()
        assert [row['disclosure_id'] for row in filtered['records']] == expected
        assert filtered['total'] == filtered['filtered_summary']['total'] == len(expected)
        assert filtered['summary'] == data['summary']
        assert filtered['member_profiles'] == data['member_profiles']


def test_congress_empty_browse_is_authenticated_and_has_no_invented_statistics(context):
    client, headers, *_ = context
    assert client.get('/api/trading/congress').status_code == 401
    response = client.get('/api/trading/congress', headers=headers['guest'], params={'q': 'nothing'})
    assert response.status_code == 200
    data = response.json()
    assert data['records'] == data['members'] == data['symbols'] == data['member_profiles'] == []
    assert data['last_import'] is None
    assert data['summary'] == data['filtered_summary'] == {
        'total': 0, 'buys': 0, 'sells': 0, 'symbol_count': 0, 'member_count': 0,
        'latest_available_date': None, 'average_lag_days': None,
    }


@pytest.mark.parametrize('params', [
    {'symbol': 'AA/PL'}, {'symbol': 'X' * 11}, {'side': 'hold'}, {'side': 'Buy'},
    {'q': 'x' * 121}, {'member': 'x' * 151}, {'offset': -1}, {'offset': 60001},
    {'limit': 0}, {'limit': 201},
])
def test_congress_browse_rejects_invalid_or_unbounded_filters(context, params):
    client, headers, *_ = context
    assert client.get('/api/trading/congress', headers=headers['guest'], params=params).status_code == 422


@pytest.mark.parametrize('name_input, expected', [
    ({'name': '  Walkthrough · AAPL + MSFT  '}, 'Walkthrough · AAPL + MSFT'),
    ({'name': '   '}, None),
    ({'name': None}, None),
    ({}, None),
])
def test_backtest_optional_name_round_trips_in_results_listing_and_export(context, name_input, expected):
    client, headers, *_ = context
    response = client.post('/api/trading/backtests', headers=headers['admin'], json={
        'start': '2025-01-02', 'end': '2025-01-10', 'symbols': ['AAPL', 'MSFT'], **name_input,
    })
    assert response.status_code == 201, response.text
    run = response.json()
    assert run['name'] == expected
    assert client.get('/api/trading/backtests', headers=headers['guest']).json()[0]['name'] == expected
    assert client.get(f"/api/trading/backtests/{run['id']}", headers=headers['guest']).json()['name'] == expected
    assert client.get(f"/api/trading/backtests/{run['id']}/export", headers=headers['guest']).json()['name'] == expected

    # Existing documents without this optional field still load and list normally.
    def legacy_document(document):
        document.pop('name')
        return document
    storage.mutate(run['id'], legacy_document)
    assert client.get(f"/api/trading/backtests/{run['id']}", headers=headers['guest']).status_code == 200
    assert client.get('/api/trading/backtests', headers=headers['guest']).json()[0]['id'] == run['id']


def test_backtest_rename_changes_only_name_and_summary(context, monkeypatch):
    client, headers, *_ = context
    response = client.post('/api/trading/backtests', headers=headers['admin'], json={
        'name': 'Original experiment', 'start': '2025-01-02', 'end': '2025-01-10', 'symbols': ['AAPL', 'MSFT'],
    })
    assert response.status_code == 201, response.text
    key = response.json()['id']
    before = client.get(f'/api/trading/backtests/{key}/export', headers=headers['guest']).json()

    def no_recalculation(*_):
        raise AssertionError('Renaming must not collect prices or rerun the experiment')
    monkeypatch.setattr(market, 'prepare_data', no_recalculation)
    monkeypatch.setattr(service, 'simulate', no_recalculation)
    path = f'/api/trading/backtests/{key}/name'
    response = client.post(path, headers=headers['admin'], json={'name': '  Walkthrough · rolling-year baseline  '})
    assert response.status_code == 200, response.text
    expected = {**before, 'name': 'Walkthrough · rolling-year baseline'}
    assert response.json() == {k: v for k, v in expected.items() if k != 'data'}
    assert client.get(f'/api/trading/backtests/{key}/export', headers=headers['guest']).json() == expected
    summary = client.get('/api/trading/backtests', headers=headers['guest']).json()[0]
    assert summary['name'] == expected['name']
    assert summary['created_at'] == before['created_at']
    assert summary['metrics'] == before['result']['metrics']

    # Both API validation failures and unauthorized writes leave the saved run untouched.
    assert client.post(path, json={'name': 'Unauthorized'}).status_code == 401
    for role in ['guest', 'demo']:
        assert client.post(path, headers=headers[role], json={'name': 'Unauthorized'}).status_code == 403
    for invalid in [{}, {'name': ''}, {'name': '   '}, {'name': None}, {'name': 'x' * 81}, {'name': 'Valid', 'start': '2020-01-01'}]:
        assert client.post(path, headers=headers['admin'], json=invalid).status_code == 422
    assert client.get(f'/api/trading/backtests/{key}/export', headers=headers['guest']).json() == expected


def test_backtest_rename_missing_or_wrong_kind_is_not_found(context):
    client, headers, *_ = context
    key = f'run-{uuid4()}'
    path = f'/api/trading/backtests/{key}/name'
    assert client.post(path, headers=headers['admin'], json={'name': 'Missing'}).status_code == 404
    assert storage.read(key) is None
    assert client.post(f'/api/trading/backtests/portfolio-{uuid4()}/name', headers=headers['admin'], json={'name': 'Wrong type'}).status_code == 404
    before = {'id': key, 'kind': 'portfolio', 'name': 'Wrong document type', 'created_at': '2025-01-02T12:00:00+00:00'}
    storage.mutate(key, lambda _: before)
    assert client.post(path, headers=headers['admin'], json={'name': 'Do not overwrite'}).status_code == 404
    assert storage.read(key) == before


def test_backtest_risk_is_authenticated_read_only_saved_curve_analysis(context, monkeypatch):
    pytest.importorskip('quantstats')
    client, headers, *_ = context
    response = client.post('/api/trading/backtests', headers=headers['admin'], json={
        'start': '2025-01-02', 'end': '2025-01-10', 'symbols': ['AAPL', 'MSFT'],
    })
    assert response.status_code == 201, response.text
    key = response.json()['id']
    before = client.get(f'/api/trading/backtests/{key}/export', headers=headers['guest']).json()

    def forbidden(*_):
        raise AssertionError('Saved risk analysis must neither write nor fetch prices nor rerun the engine')
    monkeypatch.setattr(market, 'fetch_bars', forbidden)
    monkeypatch.setattr(market, 'prepare_data', forbidden)
    monkeypatch.setattr(service, 'simulate', forbidden)
    monkeypatch.setattr(storage, 'mutate', forbidden)
    path = f'/api/trading/backtests/{key}/risk'
    assert client.get(path).status_code == 401
    for role in ['admin', 'guest', 'demo']:
        response = client.get(path, headers=headers[role])
        assert response.status_code == 200, response.text
        assert response.json()['sample_count'] == len(before['result']['curve'])
        assert response.json()['as_of'] == before['result']['as_of']
    assert client.get(f'/api/trading/backtests/{key}/export', headers=headers['guest']).json() == before


def test_backtest_risk_missing_dependency_is_feature_scoped_and_missing_run_is_not_found(context, monkeypatch):
    client, headers, *_ = context
    key = f'run-{uuid4()}'
    assert client.get(f'/api/trading/backtests/{key}/risk', headers=headers['guest']).status_code == 404
    assert client.get(f'/api/trading/backtests/portfolio-{uuid4()}/risk', headers=headers['guest']).status_code == 404
    response = client.post('/api/trading/backtests', headers=headers['admin'], json={'start': '2025-01-02', 'end': '2025-01-10'})
    key = response.json()['id']
    def unavailable():
        raise risk.RiskUnavailable('QuantStats dependency unavailable')
    monkeypatch.setattr(risk, '_library', unavailable)
    response = client.get(f'/api/trading/backtests/{key}/risk', headers=headers['guest'])
    assert response.status_code == 503
    assert response.json()['detail'] == 'QuantStats dependency unavailable'
    assert client.get(f'/api/trading/backtests/{key}', headers=headers['guest']).status_code == 200


@pytest.mark.parametrize('change', [
    {"available_date": "2024-01-01"}, {"available_date": "2099-01-01"}, {"available_date": ""},
    {"side": "purchase"}, {"asset_type": ""}, {"symbol": "../../file"}, {"source_url": "javascript:alert(1)"},
    {"source_url": "https://user:secret@example.com/doc"}, {"member": "x" * 151},
])
def test_invalid_disclosure_batch_is_atomic(context, change):
    client, headers, *_ = context
    response = client.post('/api/trading/congress/import', headers=headers['admin'], json={"csv_text": csv_text([disclosure(), disclosure(disclosure_id='bad-row', **change)])})
    assert response.status_code == 422
    assert storage.read('congress') is None
    assert client.get('/api/trading/congress', headers=headers['admin']).json()['total'] == 0


def test_imported_member_at_length_limit_remains_filterable(context):
    client, headers, *_ = context
    member = 'x' * 150
    response = client.post('/api/trading/congress/import', headers=headers['admin'],
                           json={'csv_text': csv_text([disclosure(member=member)])})
    assert response.status_code == 200
    data = client.get('/api/trading/congress', headers=headers['guest'], params={'member': member}).json()
    assert data['total'] == 1 and data['records'][0]['member'] == member


def test_conflicting_import_never_rewrites_history(context):
    client, headers, *_ = context
    path = '/api/trading/congress/import'
    assert client.post(path, headers=headers['admin'], json={"csv_text": csv_text([disclosure()])}).status_code == 200
    conflict = client.post(path, headers=headers['admin'], json={"csv_text": csv_text([disclosure(disclosure_id='new-row'), disclosure(side='sell')])})
    assert conflict.status_code == 422
    saved = client.get('/api/trading/congress', headers=headers['admin']).json()
    assert saved['total'] == 1 and saved['records'][0]['side'] == 'buy'


def test_storage_failure_never_reads_local_fallback(context, monkeypatch):
    _, _, _, directory, repo = context
    if repo is None:
        pytest.skip('Database-specific failure case')
    def fail(*_):
        raise OperationalError('fixture', {}, RuntimeError('offline'))
    monkeypatch.setattr(repo.engine, 'connect', fail)
    (directory / 'data' / 'trading').mkdir(parents=True)
    (directory / 'data' / 'trading' / 'congress.json').write_text('{"records": []}')
    with pytest.raises(OperationalError):
        storage.read('congress')


def test_paper_refresh_cannot_overwrite_an_order_submitted_during_fetch(context, monkeypatch):
    client, headers, prices, *_ = context
    key = service.create_portfolio(PortfolioInput(name='Concurrent'))['id']
    storage.mutate(key, lambda d: {**d, 'created_at': '2025-01-01T12:00:00+00:00'})
    monkeypatch.setattr(market, 'market_today', lambda: date(2025, 1, 8))
    def submit_during_fetch(symbols, start, end):
        from backend.trading.models import OrderInput
        service.place_order(key, OrderInput(client_order_id='concurrent-order', symbol='AAPL', side='buy', budget=100, thesis='Submitted during collection'))
        return prices(symbols, start, end)
    monkeypatch.setattr(market, 'fetch_bars', submit_during_fetch)
    response = client.post(f'/api/trading/portfolios/{key}/refresh', headers=headers['admin'], json={})
    assert response.status_code == 409
    saved = storage.read(key)
    assert len(saved['orders']) == 1 and saved['result'] is None


def test_file_mode_concurrent_imports_do_not_lose_disclosures(context):
    from concurrent.futures import ThreadPoolExecutor
    _, _, _, _, repo = context
    if repo is not None:
        pytest.skip('File-lock behavior is separate from PostgreSQL row locks')
    rows = [congress.parse_csv(csv_text([disclosure(disclosure_id=f'parallel-{i}')])) for i in range(8)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda batch: storage.mutate('congress', lambda previous: congress.merge_import(previous, batch)), rows))
    assert len(storage.read('congress')['records']) == 8


def test_cancelled_symbols_cannot_block_a_later_portfolio_valuation(context, monkeypatch):
    client, headers, prices, *_ = context
    key = service.create_portfolio(PortfolioInput(name='Cancelled symbol'))['id']
    def seed(document):
        document['created_at'] = '2025-01-01T12:00:00+00:00'
        document['orders'] = [{'id': 'cancelled-order', 'client_order_id': 'cancel-fixture', 'symbol': 'INVALID', 'side': 'buy', 'budget': 100, 'signal_date': '2025-01-02', 'thesis': 'Cancelled', 'cancelled_at': '2025-01-02T12:00:00+00:00'}]
        return document
    storage.mutate(key, seed)
    monkeypatch.setattr(market, 'market_today', lambda: date(2025, 1, 8))
    def verified_prices(symbols, start, end):
        assert 'INVALID' not in symbols
        return prices(symbols, start, end)
    monkeypatch.setattr(market, 'fetch_bars', verified_prices)
    response = client.post(f'/api/trading/portfolios/{key}/refresh', headers=headers['admin'], json={})
    assert response.status_code == 200
    assert response.json()['result']['metrics']['total_return'] == 0
    assert not response.json()['result']['fills']
    assert len(response.json()['orders']) == 1

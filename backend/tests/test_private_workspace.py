"""Security, persistence and resource regressions for the friends-only workspace."""
import asyncio
import hashlib
import importlib
from datetime import timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, event

from backend.db.engine import create_database_engine
from backend.db.repository import ResearchRepository
from backend.db.models import WorkspaceUser, WorkspaceInvite, ResourceState, utcnow
from backend.services import accounts
from backend.core import resources
from backend.core.auth import create_access_token

PASSWORD = 'test-only-long-passphrase'


@pytest.fixture
def workspace(monkeypatch, tmp_path):
    engine = create_database_engine('sqlite:///' + str(tmp_path / 'workspace.db'), allow_sqlite=True)
    for section in ('alembic', 'workspace'):
        config = Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'), ini_section=section)
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')
    repo = ResearchRepository(engine)
    monkeypatch.setattr('backend.db.get_repository', lambda: repo)
    for key, value in {'ADMIN_PASSWORD': 'owner-setup-password', 'DEMO_PASSWORD': 'demo', 'GUEST_PASSWORD': 'guest', 'SECRET_KEY': 'test-secret-with-at-least-32-characters'}.items():
        monkeypatch.setenv(key, value)
    accounts._attempts.clear()
    api = importlib.import_module('backend.api')
    api.cache.invalidate()
    api.analysis_status.clear()
    owner = accounts.bootstrap('owner@example.test', 'Owner', PASSWORD, 'owner-setup-password')
    client = TestClient(api.app)
    def auth(user):
        return {'Authorization': 'Bearer ' + create_access_token('user:' + user.id, user.role, session_version=user.session_version)}
    yield client, repo, owner, auth
    engine.dispose()


def join(owner, email='friend@example.test', role='member'):
    invite = accounts.issue_invite(owner, email, role)
    return accounts.accept_invite(invite['token'], email, 'Friend', PASSWORD), invite


def test_invite_is_hashed_email_bound_single_use_and_expiring(workspace):
    client, repo, owner, auth = workspace
    invite = accounts.issue_invite(owner, 'Friend@example.test', 'member')
    with repo.session_factory() as session:
        stored = session.get(WorkspaceInvite, invite['id'])
        assert stored.token_hash == hashlib.sha256(invite['token'].encode()).hexdigest()
        assert invite['token'] not in stored.token_hash
    body = {'token': invite['token'], 'email': 'wrong@example.test', 'name': 'Friend', 'password': PASSWORD}
    assert client.post('/api/auth/accept-invite', json=body).status_code == 400
    body['email'] = 'friend@example.test'
    assert client.post('/api/auth/accept-invite', json=body).status_code == 201
    assert client.post('/api/auth/accept-invite', json=body).status_code == 400
    expired = accounts.issue_invite(owner, 'expired@example.test', 'viewer')
    with repo.session_factory.begin() as session:
        session.get(WorkspaceInvite, expired['id']).expires_at = utcnow() - timedelta(seconds=1)
    assert client.post('/api/auth/accept-invite', json={**body, 'token': expired['token'], 'email': 'expired@example.test'}).status_code == 400


def test_no_public_signup_or_shared_password_bypass(workspace):
    client, _, owner, auth = workspace
    assert client.post('/api/auth/signup', json={}).status_code == 404
    assert client.post('/api/auth/setup', json={'email': 'other@example.test', 'name': 'Other', 'password': PASSWORD, 'owner_password': 'owner-setup-password'}).status_code == 409
    assert client.post('/api/auth/login', json={'password': 'owner-setup-password'}).status_code == 401
    assert client.get('/api/stocks', headers={'Authorization': 'Bearer ' + create_access_token('stockscope_user', 'admin')}).status_code == 401
    assert client.post('/api/auth/sign-in', json={'email': 'owner@example.test', 'password': PASSWORD}).status_code == 200


def test_lists_are_private_and_removal_never_deletes_research(workspace):
    client, repo, owner, auth = workspace
    friend, _ = join(owner)
    repo.save_snapshot('AAPL', 'news_sentiment', [{'title': 'Saved article', 'publishedAt': '2026-10-29T00:00:00Z', 'source': 'Example'}])
    created = client.post('/api/lists', headers=auth(owner), json={'name': 'Core'}).json()
    path = '/api/lists/' + created['id']
    assert client.put(path + '/items', headers=auth(owner), json={'symbol': 'AAPL', 'pinned': True}).status_code == 200
    assert client.get('/api/lists', headers=auth(friend)).json() == []
    assert client.put(path + '/items', headers=auth(friend), json={'symbol': 'MSFT'}).status_code == 404
    assert client.delete(path, headers=auth(friend)).status_code == 404
    second = client.post('/api/lists', headers=auth(owner), json={'name': 'Second', 'initial_symbol': 'aapl'})
    assert second.status_code == 201
    assert second.json()['items'] == [{'symbol': 'AAPL', 'pinned': False}]
    second_path = '/api/lists/' + second.json()['id']
    assert client.get('/api/lists', headers=auth(friend)).json() == []
    assert client.delete(second_path + '/items/AAPL', headers=auth(friend)).status_code == 404
    first_with_pin = {**created, 'items': [{'symbol': 'AAPL', 'pinned': True}]}
    assert client.delete(second_path + '/items/AAPL', headers=auth(owner)).status_code == 200
    assert client.get('/api/lists', headers=auth(owner)).json() == [first_with_pin, {**second.json(), 'items': []}]
    assert client.put(second_path + '/items/batch', headers=auth(owner), json={'symbols': ['AAPL']}).status_code == 200
    assert client.delete(second_path, headers=auth(owner)).status_code == 200
    assert client.get('/api/lists', headers=auth(owner)).json() == [first_with_pin]
    assert repo.list_symbols() == ['AAPL']
    assert repo.load_snapshots('AAPL')[0][1][0]['title'] == 'Saved article'


def test_create_with_initial_symbol_validates_before_saving_and_obeys_limits(workspace):
    client, _, owner, auth = workspace
    headers = auth(owner)
    assert client.post('/api/lists', headers=headers, json={'name': 'Core', 'initial_symbol': 'BAD!'}).status_code == 422
    assert client.get('/api/lists', headers=headers).json() == []
    assert client.post('/api/lists', headers=headers, json={'name': 'Core'}).status_code == 201
    duplicate = client.post('/api/lists', headers=headers, json={'name': 'Core', 'initial_symbol': 'AAPL'})
    assert duplicate.status_code == 409
    for index in range(19):
        assert client.post('/api/lists', headers=headers, json={'name': f'List {index}'}).status_code == 201
    assert client.post('/api/lists', headers=headers, json={'name': 'One more', 'initial_symbol': 'AAPL'}).status_code == 409
    lists = client.get('/api/lists', headers=headers).json()
    assert len(lists) == 20 and all(row['items'] == [] for row in lists)


def test_revocation_invalidates_existing_tokens_and_cannot_demote_self(workspace):
    client, _, owner, auth = workspace
    friend, _ = join(owner)
    headers = auth(friend)
    assert client.get('/api/lists', headers=headers).status_code == 200
    assert client.post('/api/access/invites', headers=headers, json={'email': 'attacker@example.test'}).status_code == 403
    assert client.put('/api/access/users/' + owner.id, headers=auth(owner), json={'active': False, 'role': 'viewer'}).status_code == 409
    assert client.put('/api/access/users/' + friend.id, headers=auth(owner), json={'active': False, 'role': 'member'}).status_code == 200
    assert client.get('/api/lists', headers=headers).status_code == 401
    assert client.post('/api/auth/sign-in', json={'email': friend.email, 'password': PASSWORD}).status_code == 401
    assert client.put('/api/access/users/' + friend.id, headers=auth(owner), json={'active': True, 'role': 'viewer'}).status_code == 200
    assert client.get('/api/lists', headers=headers).status_code == 401
    login = client.post('/api/auth/sign-in', json={'email': friend.email, 'password': PASSWORD}).json()
    viewer = {'Authorization': 'Bearer ' + login['access_token']}
    assert client.post('/api/stocks/analyze', headers=viewer, json={'symbol': 'AAPL', 'sources': ['news']}).status_code == 403
    assert client.post('/api/auth/sign-out', headers=viewer).status_code == 200
    assert client.get('/api/lists', headers=viewer).status_code == 401


def test_summary_does_not_read_payloads_or_call_providers(workspace, monkeypatch):
    client, repo, owner, auth = workspace
    repo.save_snapshot('AAPL', 'news_sentiment', [{'title': 'Article', 'publishedAt': '2026-10-29T00:00:00Z'}])
    monkeypatch.setattr('backend.core.market_provider.Ticker', lambda *args, **kwargs: pytest.fail('No providers on list reads'))
    statements = []
    event.listen(repo.engine, 'before_cursor_execute', lambda conn, cursor, statement, params, context, many: statements.append(statement))
    result = client.get('/api/stocks', headers=auth(owner))
    assert result.status_code == 200
    assert result.json()['stocks'][0]['total_posts'] == 1
    assert result.json()['stocks'][0]['currentPrice'] is None
    assert not any('snapshot_revisions' in query.lower() for query in statements)


def test_daily_budget_is_durable_shared_and_never_calls_network_after_cap(workspace, monkeypatch):
    _, repo, _, _ = workspace
    monkeypatch.setenv('PROVIDER_SEC_DAILY_LIMIT', '2')
    resources.reserve('sec', cooldown=0)
    resources.reserve('sec', cooldown=0)
    with pytest.raises(resources.BudgetExceeded):
        resources.reserve('sec', cooldown=0)
    with repo.session_factory() as session:
        assert session.get(ResourceState, 'provider:sec').payload['count'] == 2
    with pytest.raises(resources.BudgetExceeded):
        resources.guarded_get('https://data.sec.gov/api/test')
    resources.record_response('yahoo', 429, {'Retry-After': '7200'})
    with pytest.raises(resources.BudgetExceeded, match='cooling down'):
        resources.reserve('yahoo', cooldown=0)


def test_refresh_cooldown_and_global_cap_survive_new_repository(workspace, monkeypatch):
    _, repo, _, _ = workspace
    monkeypatch.setenv('PROVIDER_REFRESH_DAILY_LIMIT', '2')
    resources.admit_refresh('AAPL')
    with pytest.raises(resources.BudgetExceeded, match='six hours'):
        resources.admit_refresh('AAPL')
    resources.admit_refresh('MSFT')
    with pytest.raises(resources.BudgetExceeded, match='daily'):
        resources.admit_refresh('NVDA')
    with repo.session_factory() as session:
        assert session.get(ResourceState, 'provider:refresh').payload['count'] == 2


def test_password_hash_is_salted_and_never_stored_as_plaintext(workspace):
    _, repo, owner, _ = workspace
    with repo.session_factory() as session:
        stored = session.get(WorkspaceUser, owner.id)
        assert PASSWORD not in stored.password_hash
        assert accounts.valid_password(PASSWORD, stored.password_hash)
        assert not accounts.valid_password('wrong-password-long', stored.password_hash)
        assert accounts.hash_password(PASSWORD) != stored.password_hash


def test_owner_reset_link_revokes_old_sessions_without_changing_role(workspace):
    client, _, owner, auth = workspace
    friend, _ = join(owner, role='viewer')
    before = auth(friend)
    reset = client.post('/api/access/users/' + friend.id + '/reset', headers=auth(owner)).json()
    accepted = client.post('/api/auth/accept-invite', json={'token': reset['token'], 'email': friend.email,
                                                        'name': 'Ignored', 'password': 'a-new-test-passphrase'})
    assert accepted.status_code == 201
    assert accepted.json()['role'] == 'viewer'
    assert client.get('/api/lists', headers=before).status_code == 401
    assert client.post('/api/auth/sign-in', json={'email': friend.email, 'password': PASSWORD}).status_code == 401
    assert client.post('/api/auth/sign-in', json={'email': friend.email, 'password': 'a-new-test-passphrase'}).status_code == 200


def test_durable_fundamentals_cache_coalesces_and_keeps_last_good_data(workspace):
    from backend.core.cache import cached, clear_cache, peek_many
    calls = []
    @cached
    def fixture_fundamentals(symbol):
        calls.append(symbol)
        return {'ttm': {'ticker': symbol, 'revenue_ttm': 42}, 'metadata': {'insufficient_data': False, 'retrieved_at': '2026-10-01T00:00:00Z'}}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fixture_fundamentals, ['AAPL'] * 4))
    assert calls == ['AAPL']
    clear_cache()  # Simulate an API process restart.
    assert fixture_fundamentals('AAPL') == results[0]
    assert calls == ['AAPL']
    saved = peek_many('fixture_fundamentals', ['AAPL', 'MSFT'])
    assert saved == {'AAPL': results[0]}
    assert calls == ['AAPL']


def test_screening_does_not_make_provider_calls(workspace, monkeypatch):
    client, _, owner, auth = workspace
    monkeypatch.setattr('backend.core.market_provider.Ticker', lambda *args, **kwargs: pytest.fail('Screening must use saved fundamentals'))
    result = client.post('/api/fundamentals/screener', headers=auth(owner), json={'universe': ['AAPL', 'MSFT']})
    assert result.status_code == 200
    assert result.json()['total_evaluated'] == 0


def test_workspace_migration_keeps_deployed_research_version(workspace):
    from sqlalchemy import text
    _, repo, _, _ = workspace
    with repo.engine.connect() as connection:
        assert connection.scalar(text('select version_num from alembic_version')) == '20261015_02'
        assert connection.scalar(text('select version_num from workspace_schema_version')) == '20261030_03'


def test_batch_list_add_is_atomic_and_preserves_pins(workspace):
    client, _, owner, auth = workspace
    path = '/api/lists/' + client.post('/api/lists', headers=auth(owner), json={'name': 'Batch'}).json()['id']
    assert client.put(path + '/items', headers=auth(owner), json={'symbol': 'AAPL', 'pinned': True}).status_code == 200
    assert client.put(path + '/items/batch', headers=auth(owner), json={'symbols': ['MSFT', 'not valid']}).status_code == 422
    assert len(client.get('/api/lists', headers=auth(owner)).json()[0]['items']) == 1
    assert client.put(path + '/items/batch', headers=auth(owner), json={'symbols': ['AAPL', 'msft', 'MSFT']}).status_code == 200
    items = client.get('/api/lists', headers=auth(owner)).json()[0]['items']
    assert len(items) == 2
    assert next(item for item in items if item['symbol'] == 'AAPL')['pinned'] is True


def test_resource_history_is_persistent_and_admin_only(workspace):
    client, repo, owner, auth = workspace
    yesterday = (utcnow().date() - timedelta(days=1)).isoformat()
    with resources.state('provider:yahoo') as usage:
        usage.update(day=yesterday, count=4, responses={'429': 1})
    response = client.get('/api/resources', headers=auth(owner))
    assert response.status_code == 200
    yahoo = next(row for row in response.json()['providers'] if row['provider'] == 'yahoo')
    assert yahoo['used'] == 0
    assert yahoo['history'][0]['count'] == 4
    with repo.session_factory() as session:
        assert session.get(ResourceState, 'provider:yahoo').payload['history'][yesterday]['responses'] == {'429': 1}
    friend, _ = join(owner)
    assert client.get('/api/resources', headers=auth(friend)).status_code == 403


def test_remembered_device_is_opt_in_scoped_and_revocable(workspace):
    client, _, owner, auth = workspace
    friend, _ = join(owner)
    creds = {'email': friend.email, 'password': PASSWORD}
    regular = client.post('/api/auth/sign-in', json=creds).json()
    assert 'device_token' not in regular
    assert client.post('/api/auth/resume', json={'token': regular['access_token']}).status_code == 401
    remembered = client.post('/api/auth/sign-in', json={**creds, 'remember_device': True}).json()
    assert remembered['device_max_age'] == 30 * 86400
    credential = {'token': remembered['device_token']}
    assert client.get('/api/lists', headers={'Authorization': 'Bearer ' + credential['token']}).status_code == 401
    resumed = client.post('/api/auth/resume', json=credential).json()
    assert resumed['user']['id'] == friend.id and 'device_token' not in resumed
    headers = {'Authorization': 'Bearer ' + resumed['access_token']}
    assert client.get('/api/lists', headers=headers).status_code == 200
    assert client.post('/api/auth/password', headers=headers, json={
        'current_password': 'wrong', 'new_password': 'different-long-password'
    }).status_code == 400
    assert client.post('/api/auth/resume', json=credential).status_code == 200
    assert client.post('/api/auth/sign-out', headers=headers).status_code == 200
    assert client.post('/api/auth/resume', json=credential).status_code == 401
    newer = client.post('/api/auth/sign-in', json={**creds, 'remember_device': True}).json()
    client.put('/api/access/users/' + friend.id, headers=auth(owner), json={'active': False, 'role': 'member'})
    assert client.post('/api/auth/resume', json={'token': newer['device_token']}).status_code == 401


def test_personal_yahoo_quota_is_enforced_on_actual_requests_and_private_to_each_account(workspace, monkeypatch):
    from backend.core import market_provider as market
    from backend.services import valuation
    from backend.routers import fundamentals
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    client, _, owner, auth = workspace
    friend, _ = join(owner)
    today = datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    with resources.state('provider:yahoo') as usage:
        usage.update(personal_day=today, personal_counts={owner.id: 49}, count=113,
                     day=datetime.now(timezone.utc).date().isoformat())
    calls = []
    class FakeTicker:
        @property
        def info(self):
            # Mimic an SDK hitting the limit on an internal retry and returning partial data.
            for i in range(2):
                try:
                    resources.reserve('yahoo', cooldown=0)
                except resources.PersonalYahooLimit:
                    break
                calls.append(resources.yahoo_principal.get())
            return {'symbol': 'IBM', 'currentPrice': 12}

    monkeypatch.setattr(market, 'Ticker', lambda _: FakeTicker())
    request = '/api/stocks/IBM/info'
    # Caller-controlled identity hints cannot transfer the charge.
    denied = client.get(request, headers={**auth(owner), 'X-User-Id': friend.id})
    assert denied.status_code == 429 and int(denied.headers['retry-after']) > 0
    assert 'midnight Eastern' in denied.json()['detail']
    assert calls == [owner.id]
    assert client.get(request, headers=auth(friend)).status_code == 200
    assert calls == [owner.id, friend.id, friend.id]
    assert client.get(request, headers=auth(owner)).status_code == 200  # free shared snapshot
    assert client.get('/api/account/yahoo-usage', headers=auth(owner)).json()['used'] == 50
    assert client.get('/api/account/yahoo-usage', headers=auth(friend)).json()['used'] == 2

    # Raw executor jobs must carry the authenticated identity as well.
    def compute(symbol):
        resources.reserve('yahoo', cooldown=0)
        return {'ticker': symbol}
    monkeypatch.setattr(valuation, '_load', compute)
    monkeypatch.setattr(fundamentals, '_compute_ttm_cached', compute)
    assert client.get('/api/valuation/QUOTA', headers=auth(owner)).status_code == 429
    assert client.get('/api/valuation/QUOTA', headers=auth(friend)).status_code == 200
    assert client.post('/api/fundamentals/compare', headers=auth(owner), json={'tickers': ['IBM']}).status_code == 429
    assert client.post('/api/fundamentals/compare', headers=auth(friend), json={'tickers': ['IBM']}).status_code == 200
    assert client.get('/api/account/yahoo-usage', headers=auth(friend)).json()['used'] == 4

    # User-initiated research still has the initiating identity in the background worker.
    api = importlib.import_module('backend.api')
    def collect_news(symbol):
        resources.reserve('yahoo', cooldown=0, category='news')
        return {}
    monkeypatch.setattr(api, '_collect_news', collect_news)
    assert client.post('/api/stocks/analyze', headers=auth(friend), json={'symbol': 'IBM', 'sources': ['news']}).status_code == 202
    assert client.get('/api/account/yahoo-usage', headers=auth(friend)).json()['used'] == 5

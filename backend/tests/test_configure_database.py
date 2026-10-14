"""Private setup input handling; never contacts a hosted database."""

import pytest
from dotenv import dotenv_values
from scripts import configure_database as setup

REF = 'zkuvyybcfdpljpttrwdj'
URI = f'postgresql://postgres.{REF}:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres'


@pytest.mark.parametrize('value', [URI, f"'{URI}'", f'psql "{URI}"', f'DATABASE_URL="{URI}"'])
def test_dashboard_copy_formats(value):
    url = setup.parse_connection(value, REF)
    assert url.username == f'postgres.{REF}'
    assert url.password is None
    assert url.query['sslmode'] == 'require'


@pytest.mark.parametrize('value', ['', 'private-invalid-input', 'https://private.example.org', URI.replace(':5432', ':6543'), URI.replace(REF, 'wrongproject'), URI + '?host=private.example.org'])
def test_invalid_inputs_have_safe_actionable_errors(value):
    with pytest.raises(ValueError) as error:
        setup.parse_connection(value, REF)
    assert 'private' not in str(error.value)
    assert '[YOUR-PASSWORD]' not in str(error.value)


def test_success_encodes_password_and_preserves_existing_settings(monkeypatch, tmp_path, capsys):
    env = tmp_path / '.env'
    env.write_text('SECRET_KEY=keep-existing-value\n')
    monkeypatch.setattr(setup, 'ENV_PATH', env)
    monkeypatch.setattr(setup.sys.stdin, 'isatty', lambda: True)
    password = 'fixture:@/#$pass'
    values = iter(['not-a-uri', URI, password])
    monkeypatch.setattr(setup.getpass, 'getpass', lambda _: next(values))
    checked = []
    monkeypatch.setattr(setup, 'check_connection', lambda url: checked.append(url))
    assert setup.main(['--project-ref', REF]) == 0
    saved = dotenv_values(env)
    assert saved['SECRET_KEY'] == 'keep-existing-value'
    assert setup.make_url(saved['DATABASE_URL']).password == password
    assert checked[0].password == password
    assert env.stat().st_mode & 0o777 == 0o600
    output = capsys.readouterr().out
    assert password not in output and 'not-a-uri' not in output


def test_failed_connection_keeps_environment_unchanged(monkeypatch, tmp_path, capsys):
    env = tmp_path / '.env'
    original = 'DATABASE_URL=previous\nSECRET_KEY=unchanged\n'
    env.write_text(original)
    monkeypatch.setattr(setup, 'ENV_PATH', env)
    monkeypatch.setattr(setup.sys.stdin, 'isatty', lambda: True)
    values = iter([URI, 'fixture-secret'])
    monkeypatch.setattr(setup.getpass, 'getpass', lambda _: next(values))
    def fail(url):
        raise RuntimeError('fixture-secret must never be printed')
    monkeypatch.setattr(setup, 'check_connection', fail)
    assert setup.main(['--project-ref', REF]) == 1
    assert env.read_text() == original
    assert 'fixture-secret' not in capsys.readouterr().out


def test_existing_connection_prompts_only_for_password(monkeypatch, tmp_path, capsys):
    env = tmp_path / '.env'
    from dotenv import set_key
    set_key(str(env), 'DATABASE_URL', URI)
    monkeypatch.setattr(setup, 'ENV_PATH', env)
    monkeypatch.setattr(setup.sys.stdin, 'isatty', lambda: True)
    prompts = []
    def password(prompt):
        prompts.append(prompt)
        return 'literal%40:@/$fixture'
    monkeypatch.setattr(setup.getpass, 'getpass', password)
    checked = []
    monkeypatch.setattr(setup, 'check_connection', lambda url: checked.append(url))
    assert setup.main(['--project-ref', REF, '--use-existing']) == 0
    assert len(prompts) == 1 and 'Database password' in prompts[0]
    assert checked[0].password == 'literal%40:@/$fixture'
    assert setup.make_url(dotenv_values(env)['DATABASE_URL']).password == 'literal%40:@/$fixture'
    assert 'literal' not in capsys.readouterr().out

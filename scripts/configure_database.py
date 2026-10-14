"""Privately configure a Supabase connection; checks connectivity before saving."""

import argparse
import getpass
from pathlib import Path
import shlex
import sys
import warnings

from dotenv import dotenv_values, set_key
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

from backend.db.engine import create_database_engine

ENV_PATH = Path(__file__).resolve().parents[1] / '.env'


def parse_connection(value, project_ref):
    """Accept dashboard URI, quoted URI, psql command, or DATABASE_URL assignment."""
    value = value.strip()
    if not value:
        raise ValueError('Nothing was pasted. Copy the URI from Connect → Session pooler.')
    if value.startswith('DATABASE_URL='):
        value = value.split('=', 1)[1].strip()
    if value.startswith('psql '):
        try:
            parts = shlex.split(value)
        except ValueError:
            raise ValueError('The copied psql command has unmatched quotes. Copy only its URI.') from None
        if len(parts) != 2:
            raise ValueError('Copy only the connection URI, without extra psql options.')
        value = parts[1]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    if value.startswith('https://'):
        raise ValueError('That is a website/API URL. Choose Connect → Session pooler → URI.')
    try:
        url = make_url(value)
        port = url.port
    except Exception:
        raise ValueError('Expected a URI beginning postgresql://, copied from Connect → Session pooler.') from None
    if url.drivername not in {'postgres', 'postgresql', 'postgresql+psycopg'}:
        raise ValueError('Choose the PostgreSQL URI format in the Connect dialog.')
    host = url.host or ''
    direct = host == f'db.{project_ref}.supabase.co' and url.username == 'postgres'
    pooled = host.endswith('.pooler.supabase.com') and url.username == f'postgres.{project_ref}'
    if not (direct or pooled) or url.database != 'postgres' or port not in {None, 5432}:
        raise ValueError('Use this project’s direct URI or Session pooler URI on port 5432; verify the selected project.')
    if set(url.query) - {'sslmode', 'connect_timeout'}:
        raise ValueError('Copy the standard dashboard URI without extra connection options.')
    # Password is requested separately, so callers can paste the placeholder safely.
    return URL.create(
        drivername='postgresql+psycopg', username=url.username, host=url.host,
        port=url.port, database=url.database,
        query={'sslmode': url.query.get('sslmode') if url.query.get('sslmode') in {'verify-ca', 'verify-full'} else 'require', 'connect_timeout': '10'},
    )


def check_connection(url):
    engine = create_database_engine(url)
    try:
        with engine.connect() as connection:
            connection.execute(text('SET TRANSACTION READ ONLY'))
            assert connection.scalar(text('SELECT 1')) == 1
    finally:
        engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-ref', required=True, help='Expected Supabase project reference (not a secret)')
    parser.add_argument('--use-existing', action='store_true', help='Reuse the saved URI and ask only for the database password')
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        print('Run this command directly in your terminal so secret input stays hidden.')
        return 1
    warnings.simplefilter('error', getpass.GetPassWarning)
    try:
        url = None
        if args.use_existing:
            try:
                url = parse_connection(dotenv_values(ENV_PATH, interpolate=False).get('DATABASE_URL') or '', args.project_ref)
            except ValueError as error:
                print(str(error))
                print('Saved connection is invalid. Run without --use-existing to replace it.')
                return 1
        else:
            for _ in range(3):
                pasted = getpass.getpass('Paste Session pooler URI (hidden; then press Enter): ')
                try:
                    url = parse_connection(pasted, args.project_ref)
                    break
                except ValueError as error:
                    print(str(error))  # Only fixed messages; never echo user input.
        if url is None:
            print('No settings changed. Reopen Connect and run this command again.')
            return 1
        password = getpass.getpass('Database password (hidden; then press Enter): ')
        if not password or password == '[YOUR-PASSWORD]':
            print('Enter your actual database password. No settings changed.')
            return 1
        url = url.set(password=password)
        print('Checking a read-only connection…')
        try:
            check_connection(url)
        except Exception:
            print('Connection failed. Check the database password, project readiness, and Session pooler URI. No settings changed.')
            return 1
        if ENV_PATH.is_symlink():
            print('The environment file is a symlink; configure it manually. No settings changed.')
            return 1
        result = set_key(str(ENV_PATH), 'DATABASE_URL', url.render_as_string(hide_password=False))
        if not result[0]:
            raise OSError('Could not save environment file')
        ENV_PATH.chmod(0o600)
        print('Connection verified. DATABASE_URL saved privately to .env; other settings preserved.')
        print('No tables were created or changed. You can now return to the chat.')
        return 0
    except (KeyboardInterrupt, EOFError):
        print('\nSetup cancelled.')
        return 1
    except getpass.GetPassWarning:
        print('Hidden input is unavailable. Run this command in an interactive terminal.')
        return 1
    except Exception:
        print('Setup could not finish. No credentials are printed; check local file permissions before retrying.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

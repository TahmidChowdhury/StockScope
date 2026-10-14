#!/usr/bin/env python3
"""Read-only HTTP smoke checks; passwords/tokens are never printed or put in URLs."""

import argparse
import os
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-url', default='http://localhost:8000')
    parser.add_argument('--frontend-url', default='http://localhost:3000')
    parser.add_argument('--ticker', help='Optionally check live fundamentals for this symbol')
    args = parser.parse_args()
    base = args.api_url.rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error('Provide an HTTP(S) API origin without credentials or query parameters')
    if parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
        parser.error('Remote APIs must use HTTPS')
    load_dotenv(Path(__file__).with_name('.env'))
    password = os.getenv('STOCKSCOPE_TEST_PASSWORD') or os.getenv('ADMIN_PASSWORD')
    if not password:
        print('FAIL: Set STOCKSCOPE_TEST_PASSWORD or ADMIN_PASSWORD; no default password is used.')
        return 1
    checks = []

    def check(name, condition):
        checks.append(bool(condition))
        print(f"{'PASS' if condition else 'FAIL'}: {name}")

    try:
        with requests.Session() as client:
            check('API health', client.get(f'{base}/health', timeout=10, allow_redirects=False).status_code == 200)
            check('Unauthenticated session rejected', client.get(f'{base}/api/auth/session', timeout=10, allow_redirects=False).status_code == 401)
            response = client.post(f'{base}/api/auth/login', json={'password': password}, timeout=10, allow_redirects=False)
            payload = response.json() if response.status_code == 200 else {}
            token = payload.get('access_token')
            check('Password login returns bearer session', bool(token) and payload.get('token_type') == 'bearer')
            if not token:
                return 1
            client.headers['Authorization'] = f'Bearer {token}'
            response = client.get(f'{base}/api/auth/session', timeout=10, allow_redirects=False)
            check('Bearer session accepted', response.status_code == 200 and response.json().get('role') in ('admin', 'demo', 'guest'))
            response = client.get(f'{base}/api/stocks/AAPL/quantitative', timeout=10, allow_redirects=False)
            body = response.json() if response.status_code == 200 else {}
            check('Unvalidated metrics withheld', body.get('status') == 'unavailable' and body.get('metrics') == {} and 'confidence' not in body and 'recommendation' not in body)
            if args.ticker:
                response = client.get(f'{base}/api/fundamentals/{quote(args.ticker.upper(), safe="")}', timeout=90, allow_redirects=False)
                check('Fundamentals response', response.status_code == 200 and 'ttm' in response.json())
        # Do not forward the API Authorization header to the frontend.
        check('Frontend HTTP response', requests.get(args.frontend_url, timeout=15, allow_redirects=False).status_code == 200)
    except (requests.RequestException, ValueError, KeyError):
        print('FAIL: A service could not be reached or returned an invalid response. Check its local logs.')
        return 1
    print(f'{sum(checks)}/{len(checks)} smoke checks passed. These checks do not validate investment performance.')
    return 0 if all(checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())

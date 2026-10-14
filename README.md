# StockScope

StockScope is a personal stock-research workspace for a long-term investing core and a separate trading-learning allocation. It combines company fundamentals, comparison, a curated stock screener, dated news, and links to original SEC filings.

## Current behavior

- **Fundamentals:** quarterly and trailing-twelve-month financials from yfinance, with missing values and calculation limitations exposed. Free cash flow requires both operating cash flow and capital expenditure. Growth figures identify their reporting basis.
- **Comparison and screening:** compare companies and filter a **curated 110-symbol universe**, or supply a custom universe. This is not a complete/current S&P 500 constituent list. Coverage counts distinguish failures, missing data, matches, and displayed results.
- **SEC reported facts:** an explicit refresh collects primary financial facts and recent filings. The fundamentals page exposes periods, units, filing versions, and original links alongside the existing yfinance metrics; SEC facts do not silently replace TTM calculations.
- **Research:** news text-tone scores describe saved articles; SEC filing events and company press releases are unscored. Publication dates are distinct from summary-generation dates, and unknown dates stay unknown.
- **Refresh:** collect new source snapshots explicitly, with completion, partial-result, and failure status. Merely opening saved research does not imply it was refreshed.
- **Shared watchlist:** saved analyzed symbols are shared across authenticated roles. This is not a holdings ledger or a measure of actual portfolio returns.
- **Authentication:** a shared password for each role is exchanged for an expiring bearer token. The browser keeps tokens in sessionStorage, removes old stored passwords, and clears client data on logout/expiry. API credentials are no longer accepted in URL query parameters.

Users sign in on the website with one of the app passwords configured on the backend. `ADMIN_PASSWORD` grants administrative deletion/cache access; `DEMO_PASSWORD` and `GUEST_PASSWORD` currently both allow research reads and refreshes. Everyone sees the same watchlist and saved research. There is no email signup, user-owned portfolio, or account password-reset flow yet. Supabase stores research; Supabase Auth is not connected to this login. The legacy `STOCKSCOPE_PASSWORD` also grants admin if set; remove that variable when deploying the three role passwords. Sessions last eight hours by default and are stored per browser tab; existing sessions must sign in again after the authentication migration.

The former BUY/SELL/HOLD recommendations, probability-like confidence percentages, and fabricated quantitative metrics have been removed from active API responses. The legacy `/investment-advice` route now returns an evidence summary. `/quantitative` explicitly reports that validated metrics are unavailable. Experimental code in `analysis/` is not a validated investment model and is no longer called by these routes.

## Architecture

```text
Next.js frontend (Vercel)
        | HTTPS + Authorization: Bearer token
FastAPI backend (Railway)
        |-- Fundamentals / prices: yfinance
        |-- News: RSS / Yahoo / configured company IR / GDELT
        |-- Reported financial facts + filing events: SEC EDGAR
        |-- DATABASE_URL set: Supabase Postgres
        |   (versioned research, shared watchlist, collection outcomes)
        `-- DATABASE_URL absent: local JSON snapshots + in-memory jobs
```

The frontend and backend deploy separately. Postgres stores research and job outcomes when configured; a failed database never silently falls back to files. Without `DATABASE_URL`, file mode remains available and job status is lost on restart.

Run **one backend process/worker and one replica**. Work still executes in that process, with a four-job admission limit. At startup, unfinished persisted runs are marked failed, not resumed. Stop the old process before starting a replacement: overlapping deployments can mark another process’s work interrupted. A durable external queue and shared cache are still future work.

## Local setup

Use Python 3.11 and Node.js 22 (Node 24 is also supported). Run commands from the repository root unless otherwise stated.

```bash
python3.11 -m venv venv
venv/bin/python -m pip install -r requirements.txt
npm --prefix stockscope-frontend ci
cp .env.example .env
cp stockscope-frontend/.env.example stockscope-frontend/.env.local
```

Set three distinct private role passwords in `.env` and generate an independent signing secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into `SECRET_KEY`. It must be at least 32 characters and must not equal a login password. Missing/invalid signing configuration prevents startup. Never put the secret in a `NEXT_PUBLIC_` variable or commit `.env`.

Required backend variables:

| Variable | Purpose |
|---|---|
| `ADMIN_PASSWORD` | Full access, including deleting saved research and clearing caches |
| `DEMO_PASSWORD` | Shared research access without admin mutations |
| `GUEST_PASSWORD` | Restricted access as enforced by API routes |
| `SECRET_KEY` | Independent random signing secret, at least 32 characters |

Additional configuration:

- `ACCESS_TOKEN_EXPIRE_MINUTES`: session lifetime; default 480 minutes.
- `FRONTEND_ORIGINS`: comma-separated browser origins, such as `http://localhost:3000`.
- `DATABASE_URL`: optional private Postgres connection; schema migration is required before API startup.
- `STOCKSCOPE_DATA_DIR`: file-mode directory; defaults to root `data/`. Existing files are imported explicitly, never automatically.
- `SEC_USER_AGENT`: app name and actual contact email; SEC facts remain disabled until configured.
- `SEC_FACT_CONCEPTS`: optional concept allowlist to control storage (see `.env.example`).
- `STOCKSCOPE_IR_ENABLED` / `STOCKSCOPE_GDELT_ENABLED`: default `true`; set `false` to disable either provider.
- Frontend `NEXT_PUBLIC_API_URL`: backend URL, embedded at frontend **build time**.

Start both services:

```bash
npm run dev
```

Or start them separately:

```bash
npm run backend
npm run frontend
```

The frontend is at `http://localhost:3000`; the API is at `http://localhost:8000`; API documentation is at `/docs`. `npm run start` starts the API using `$PORT` (default 8000).

## Supabase setup and existing-data migration

Create a dedicated Supabase project on the Free plan. Copy the owner Postgres URI from **Connect** into `DATABASE_URL` in your private backend `.env` and Railway variables; never put it in Vercel or a `NEXT_PUBLIC_` variable. Use the direct connection when IPv6 is available, or the **Session pooler** on port 5432 for IPv4. Percent-encode reserved password characters and enable TLS with `sslmode=require` (`verify-full` with the supplied CA is stronger). Use the exact dashboard hostname and username. See [Supabase connection instructions](https://supabase.com/docs/guides/database/connecting-to-postgres).

For local setup, copy the Session pooler URI from **Connect**, then run the private interactive helper (replace `YOUR_PROJECT_REF` with the project reference):

```bash
venv/bin/python -m scripts.configure_database --project-ref YOUR_PROJECT_REF
```

Paste the URI at its hidden prompt, then enter the database password separately. The helper accepts a plain URI, quoted URI, `psql` command, or `DATABASE_URL=` assignment. It verifies the project, requires TLS, tests a read-only connection, and saves only after success. It preserves other `.env` entries and sets file permissions to owner-only. It does not apply migrations.

The backend uses SQLAlchemy/psycopg, not the Supabase browser client. No Supabase anon/publishable key or service-role API key is needed. Existing application roles are shared backend roles, not Supabase Auth accounts. The migration enables RLS with no public policies and revokes access from `PUBLIC`, `anon`, and `authenticated` on its tables. The owner connection can access the tables; keep that credential private.

Stop refreshes and the backend before migration/import. Back up the original `data/` directory and any existing database. Then, from the repository root with the private `.env` configured:

```bash
venv/bin/python -m alembic upgrade head
venv/bin/python -m scripts.import_research --data-dir data
venv/bin/python -m scripts.import_research --data-dir data --apply
```

The first import command is a dry run. `--apply` validates the full batch and writes it in one transaction, leaves input files untouched, and skips an identical batch already imported. Unsupported old social snapshots are skipped; invalid supported JSON aborts the entire batch. Re-importing a **changed** batch publishes those files as current snapshots, so only import deliberately before resuming refreshes. With `DATABASE_URL` set, the API reads only Postgres; files are not merged into the live view. Start the backend after import and confirm `/health` reports `storage: postgres`.

The initial migration creates companies, providers, article links/revisions, filings/revisions, reported financial facts, shared watchlists, notes, snapshot history, collection runs, and import batches. Watchlist and saved-research APIs are integrated; the notes table is groundwork, with no notes UI yet. Repeated refreshes preserve prior snapshot revisions and original source dates. Explicit admin stock deletion purges its research/history and runs, retaining shared articles linked to other stocks. Active refreshes block deletion.

Supabase currently lists **500 MB database storage** on Free and pauses inactive projects after one week; check [current limits](https://supabase.com/pricing). Start with a small watchlist. Full SEC histories plus normalized rows and snapshot revisions consume space; pagination only reduces response size. `SEC_FACT_CONCEPTS` can limit collected concepts while preserving their units and filing versions. There is no automatic retention/pruning yet. Monitor database size and export backups before cleanup or plan changes. If reverting to file mode, export new database research first: the original files will otherwise be stale.

## Article sources and primary evidence

| Source | Use in StockScope | Limits and interpretation |
|---|---|---|
| [Company investor relations](https://investor.nvidia.com/investor-resources/rss/default.aspx) | Official company releases; NVIDIA feed configured and live-checked | Company statements, separately labeled and excluded from news tone. Add reviewed feeds explicitly in `backend/data/source_feeds.json`. NVIDIA RSS terms permit individual informational, non-commercial use. |
| [GDELT DOC 2](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) | Discover article metadata and original publisher links for configured company aliases | Discovery time is not publication time. Conservative title matching reduces, but cannot eliminate, irrelevant matches. Public availability varies; live smoke timed out on October 14, 2026. |
| [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Company Facts plus the recent submissions table | Actual contact identity required. Preserve reporting periods, units, and amendments; do not treat every duration as a quarter or TTM. Older submission archive files are not fetched. |
| Existing Yahoo / Google News / publisher RSS / Finviz adapters | Additional headline coverage | Unofficial endpoints and feeds can change or fail. Provider outcomes and incomplete coverage remain visible. |

Collection stores metadata, summaries supplied by the feed, and original links; it does not scrape full article bodies. [NVIDIA RSS terms](https://www.nvidia.com/en-us/about-nvidia/rss/) and each publisher’s terms still apply. No full-text redistribution rights are implied. The active refresh does not use NewsAPI: its [free plan is development-only](https://newsapi.org/pricing). Legacy scripts are not the production collection path.

The new source adapters use response-size limits, public HTTPS targets, timeouts, and a shared collection budget. This budget limits request admission and transport timeouts; DNS and third-party library calls are not forcibly cancellable. Failed refreshes retain previous saved evidence, and partial refreshes retain only the newly collected providers in the current news snapshot (older revisions remain in Postgres). Provider failures are visible in job results. SEC data is cached per process and rate limited; multiple processes would need coordinated limits.

## Validation

```bash
npm test
npm run test:frontend
npm run lint
npm run build
```

The backend regression suite uses controlled fixtures for authentication, accounting, reporting periods, source dates, and collection outcomes. Frontend tests exercise session handling and request authentication. CI installs from the npm lockfile and runs backend tests, frontend tests, lint, and the production build. Passing these checks does not establish a profitable investment strategy.

Dependency check on October 14, 2026: `npm audit --omit=dev` reports no known production dependency vulnerabilities. The full audit reports seven high-severity development dependency entries stemming from a `braces` stack-exhaustion advisory in the Tailwind 3 / Next ESLint tooling chains. They remain open; resolving them requires a separately tested tooling migration. The lockfile includes patched React/Next versions and PostCSS dependency overrides. Recheck advisories before release.

## API overview

Login with `POST /api/auth/login` and a JSON password body. For subsequent calls use `Authorization: Bearer <access_token>`. Old `?password=` clients must be migrated; old browser sessions must sign in again.

| Route | Behavior |
|---|---|
| `GET /api/auth/session` | Read the current authenticated role without mutating data |
| `GET /api/stocks` | Shared saved-research watchlist |
| `POST /api/stocks/analyze` | Start an explicit refresh for requested sources |
| `GET /api/stocks/{symbol}/status` | Collection progress and terminal outcome |
| `GET /api/stocks/{symbol}` | Dated evidence and text-tone summary |
| `GET /api/stocks/{symbol}/investment-advice` | Research observations and limitations; no trading recommendation |
| `GET /api/stocks/{symbol}/quantitative` | Explicit unavailable response; no fabricated metrics |
| `GET /api/stocks/{symbol}/news` | Saved source articles |
| `GET /api/stocks/{symbol}/price-history` | Provider price history |
| `GET /api/fundamentals/{ticker}/sec-facts` | Saved primary facts with concept filtering and pagination; no collection on read |
| `GET /api/fundamentals/{ticker}` | Financial series, metrics, and reporting metadata |
| `POST /api/fundamentals/compare` | Company comparison |
| `POST /api/fundamentals/screener` | Screening with coverage counts |
| `GET /health` | Storage readiness; returns 503 if configured Postgres is unavailable |

## Deployment

The established production arrangement is Vercel for `stockscope-frontend/` and Railway for FastAPI. Keep development work on a branch and validate before promoting it.

For this authentication migration, configure the independent `SECRET_KEY` and all role passwords on the backend **before** deploying the backend code. Deploy the frontend and backend together in a coordinated release: the frontend requires bearer-token support, and the backend no longer accepts query passwords. Existing sessions must sign in again. Verify admin/guest behavior, refresh success/partial/failure, and source timestamps against the candidate deployment.

Vercel:

- Project root: `stockscope-frontend`.
- Install: `npm ci`; build: `npm run build`.
- Set `NEXT_PUBLIC_API_URL` to the Railway API URL before building.
- Node.js 22.

Railway:

- Uses `railway.json` and `Dockerfile.backend`.
- Set required authentication variables and `FRONTEND_ORIGINS` to the deployed frontend origin.
- Set `DATABASE_URL` after the migration/import below, or mount persistent file-mode storage.
- If `DATABASE_URL` uses the direct `db.<project-ref>.supabase.co` host, enable **Settings → Networking → Enable Outbound IPv6** on the Railway API service. Outbound IPv6 is opt-in. Alternatively use a verified Supabase Session pooler URI.
- Run one API worker/replica and avoid overlapping deployments; persistent status is not a distributed queue.

For local container testing, configure `.env`, then use `docker compose up --build`. The Docker build context excludes secrets, environments, generated research, and dependency directories. The frontend API URL is supplied as a build argument.

No automatic trade execution is implemented. No provider subscription or brokerage connection is required for the current research workflow. Free data access does not automatically grant redistribution or display rights; check the chosen provider's terms before sharing a deployment.

## Next implementation stages

1. Connect the prepared Supabase schema, import the existing research, and verify a coordinated preview deployment. Add storage retention controls and a durable worker queue before scaling.
2. Build long-term research notes, valuation scenarios, actual holdings/contributions, and benchmark-relative performance.
3. Add a separate paper-trading journal with planned risk, execution costs, and drawdowns.
4. Evaluate any predictive strategy on point-in-time data and unseen periods before exposing predictive claims.

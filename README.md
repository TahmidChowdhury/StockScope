# StockScope

StockScope is a personal stock-research workspace for a long-term investing core and a separate trading-learning allocation. It combines company fundamentals, comparison, a curated stock screener, dated news, and links to original SEC filings.

## Current behavior

- **Fundamentals:** quarterly and trailing-twelve-month financials from yfinance, with missing values and calculation limitations exposed. Free cash flow requires both operating cash flow and capital expenditure. Growth figures identify their reporting basis.
- **Comparison and screening:** compare companies and filter a **curated 110-symbol universe**, or supply a custom universe. This is not a complete/current S&P 500 constituent list. Coverage counts distinguish failures, missing data, matches, and displayed results.
- **SEC reported facts:** an explicit refresh collects primary financial facts and recent filings. The fundamentals page exposes periods, units, filing versions, and original links alongside the existing yfinance metrics; SEC facts do not silently replace TTM calculations.
- **Research:** news text-tone scores describe saved articles; SEC filing events and company press releases are unscored. Publication dates are distinct from summary-generation dates, and unknown dates stay unknown.
- **Disclosures:** House and Senate transaction snapshots refresh automatically, with original filing links, publisher coverage, amendment versions, and StockScope observation times. Search disclosures, open company research, and test a defined following rule.
- **Refresh:** company research refreshes explicitly, with completion, partial-result, and failure status. Disclosure collection runs on its own schedule. Merely opening saved research does not imply it was refreshed.
- **Shared watchlist:** saved analyzed symbols are shared across authenticated roles. This is not a holdings ledger or a measure of actual portfolio returns. Dashboard evidence counts include news and filing records, not just distinct articles.
- **Workspace navigation:** dashboard, company research, financials, comparison, screening, and paper experiments share a responsive shell and watchlist. Saved backtests and paper portfolios have direct URLs. Screener selections carry into Compare; missing data and coverage remain visible.
- **Browser drafts:** screening inputs/results/selections, comparison inputs/results, trading forms, per-portfolio order drafts, company valuation assumptions, and tone annotations/completed reports restore after refresh or return visits. Drafts use local browser storage separated by API connection and individual account (or legacy access role before owner setup), without cross-device sync. Credentials remain in session storage. Saved snapshots retain their collection dates and do not trigger fresh screening, model inference, or trading actions. Clear controls affect only their local workspace; blocked or full browser storage displays an unsaved warning.
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
        |-- Congressional disclosures: attributed, versioned public dataset snapshots
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
- `STOCKSCOPE_DATA_DIR`: file-mode directory; defaults to root `data/`. Existing research files are imported into Postgres explicitly.
- `DISCLOSURE_COLLECTION_ENABLED`: defaults to enabled when `DATABASE_URL` is set. Explicit `false` pauses disclosure collection; explicit `true` also permits local file mode.
- `DISCLOSURE_COLLECTION_INTERVAL_HOURS`: whole hours from 1–24, default 6. Failed attempts retry sooner.
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
| [MarketWatch Top Stories](https://feeds.content.dowjones.io/public/rss/mw_topstories), [CNBC Finance](https://www.cnbc.com/id/10000664/device/rss/rss.html), [NPR Business](https://feeds.npr.org/1006/rss.xml) | No-key publisher feeds, filtered using ticker boundaries and configured company aliases | Feeds were checked on October 14, 2026. The old MarketWatch endpoint was stale and the legacy Reuters RSS endpoint was unreachable; neither is used. A working feed can have no stories about the selected company. |
| [Marketaux](https://www.marketaux.com/pricing) (not integrated) | Possible structured company/entity news alternative | Free tier: 100 requests/day, three articles/request; needs an API key. [Terms](https://www.marketaux.com/tos) limit use, including commercial activity. Free access does not establish public redistribution rights. |

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

## Paper portfolios, backtesting, and Congress research

Open **Paper & tests** (`/trading`) in the sidebar. This is a shared research workspace,
not a brokerage connection. Admin can create portfolios, submit/cancel paper orders,
refresh valuations, run saved backtests, and import disclosures. Demo and guest can
read and export saved results. Role passwords do not provide individual account ownership.

Saved records open at `/trading/backtests/{run_id}` and
`/trading/portfolios/{portfolio_id}`. These URLs load the database record after
refresh or sign-in and work with browser Back/Forward. Opening a saved record
does not rerun it. Malformed IDs and unavailable records show explicit missing-record
states. `/trading?tab=backtest&symbols=AAPL,MSFT` remains a research handoff;
refreshing that URL preserves later draft edits, while a new Compare handoff
updates the symbols without discarding other experiment inputs.

**Before deploying this change**, run `venv/bin/python -m alembic upgrade head` with
an appropriate database backup. Revision `20261015_02` adds `trading_documents`,
sealed with RLS and anonymous-role privilege revocations. Do not run the migration
against a live deployment still expecting the previous schema version; coordinate
backend replacement. No DDL runs at application startup. Without `DATABASE_URL`,
atomic files under `STOCKSCOPE_DATA_DIR/trading/` are authoritative. Configured
Postgres failures never fall back to files. Portfolio writes serialize; a refresh
that races a new order is rejected so it can be retried without losing the order.

### Paper accounting

- Starting cash and costs are fixed at portfolio creation. Buys use a cash budget
  including costs; sales close the entire symbol. No leverage or shorting.
- A thesis and server submission timestamp are recorded before outcomes exist.
  Client order IDs make retries idempotent. Same-day queued orders can be cancelled;
  the cancellation remains in the journal. Older orders must be evaluated.
- Orders are eligible at the first observed session open **strictly after** their
  submission date in America/New_York. Even a premarket submission waits until a
  later date. Refresh uses daily sessions before today, so it is intentionally
  slower than a live broker simulator. Opening a saved portfolio does not refresh it.
- Cash/position checks occur at execution. Insufficient budgets, unmatched sells,
  and position caps appear as explicit rejected signals; unexecuted end-of-window
  signals remain pending.
- Paper refreshes freeze observed bars and append new dates. Previously recorded
  simulated fills do not change when the data provider revises historical prices.
  Failed or concurrently outdated refreshes preserve the previous result.

### Historical experiments

Three strategies are available: equal-starting-budget buy-and-hold (without
rebalancing), a one-symbol fast/slow moving-average rule, and copying one member's
imported Congress disclosures. SMA signals use adjusted closes through the prior
session and execute at the following open. There is no parameter optimization or
automatic model selection. Use separate date ranges for exploratory and unseen
validation tests, and repeat with less favorable cost/delay assumptions.

The engine supports USD equities and ETFs, fractional shares, cash dividends,
ordinary splits, and daily open/close observations. Yahoo historical OHLC is
split-adjusted: the adapter reverses later split factors to reconstruct as-traded
prices, then the ledger adjusts held shares on split dates. Stock/benchmark price
observations, costs, resolved symbols, source disclosures, an engine version, and
a SHA-256 of the input prices are saved with each run and exported as JSON. This
supports inspecting and replaying a saved experiment without fetching new prices.
The original observations and order history can also be exported for paper portfolios.

Slippage plus half the configured full bid-ask spread shifts every fill against
the strategy; each fill also incurs the configured flat commission. The benchmark
buys at the first test-session open with the same starting cash and entry costs,
then holds and accumulates dividends as cash. Ending values mark open positions
at close; no hypothetical liquidation fee is deducted. Excess return is the
strategy's cumulative return minus the benchmark's cumulative return in percentage
points, not risk-adjusted alpha. Cash yields zero. CAGR is shown only for observed
periods of at least 365 days. Drawdowns include the initial cash value and entry costs.

Missing symbol data on any benchmark session aborts a test; symbols are never
silently dropped or forward-filled. The benchmark's observed dates supply the
session calendar (not an independently verified exchange calendar). The UI exposes
the actual valuation date. A missing session in all supplied series may therefore
remain undetected. Limits: 20 strategy symbols, ten years per test, 1,000 paper
orders per portfolio, and 1,000 eligible Congress signals per test. Provider calls
are bounded by per-symbol timeouts but can still take minutes for larger universes.

These simulations do not model taxes, financing, cash interest, dividend payment-date
timing, market impact beyond configured slippage, intraday stops, special corporate
actions, or delisting proceeds. Dividends accrue on ex-date, which can make cash
available earlier than a real broker would. Yahoo data is unofficial and revisable;
metadata must identify USD stock/ETF instruments. Current-stock and famous-member
selection can introduce survivorship and selection bias. Passing tests validates
accounting and timing rules, not profitability.

### Automatic Congress disclosures

The **Disclosures** workspace at `/disclosures` connects collected and imported evidence to
company research and historical experiments. Search transactions or filter by
member, ticker, and buy/sell activity; filters and pagination live in the URL.
Member cards summarize covered transactions across all dates, not current
holdings or investment returns. Feed totals describe all matching records before
pagination. Company overviews show the five latest covered disclosures for that
ticker. A member's **Test following this member** action opens a prefilled Congress
experiment; review its dates, costs, and execution rules before running it.

The automatic source is [Austin Starks' congressional-stock-trades dataset](https://huggingface.co/datasets/austin-starks/congressional-stock-trades),
a third-party normalization of official House and Senate reports. It needs no API
key or paid subscription. Each refresh pins a dataset revision, verifies manifest
checksums, and reads the current/previous calendar-year shards plus years already
collected, so older captured reports continue to be checked for changes. Coverage,
excluded rows, publisher timestamps, and original report links remain visible;
the feed is neither complete nor real time. StockScope does not scrape the
disclosure portals during these refreshes.

The publisher labels the data `us-congressional-disclosure-restrictions`,
not CC0 or unrestricted open data. Its [data-use notice](https://huggingface.co/datasets/austin-starks/congressional-stock-trades/blob/main/LICENSE_DATA.md)
describes restrictions on commercial use, credit-rating decisions, and
solicitation. This integration does not establish permission to monetize or
redistribute the reports for every purpose.

With `DATABASE_URL` configured, API startup automatically schedules collection.
An empty database hydrates on the first check; later attempts respect the saved
due time, normally every six hours. The existing always-running Railway API owns
this schedule, so no separate cron service or GitHub secret is required. The
schedule checks compact status every minute, including earlier retries requested
by a manual refresh, without reloading all transaction rows.

Admins can use **Refresh disclosures** in the workspace or run the same collector
from the repository root with the private backend `.env` configured:

```bash
# Run only if the saved schedule is due:
venv/bin/python -m scripts.collect_disclosures
# Hydrate or refresh the current/previous-year history immediately:
venv/bin/python -m scripts.collect_disclosures --force
```

`--force` bypasses the due time, not an active lease or disabled configuration.
Set `DISCLOSURE_COLLECTION_ENABLED=false` and restart/redeploy the backend to
pause collection; saved data remains available. For local file mode, explicitly
set it to `true`. A future dedicated cron can run the same one-shot command, but
the current API service must stay an always-running web service.

Automatic evidence lives in the separate `congress-feed` document in
`trading_documents`; existing CSV imports remain in `congress`. Updates are
atomic, with a persisted 15-minute lease preventing overlapping writers. Each
transaction version keeps its first-observed timestamp. Later versions are
retained, and a source-supplied supersession is recorded without rewriting the
earlier economic fields. A changed existing version, invalid snapshot, or failed
download leaves the previous evidence intact and surfaces a status message.
Failures retry after 5 minutes, doubling to a maximum of one hour. Interrupted
workers recover after their lease expires. History is not pruned automatically;
the collector stops before exceeding 50,000 retained versions. Older captured
years remain stored and are revalidated while available in the source. A missing
previously collected version in a fetched year fails the refresh for review;
it cannot silently remain current under a newer source revision.

The publisher's availability dates estimate the end of the filing day in New
York; they are not verified publication timestamps. Automatic backtests therefore
use the date StockScope first observed the original event by default. Backfilling
old reports does not create earlier signals. The explicit exploratory option
`allow_estimated_disclosure_dates` permits historical filing-day estimates and
labels the resulting look-ahead risk. Tests copy an eligible original version
once; later corrections are not new trades. Saved experiments retain their
selected disclosure versions and source snapshot metadata.

### Manual Congress imports

Download the CSV header template from the Disclosure imports tab and supply
source-backed transaction rows. Required columns in order:

```csv
disclosure_id,member,owner,symbol,side,transaction_date,available_date,asset_type,amount_range,source_url
```

`disclosure_id` identifies one transaction row, not an entire multi-row report;
the `cst:` prefix is reserved for automatically collected records.
Use ISO dates (`YYYY-MM-DD`); `side` is `buy` or `sell`; `asset_type` is `stock`,
`etf`, `option`, or `other`. Every field is required. `source_url` must be HTTPS;
URLs are retained as evidence links and are not fetched by the importer. Quote
CSV values containing commas. Dates, classifications, and public availability are
user-supplied and are not independently verified. A filing date is not necessarily
the date the public could access it. Verify against the
[House portal](https://disclosures-clerk.house.gov/FinancialDisclosure) or
[Senate portal](https://efdsearch.senate.gov/search/).

Imports validate the whole batch before saving. Identical IDs/content are skipped;
conflicting IDs reject the batch and cannot rewrite prior history. Amendments are
not supported: do not upload a correction as a new trade. Maximum import size is
2 MB/5,000 rows, and the manual-import store holds up to 10,000 disclosures.

Congress tests start with cash and use only records with the selected signal dates inside
the requested window. An optional extra calendar-day delay precedes the next-open
rule. Each buy uses a fixed fraction of initial cash, capped by available cash and
the configured symbol weight at execution. A sale exits the copied symbol. Owners
for the selected member are pooled. Reported dollar ranges do not identify exact
allocations; partial sales, options, earlier holdings, and amendments are not
replicated. Excluded option/other rows are visible. This measures a defined copying
rule against a benchmark, not a reconstruction of a politician's actual return.

Trading API routes live under `/api/trading`: `portfolios`, portfolio `orders`,
`refresh`, and `export`; `backtests` and per-run `export`; `congress`,
`congress/template`, and `congress/import`. Collection health is available at
`GET /congress/collection`; admins can request `POST /congress/collection/refresh`.
All require bearer authentication.

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
- Disclosure hydration and scheduled refreshes start automatically with `DATABASE_URL`; no additional cron service is required. Set `DISCLOSURE_COLLECTION_ENABLED=false` to pause them. Check the Disclosures status card after deployment for source freshness, retained version count, and the next attempt.

For local container testing, configure `.env`, then use `docker compose up --build`. The Docker build context excludes secrets, environments, generated research, and dependency directories. The frontend API URL is supplied as a build argument.

No automatic trade execution is implemented. No provider subscription or brokerage connection is required for the current research workflow. Free data access does not automatically grant redistribution or display rights; check the chosen provider's terms before sharing a deployment.

## Local tone research, valuation and risk

Company research includes a **Tone lab** tab. VADER remains the production news-tone method. The lab compares it with two allowlisted local research checkpoints: FinSense ModernBERT and ModernFinBERT. Every challenger result includes its pinned revision, text coverage, truncation and model probabilities. Softmax probabilities are uncalibrated tone estimates, not probabilities of investment success. SEC events, company releases, empty text and unsupported/unknown languages are excluded.

Install the optional CPU research runtime, then explicitly cache the models (about 1.2 GB of model weights):

```sh
venv/bin/python -m pip install -r requirements-sentiment.txt
venv/bin/python -m scripts.cache_sentiment_models
venv/bin/python -m scripts.cache_sentiment_models --download
```

The default model cache is `.cache/huggingface` inside this repository, excluded from Git. `STOCKSCOPE_HF_CACHE` can select another cache. Web requests use cached safetensors only, prohibit remote model code and never download weights. Comparison is bounded to 30 saved news records and one active inference job. All research endpoints require the existing bearer session.

The production Docker image installs the CPU-only tone runtime and bakes both pinned model revisions into `/opt/stockscope/models`. It verifies the cache and runs actual inference in offline mode during the build; incomplete downloads or incompatible models fail the build. Runtime model downloads stay disabled, and no model token or persistent model volume is needed. Allow at least 3 GiB RAM for inference alongside API and collection work. `INSTALL_SENTIMENT_MODELS=false` is an explicit build-time opt-out for deployments that only need the base app. Locally, `python -m scripts.cache_sentiment_models --verify --smoke-test` checks the same cache without downloading.

FinSense's author-declared weight license is Apache-2.0, but its Financial PhraseBank training data carries noncommercial terms. ModernFinBERT is author-tagged Apache-2.0 with incomplete training-source disclosure. These are research candidates; the app does not certify commercial rights or claim either model improves investment performance. See the exact model-card links in the lab.

For a reproducible comparison and explicit annotation workflow:

```sh
venv/bin/python -m scripts.benchmark_sentiment AAPL --limit 12 --template /tmp/aapl-labels.json
venv/bin/python -m scripts.benchmark_sentiment AAPL --limit 12 --compare --output /tmp/aapl-tone-comparison.json
# Fill explicit positive/neutral/negative labels in the template, then evaluate:
venv/bin/python -m scripts.benchmark_sentiment AAPL --limit 12 --compare --labels /tmp/aapl-labels.json --output /tmp/aapl-tone-evaluation.json
```

Templates start with null labels. Accuracy and macro-F1 are unavailable until annotations are supplied; model agreement is not ground truth. Sample identifiers and text hashes reject annotations for changed text. These commands read saved evidence without replacing production scores or collecting new articles.

**Business quality & valuation** appears in company Overview and Financials. It separates operating metrics from price-based ratios, retaining dates, unknown inputs and provider-declared financial currency. Cross-source ratios require matching supported currencies, a recent timestamped quote and dated four-quarter financials. Provider operating cash flow minus CapEx is not treated as verified FCFF or FCFE. Editable equity cash-flow scenarios use the user's explicit FCFE and share assumptions with cash-flow multiples; they are illustrative, save as a local company draft, and are not DCF forecasts or buy/sell ratings. Refreshed evidence preserves those assumptions; Reset uses current quote defaults. Tone annotations are tied to article IDs and text hashes. Saved tone reports are dated snapshots checked against current samples before restoration; changed samples withhold incompatible reports and labels while preserving them for local export.

Saved backtests now include a **Risk profile** from QuantStats 0.0.77, the release pinned for this app's Python 3.9 environment. It uses the saved strategy and benchmark equity curves, including initial cash to first saved close. Sharpe/Sortino use zero risk-free rate, 252 sessions per year and the documented sample/downside estimators. Undefined ratios remain unavailable; measured zero volatility remains zero. Drawdown duration uses observed underwater sessions and calendar time, with recovery sessions excluded. Saved experiments and their data hashes remain unchanged.

New read-only routes: `GET /api/valuation/{symbol}`, `GET /api/sentiment-lab/{symbol}`, `GET /api/sentiment-lab/{symbol}/labels`, and `GET /api/trading/backtests/{run_id}/risk`. The lab's `POST /api/sentiment-lab/{symbol}/evaluate` compares explicit supplied annotations without saving changes. SEC collection stays disabled unless configured separately.

## Next implementation stages

1. Verify backup restoration and a coordinated deployed preview of the connected Supabase schema. Add storage retention controls and a durable worker queue before scaling.
2. Add long-term research notes, account-based draft sync, actual holdings/contributions, and further benchmark-relative performance views.
3. Extend the paper journal with precommitted risk plans and independently verified exchange-session coverage.
4. Validate strategies on unseen periods and licensed point-in-time data; add a paid Congress feed only after verifying its coverage and access terms.

### Private friends workspace and conservative refreshes

Run `python -m alembic upgrade head` and `python -m alembic -n workspace upgrade head`
with the backend environment before starting this version. The workspace migration
is additive and uses its own version table: it does not change the research schema
version expected by the currently deployed API. PostgreSQL RLS is enabled and access
is revoked from public, anon, and authenticated roles on the new tables. Only the
trusted backend database connection accesses them.

Open **Your account** (or the login screen on a fresh browser) and create the owner
account using an email, a new passphrase of at least 12 characters, and the existing
`ADMIN_PASSWORD`. There is no public signup. Once setup completes, shared passwords
and previously issued shared-role tokens no longer grant access in this API version.
Migrate every running backend to this version before inviting friends: an old API
process still implements the old shared-password policy.

**Access & resources** lets an administrator create a three-day single-use invitation
for a specific email, change roles, suspend/restore accounts, revoke pending links,
and create password-reset links. Share links privately yourself; the application does
not send mail or require an email service. Link possession plus the addressed email
allows acceptance, so do not post links publicly. Invite tokens are stored only as
SHA-256 hashes. Passwords use salted scrypt (N=2^17, r=8, p=1). Sessions expire after
8 hours by default; each protected request checks the user's current status, role,
and session version. Signing out, resetting a password, and access changes invalidate
existing sessions. Sessions remain in tab sessionStorage; production must use HTTPS.
A database is required. `ALLOW_LEGACY_FILE_AUTH=true` is an explicit offline development
escape hatch and must remain false for the friends workspace.

Personal lists are scoped to their owner on every API operation. A user can keep
20 lists of 250 symbols; the workspace is capped at 25 accounts/pending invitations.
Unfollowing a symbol or deleting a list does not delete shared research. Home shows
six companies, pins first; the sidebar shows at most five pins. The library pages
25 rows at a time. Browser research drafts are keyed by account as well as workspace.

Opening the watchlist uses compact relational summaries, with no remote market-data
calls or large snapshot downloads. The browser rechecks this saved list every five
minutes while visible. Company fundamentals use a shared six-hour cache with durable
last-good results and coalesced requests. Screens read this cache only; opening an
individual company's Financials view populates it. Screens expose partial coverage;
they do not imply all companies were freshly fetched. Watchlist summaries do not
pretend to be live quotes. Original source and retrieval dates remain visible.

All active requests through the SEC/news/disclosure collectors and yfinance transport
use persistent shared UTC daily budgets. Defaults: Yahoo 100 actual HTTP attempts,
SEC 200, Google/Finviz/other feeds 30 each, disclosures 10, research jobs 12. Manual
research collection has a six-hour per-symbol cooldown, including failed jobs. Budgets
can be lowered via `.env`; raising the hard ceilings requires an intentional code
change. NewsAPI is disabled even if a key is present. HTTP 429/403/503 responses start
a cooldown of at least one hour and honor longer Retry-After values. HTTP redirects
are not followed implicitly; the disclosure downloader validates and budgets each hop.
The supported deployment remains **one API process**. Separate old deployments or
external uses of the same provider credentials are outside these counters.

These ceilings are an application safeguard, not a guarantee of upstream availability
or a provider's unpublished limits. The app never upgrades a plan or automatically
buys quota. When requests are blocked, saved research remains available. Disclosure
collection retains its existing six-hour schedule and shared database lease; no
additional automatic market-wide crawler has been enabled. Local verification starts
the API with `DISCLOSURE_COLLECTION_ENABLED=false` to avoid duplicating the hosted
scheduler. Check **Access & resources** to inspect actual usage.

The disclosure browser also filters and paginates the saved PostgreSQL JSON on the
server, returning only the requested page plus compact summaries. It preserves the
same latest-amendment selection and manual/automatic duplicate suppression as the
Python reference. `backend/tests/test_disclosure_projection.py` checks parity using
a temporary table when `STOCKSCOPE_TEST_DATABASE_URL` is provided; it does not replace
or modify saved disclosure data.

Mobile disclosure rows show the ticker, activity, reported range, and trade date first.
Animate UI details reveal the owner, filing/public date, observation date, and original
evidence; desktop keeps this evidence visible. Filters stack at phone widths and active
filters can be removed individually. Company previews use the same record layout.

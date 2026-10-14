#!/bin/bash
set -euo pipefail

# Read-only release guidance. This helper never switches branches or deploys.
cat <<'GUIDE'
StockScope deployment

1. Run the local checks:
   npm test
   npm run test:frontend
   npm run lint
   npm run build

2. Configure Railway before releasing the authentication migration:
   ADMIN_PASSWORD, DEMO_PASSWORD, GUEST_PASSWORD
   SECRET_KEY: an independent random secret of at least 32 characters
   FRONTEND_ORIGINS: the Vercel frontend origin
   DATABASE_URL: Supabase Postgres URI with TLS (backend only)
   Direct Supabase URI: enable Railway Settings > Networking > Outbound IPv6.
   SEC_USER_AGENT: app name plus your actual contact email to enable SEC facts
   Remove legacy STOCKSCOPE_PASSWORD after configuring the three role passwords.
   The Supabase schema/import is already complete for this project.
   For future schema changes, migrate explicitly before restarting the API.

3. Configure Vercel:
   Root directory: stockscope-frontend
   Node.js: 22
   Install: npm ci
   Build: npm run build
   NEXT_PUBLIC_API_URL: the Railway backend URL (set before build)

4. Validate a candidate backend/frontend pair, then promote together.
   Existing sessions must sign in again. Query-string passwords are unsupported.
   Check all roles, explicit source refresh, partial/failure results, and dates.

Run one API worker and one replica. Job outcomes are persisted, but work still
runs in that process. Stop the old instance before the replacement starts:
startup marks unfinished runs failed. Do not use overlapping deployment instances.

Login still uses shared app passwords (admin/demo/guest), not Supabase Auth.
Admin can delete research and clear caches. Demo and guest currently both read
and refresh the shared workspace. There are no individual user accounts yet.
See README.md for details.
GUIDE

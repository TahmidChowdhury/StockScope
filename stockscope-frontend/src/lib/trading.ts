import { apiFetch } from './api'

export interface Costs { slippage_bps: number; spread_bps: number; commission: number }
export interface Metrics {
  ending_equity: number; total_return: number; max_drawdown: number; cagr: number | null
  benchmark_return: number; excess_return: number; total_costs: number; benchmark_costs: number
  dividends: number; realized_pnl: number; fill_count: number
}
export interface Order {
  id: string; symbol: string; side: 'buy' | 'sell'; budget: number; signal_date: string
  thesis?: string; submitted_at?: string; cancelled_at?: string
}
export interface Fill extends Order {
  execution_date: string; shares: number; price: number; cost: number; realized_pnl: number | null
  source_url?: string
}
export interface Result {
  metrics: Metrics; curve: { date: string; equity: number; benchmark: number; cash: number }[]
  fills: Fill[]; rejected: (Order & { reason: string; execution_date: string })[]; pending: Order[]
  positions: { symbol: string; shares: number; cost_basis: number; price: number; market_value: number; unrealized_pnl: number }[]
  cash: number; as_of: string; assumptions: string[]; exclusions?: { disclosure_id: string; reason: string }[]
}
export interface Portfolio {
  id: string; name: string; initial_cash: number; benchmark: string; costs: Costs; created_at: string
  orders: Order[]; result: Result | null; refreshed_at?: string
}
export interface Run {
  id: string; name?: string | null; strategy: string; start: string; end: string; benchmark: string; initial_cash: number
  member: string; result: Result; data_sha256: string; created_at: string; costs: Costs
  allow_estimated_disclosure_dates?: boolean
}
export interface Summary {
  id: string; name?: string | null; strategy?: string; start?: string; end?: string; member?: string; created_at: string
  metrics?: Metrics; as_of?: string
}
export interface Disclosure {
  disclosure_id: string; member: string; owner: string; symbol: string; side: string
  transaction_date: string; available_date: string; lag_days: number; amount_range: string
  source_url: string; asset_type: string
  source?: 'congressional_stock_trades' | 'user_supplied_csv'; chamber?: string; filed_date?: string
  availability_basis?: 'filing_day_estimate'; first_seen_at?: string; observed_at?: string
  is_amendment?: boolean; version?: number; partial_sale?: boolean; asset_description?: string
}
export interface DisclosureCollection {
  enabled: boolean
  state: 'disabled' | 'idle' | 'running' | 'completed' | 'failed' | 'interrupted'
  last_attempt: string | null; last_success: string | null; next_run: string | null; last_error: string | null
  row_count: number; counts?: Record<string, number | boolean>; interval_hours?: number
  source: {
    provider?: string; source_url?: string; license_url?: string; revision?: string
    source_checked_at?: string; generated_at?: string; years?: number[]
    source_counts?: Record<string, number>; excluded_counts?: Record<string, number>
    coverage_start?: string; coverage_end?: string; files?: unknown[]
  } | null
}
export interface CongressData {
  records: Disclosure[]; total: number; offset: number; members: string[]
  last_import: { inserted: number; duplicates: number; imported_at: string } | null
}
export interface DisclosureSummary {
  total: number; buys: number; sells: number; symbol_count: number; member_count: number
  latest_available_date: string | null; average_lag_days: number | null
}
export interface DisclosureResearch extends CongressData {
  symbols: string[]; summary: DisclosureSummary; filtered_summary: DisclosureSummary
  member_profiles: (DisclosureSummary & { member: string })[]
  mode: 'csv_import' | 'automatic_and_csv'; live_feed_connected: boolean
  collection?: DisclosureCollection
  provenance: { source: 'user_supplied_csv' | 'mixed_disclosures'; dates_verified: false; limitations: string[] }
}

/** Expand provider codes while preserving free-text owners in older CSV imports. */
export function disclosureOwnerLabel(value?: string): string {
  const owner = value?.trim() || ''
  const labels: Record<string, string> = {
    self: 'Member', member: 'Member', spouse: 'Spouse', dependent_child: 'Dependent child',
    dependent: 'Dependent', joint: 'Joint', not_indicated: 'Not reported', not_reported: 'Not reported',
    unknown: 'Not reported', 'n/a': 'Not reported',
  }
  const key = owner.toLowerCase().replace(/[\s-]+/g, '_')
  return Object.prototype.hasOwnProperty.call(labels, key) ? labels[key] : owner || 'Not reported'
}

export function disclosureChamberLabel(value?: string): string {
  const chamber = value?.trim() || ''
  return chamber.toLowerCase() === 'house' ? 'House' : chamber.toLowerCase() === 'senate' ? 'Senate' : chamber
}

/** Older experiments have no name; retain a readable strategy label for them. */
export function backtestName(run: Pick<Summary, 'name' | 'strategy' | 'member'>): string {
  return run.name?.trim() || (run.strategy === 'congress'
    ? `Congress · ${run.member}`
    : run.strategy === 'sma' ? 'Moving average experiment' : 'Buy and hold experiment')
}

/** Accept only a complete, bounded universe when research passes symbols to a test. */
export function backtestSymbols(value: string | null): string[] | null {
  if (!value) return null
  const symbols = [...new Set(value.split(',').map((symbol) => symbol.trim().toUpperCase()).filter(Boolean))]
  return symbols.length >= 1 && symbols.length <= 20 && symbols.every((symbol) => /^[A-Z][A-Z0-9.-]{0,9}$/.test(symbol))
    ? symbols : null
}

export async function tradingRequest<T>(path: string, body?: unknown, method?: string, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(`/api/trading${path}`, {
    signal,
    method: method || (body === undefined ? 'GET' : 'POST'),
    ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const payload = await response.json()
      if (typeof payload.detail === 'string') message = payload.detail
      else if (Array.isArray(payload.detail)) message = payload.detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.slice(1).join('.') || 'Input'}: ${item.msg || 'Invalid value'}`).join('; ')
    } catch { /* retain HTTP status if a proxy returned non-JSON */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export async function downloadTradingFile(path: string, filename: string) {
  const response = await apiFetch(`/api/trading${path}`)
  if (!response.ok) throw new Error(`Download failed (${response.status})`)
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Timestamps are displayed in the market/accounting timezone; date-only bars stay unchanged. */
export function tradingDate(timestamp: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date(timestamp))
}

/** Only orders submitted on the current New York date can still be cancelled. */
export function canCancelPaperOrder(order: Pick<Order, 'signal_date' | 'cancelled_at'>, now = new Date()): boolean {
  return !order.cancelled_at && order.signal_date === tradingDate(now.toISOString())
}

/** Submit the dates currently entered in the native form; never substitute stale defaults. */
export function backtestDates(form: Pick<FormData, 'get'>): { start: string; end: string } {
  const start = form.get('start')
  const end = form.get('end')
  const valid = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value
  if (!valid(start) || !valid(end) || end <= start) throw new Error('Enter valid start and end dates, with the end after the start.')
  return { start, end }
}

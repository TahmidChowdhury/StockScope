import type { FundamentalsTTM, ScreenerResponse } from '@/types'

export const screenFilterKeys = ['min_revenue_growth_yoy', 'min_fcf_growth_yoy', 'min_margin_growth_yoy_pp', 'min_ebitda_growth_yoy', 'max_debt_to_cash'] as const
export const screenSortKeys = ['revenue_growth_yoy', 'fcf_growth_yoy', 'ebitda_growth_yoy', 'fcf_margin_ttm', 'operating_margin_ttm', 'revenue_ttm'] as const
export interface ScreenCriteria {
  filters: Record<string, string>
  universe: 'curated' | 'watchlist' | 'custom'
  custom: string
  sort: string
  direction: 'asc' | 'desc'
  limit: string
}
export interface ScreenSnapshot {
  criteria: ScreenCriteria
  universeName: string
  data: Pick<ScreenerResponse, 'results' | 'total_attempted' | 'total_evaluated' | 'total_matches' | 'total_failed' | 'total_insufficient' | 'universe_name'>
  capturedAt: string
}
export interface ScreenerDraft {
  criteria: ScreenCriteria
  snapshot: ScreenSnapshot | null
  selected: string[]
  requestId: string | null
}
export interface ComparisonSnapshot {
  tickers: string[]
  results: FundamentalsTTM[]
  capturedAt: string
}
export interface CompareDraft {
  tickers: string[]
  snapshots: ComparisonSnapshot[]
  requestId: string | null
}

export const defaultScreenCriteria: ScreenCriteria = {
  filters: Object.fromEntries(screenFilterKeys.map((key) => [key, ''])),
  universe: 'curated', custom: '', sort: 'revenue_growth_yoy', direction: 'desc', limit: '50',
}
export const initialScreenerDraft: ScreenerDraft = { criteria: defaultScreenCriteria, snapshot: null, selected: [], requestId: null }
export const initialCompareDraft: CompareDraft = { tickers: [], snapshots: [], requestId: null }

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const short = (value: unknown, max: number): value is string => typeof value === 'string' && value.length <= max
const date = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value))
const timestamp = (value: unknown): value is string => short(value, 40) && Number.isFinite(Date.parse(value))
const symbol = (value: unknown): value is string => typeof value === 'string' && /^[A-Z][A-Z0-9-]{0,9}$/.test(value)
const symbols = (value: unknown): value is string[] => Array.isArray(value) && value.length <= 20 && value.every(symbol) && new Set(value).size === value.length
const requestId = (value: unknown) => value === null || (short(value, 40) && /^[a-f0-9-]+$/i.test(value))
const keysOnly = (value: Record<string, unknown>, keys: readonly string[]) => Object.keys(value).every((key) => keys.includes(key))

export function isScreenCriteria(value: unknown): value is ScreenCriteria {
  return record(value) && keysOnly(value, ['filters', 'universe', 'custom', 'sort', 'direction', 'limit']) &&
    record(value.filters) && keysOnly(value.filters, screenFilterKeys) && screenFilterKeys.every((key) => short((value.filters as Record<string, unknown>)[key], 40)) &&
    ['curated', 'watchlist', 'custom'].includes(String(value.universe)) && short(value.custom, 6000) &&
    screenSortKeys.includes(value.sort as typeof screenSortKeys[number]) && ['asc', 'desc'].includes(String(value.direction)) && short(value.limit, 8)
}

const amountKeys = ['revenue_ttm', 'operating_income_ttm', 'operating_margin_ttm', 'fcf_ttm', 'fcf_margin_ttm', 'ebitda_ttm', 'revenue_growth_yoy', 'fcf_growth_yoy', 'ebitda_growth_yoy', 'margin_growth_yoy_pp', 'debt_to_cash'] as const
const growthKeys = ['revenue_growth_yoy', 'fcf_growth_yoy', 'ebitda_growth_yoy']
const periodKeys = ['revenue_ttm', 'fcf_ttm', 'ebitda_ttm', 'operating_income_ttm']

/** Only displayed observations and their provenance enter a browser draft. */
export function draftFinancialRows(rows: FundamentalsTTM[]): FundamentalsTTM[] {
  return rows.map((row) => {
    const result: FundamentalsTTM = { ticker: row.ticker, insufficient_data: row.insufficient_data }
    for (const key of amountKeys) if (row[key] === null || typeof row[key] === 'number') result[key] = row[key]
    const growth = Object.fromEntries(growthKeys.filter((key) => row.growth_metadata?.[key]).map((key) => {
      const item = row.growth_metadata![key]
      return [key, { basis: item.basis, status: item.status, ...(item.current_period_end ? { current_period_end: item.current_period_end } : {}), ...(item.prior_period_end ? { prior_period_end: item.prior_period_end } : {}) }]
    }))
    const periods = Object.fromEntries(periodKeys.filter((key) => row.period_metadata?.[key]).map((key) => {
      const item = row.period_metadata![key]
      return [key, { basis: item.basis, period_end: item.period_end, quarter_ends: item.quarter_ends }]
    }))
    if (Object.keys(growth).length) result.growth_metadata = growth
    if (Object.keys(periods).length) result.period_metadata = periods
    return result
  })
}

function isFinancialRows(value: unknown, max: number): value is FundamentalsTTM[] {
  return Array.isArray(value) && value.length <= max && value.every((row) => {
    if (!record(row) || !keysOnly(row, ['ticker', 'insufficient_data', ...amountKeys, 'growth_metadata', 'period_metadata']) || !symbol(row.ticker) || typeof row.insufficient_data !== 'boolean') return false
    if (!amountKeys.every((key) => row[key] === undefined || row[key] === null || (typeof row[key] === 'number' && Number.isFinite(row[key])))) return false
    if (row.growth_metadata !== undefined && (!record(row.growth_metadata) || !keysOnly(row.growth_metadata, growthKeys) || !Object.values(row.growth_metadata).every((item) => record(item) && keysOnly(item, ['basis', 'status', 'current_period_end', 'prior_period_end']) && ['ttm', 'fiscal_year', 'unavailable'].includes(String(item.basis)) && ['available', 'non_positive_prior', 'insufficient_history'].includes(String(item.status)) && (item.current_period_end === undefined || date(item.current_period_end)) && (item.prior_period_end === undefined || date(item.prior_period_end))))) return false
    return row.period_metadata === undefined || (record(row.period_metadata) && keysOnly(row.period_metadata, periodKeys) && Object.values(row.period_metadata).every((item) => record(item) && keysOnly(item, ['basis', 'period_end', 'quarter_ends']) && short(item.basis, 20) && date(item.period_end) && Array.isArray(item.quarter_ends) && item.quarter_ends.length <= 8 && item.quarter_ends.every(date)))
  })
}

export function isScreenerDraft(value: unknown): value is ScreenerDraft {
  if (!record(value) || !keysOnly(value, ['criteria', 'snapshot', 'selected', 'requestId']) || !isScreenCriteria(value.criteria) || !symbols(value.selected) || !requestId(value.requestId)) return false
  if (value.snapshot === null) return value.selected.length === 0
  const snapshot = value.snapshot
  if (!record(snapshot) || !keysOnly(snapshot, ['criteria', 'universeName', 'data', 'capturedAt']) || !isScreenCriteria(snapshot.criteria) || !short(snapshot.universeName, 120) || !timestamp(snapshot.capturedAt) || !record(snapshot.data)) return false
  const data = snapshot.data
  const counts = ['total_attempted', 'total_evaluated', 'total_matches', 'total_failed', 'total_insufficient']
  return keysOnly(data, ['results', 'universe_name', ...counts]) && isFinancialRows(data.results, 500) && short(data.universe_name, 120) && counts.every((key) => Number.isInteger(data[key]) && Number(data[key]) >= 0 && Number(data[key]) <= 500) && value.selected.every((ticker) => (data.results as FundamentalsTTM[]).some((row) => row.ticker === ticker))
}

export function isCompareDraft(value: unknown): value is CompareDraft {
  return record(value) && keysOnly(value, ['tickers', 'snapshots', 'requestId']) && symbols(value.tickers) && requestId(value.requestId) && Array.isArray(value.snapshots) && value.snapshots.length <= 5 && value.snapshots.every((snapshot) => record(snapshot) && keysOnly(snapshot, ['tickers', 'results', 'capturedAt']) && symbols(snapshot.tickers) && snapshot.tickers.length >= 2 && timestamp(snapshot.capturedAt) && isFinancialRows(snapshot.results, 20) && snapshot.results.every((row) => (snapshot.tickers as string[]).includes(row.ticker)))
}

export function screenCriteriaKey(criteria: ScreenCriteria): string {
  return JSON.stringify({ filters: Object.fromEntries(screenFilterKeys.map((key) => [key, criteria.filters[key]])), universe: criteria.universe, custom: criteria.universe === 'custom' ? criteria.custom : '', sort: criteria.sort, direction: criteria.direction, limit: criteria.limit })
}

export function screenCriteriaParams(criteria: ScreenCriteria): URLSearchParams {
  const params = new URLSearchParams({ universe: criteria.universe, sort: criteria.sort, direction: criteria.direction, limit: criteria.limit })
  for (const key of screenFilterKeys) if (criteria.filters[key]) params.set(key, criteria.filters[key])
  // Preserve inactive custom input when another universe is selected. The
  // universe still determines which symbols are submitted to the screener.
  params.set('symbols', criteria.custom)
  return params
}

/** Query-only edits must reach the native URL before an immediate reload. */
export function replaceResearchUrl(history: Pick<History, 'replaceState'>, path: '/screener' | '/compare', params: URLSearchParams): void {
  // Next's App Router copies its internal state and synchronizes search params
  // for native history calls whose data is null.
  history.replaceState(null, '', `${path}${params.size ? `?${params}` : ''}`)
}

/** Use the latest shared draft to keep persisted input and its URL coherent. */
export function editScreenDraft(current: ScreenerDraft, changes: Partial<ScreenCriteria>, writeUrl: (params: URLSearchParams) => void): ScreenerDraft {
  const criteria = { ...current.criteria, ...changes }
  writeUrl(screenCriteriaParams(criteria))
  return { ...current, criteria }
}

/** Any screening parameter is an explicit complete link; omitted fields use defaults. */
export function screenCriteriaFromUrl(search: URLSearchParams): ScreenCriteria | null {
  if (![...screenFilterKeys, 'universe', 'symbols', 'sort', 'direction', 'limit'].some((key) => search.has(key))) return null
  const limit = search.has('limit') ? search.get('limit')!.slice(0, 8) : '50'
  return {
    filters: Object.fromEntries(screenFilterKeys.map((key) => [key, (search.get(key) || '').slice(0, 40)])),
    universe: search.get('universe') === 'watchlist' || search.get('universe') === 'custom' ? search.get('universe') as ScreenCriteria['universe'] : 'curated',
    custom: (search.get('symbols') || '').slice(0, 6000),
    sort: screenSortKeys.includes(search.get('sort') as typeof screenSortKeys[number]) ? search.get('sort')! : 'revenue_growth_yoy',
    direction: search.get('direction') === 'asc' ? 'asc' : 'desc',
    limit,
  }
}

export function completeScreen(draft: ScreenerDraft, id: string, snapshot: ScreenSnapshot): ScreenerDraft {
  return draft.requestId === id ? { ...draft, snapshot, selected: [], requestId: null } : draft
}

export function completeComparison(draft: CompareDraft, id: string, snapshot: ComparisonSnapshot): CompareDraft {
  return draft.requestId === id ? { ...draft, requestId: null, snapshots: [snapshot, ...draft.snapshots.filter((row) => row.tickers.join(',') !== snapshot.tickers.join(','))].slice(0, 5) } : draft
}

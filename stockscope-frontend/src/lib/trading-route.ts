export type TradingTab = 'paper' | 'backtest' | 'congress'
export type SavedTradingKind = 'backtest' | 'portfolio'
export interface SavedTradingRoute {
  kind: SavedTradingKind
  id: string
  apiPath: string
  href: string
}

export function validSavedTradingId(kind: SavedTradingKind, id: string): boolean {
  const prefix = kind === 'backtest' ? 'run' : 'portfolio'
  return new RegExp(`^${prefix}-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$`).test(id)
}

export function savedTradingHref(kind: SavedTradingKind, id: string): string {
  return `/trading/${kind === 'backtest' ? 'backtests' : 'portfolios'}/${encodeURIComponent(id)}`
}

/** A saved record's canonical path takes precedence over the workspace tab query. */
export function tradingRoute(pathname: string, tabQuery: string | null): {
  tab: TradingTab; saved: SavedTradingRoute | null; error: string | null
} {
  const match = /^\/trading\/(backtests|portfolios)\/([^/]+)\/?$/.exec(pathname)
  if (match) {
    const kind = match[1] === 'backtests' ? 'backtest' : 'portfolio'
    const tab = kind === 'backtest' ? 'backtest' : 'paper'
    let id = ''
    try { id = decodeURIComponent(match[2]) } catch { /* Invalid paths have no fetchable record. */ }
    if (!validSavedTradingId(kind, id)) return { tab, saved: null, error: 'This saved research link is invalid (404). Choose a saved item from the workspace.' }
    return { tab, saved: { kind, id, href: savedTradingHref(kind, id), apiPath: `/${match[1]}/${id}` }, error: null }
  }
  return { tab: tabQuery === 'backtest' || tabQuery === 'congress' ? tabQuery : 'paper', saved: null, error: null }
}

/** Ignore late responses after Back/Forward or another saved record is selected. */
export function loadSavedTradingRoute<T extends { id: string }>(
  route: SavedTradingRoute,
  load: (apiPath: string) => Promise<T>,
  onResult: (result: T) => void,
  onError: (error: Error) => void,
): () => void {
  let active = true
  void load(route.apiPath).then((result) => {
    if (!active) return
    if (result.id !== route.id) throw new Error('The saved record did not match the requested link. Reload this page to try again.')
    onResult(result)
  }).catch((error: unknown) => {
    if (active) onError(error instanceof Error ? error : new Error('Saved research could not be loaded.'))
  })
  return () => { active = false }
}

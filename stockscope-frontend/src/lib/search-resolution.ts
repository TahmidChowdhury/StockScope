type Suggestion = { symbol: string; name: string }
export function resolveSearch(query: string, matches: Suggestion[], available = true, directTicker = false): string {
  const raw = query.trim()
  const symbol = raw.toUpperCase().replace(/^(BRK|BF)\.([AB])$/, '$1-$2')
  if (directTicker) {
    if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(symbol)) throw new Error('Enter a valid ticker, such as AAPL or VOD.L.')
    if (!available) throw new Error('Ticker lookup is unavailable. Please retry; the company has not been opened.')
    const exact = matches.find(item => item.symbol.toUpperCase() === symbol)
    if (exact) return exact.symbol
    throw new Error(`Ticker ${symbol} was not found. Check the spelling (Apple is AAPL), or search by company name.`)
  }
  const exact = matches.find(item => item.symbol.toUpperCase() === symbol)
  if (exact) return exact.symbol
  if (matches.length === 1) return matches[0].symbol
  if (matches.length > 1) throw new Error('Several companies match. Select a suggestion to continue.')
  throw new Error(available ? 'No matching companies. Try another name, or select Enter ticker directly.' : 'Company search is unavailable. Retry, or select Enter ticker directly.')
}

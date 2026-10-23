/** Only research workspaces may be destinations for the company return link. */
export function researchReturn(value: string | null): { href: string; label: string } | null {
  if (!value || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u001f]/.test(value)) return null
  try {
    const url = new URL(value, 'https://stockscope.local')
    if (url.origin !== 'https://stockscope.local') return null
    const label = url.pathname === '/screener'
      ? 'Back to screener'
      : url.pathname === '/compare'
        ? 'Back to comparison'
        : url.pathname === '/disclosures'
          ? 'Back to disclosures'
          : null
    return label ? { href: `${url.pathname}${url.search}`, label } : null
  } catch {
    return null
  }
}

export function companyResearchHref(symbol: string, returnTo: string): string {
  const destination = researchReturn(returnTo)
  const params = new URLSearchParams()
  if (destination) params.set('returnTo', destination.href)
  return `/stock/${encodeURIComponent(symbol)}${params.size ? `?${params}` : ''}`
}

export function snapshotTime(timestamp: string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    timeZone: 'America/New_York', timeZoneName: 'short',
  }).format(new Date(timestamp))
}

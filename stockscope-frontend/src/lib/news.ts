/** Missing and invalid provider scores are not neutral observations. */
export function normalizeNewsSentiment(value: unknown, sourceType?: string): { score: number; label: string } | undefined {
  if (sourceType === 'company_release') return undefined
  if (!value || typeof value !== 'object' || !('compound' in value)) return undefined
  const score = value.compound
  if (typeof score !== 'number' || !Number.isFinite(score) || score < -1 || score > 1) return undefined
  return { score, label: score >= 0.05 ? 'Positive' : score <= -0.05 ? 'Negative' : 'Neutral' }
}

/** Publication and provider discovery are separate observations. */
export function newsDateLabels(publishedAt: string | null, providerSeenAt: string | null, now = Date.now()) {
  const relativeTime = (value: string | null): string | null => {
    if (!value || !Number.isFinite(Date.parse(value))) return null
    const timestamp = Date.parse(value)
    const hours = Math.floor((now - timestamp) / (1000 * 60 * 60))
    if (timestamp > now) return new Date(timestamp).toLocaleDateString()
    if (hours < 1) return 'within the last hour'
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return days < 7 ? `${days}d ago` : new Date(timestamp).toLocaleDateString()
  }
  const publication = relativeTime(publishedAt)
  const discovery = relativeTime(providerSeenAt)
  return {
    publication: publication ? `Published ${publication}` : 'Publication date unknown',
    discovery: discovery ? `Discovered ${discovery}` : null,
  }
}

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

export interface SavedNewsArticle {
  title?: string; url?: string; publishedAt?: string | null; provider_seen_at?: string | null
  source_type?: string; provider?: string; original_source?: string; source?: string
  username?: string; message_id?: number | string; description?: string
  sentiment?: { compound?: number; label?: string } | null
}
export interface SavedNewsPage {
  articles: SavedNewsArticle[]; sources: string[]; total: number; saved_total: number
  offset: number; limit: number; count: number; has_more: boolean; can_collect: boolean
}
export function readSavedNewsPage(value: unknown): SavedNewsPage {
  const page = value as SavedNewsPage | null
  if (!page || !Array.isArray(page.articles) || !Array.isArray(page.sources) ||
      !page.articles.every(article => article !== null && typeof article === 'object' && (article.source === undefined || typeof article.source === 'string')) ||
      !page.sources.every(source => typeof source === 'string') ||
      !['total', 'saved_total', 'offset', 'limit', 'count'].every(key => Number.isSafeInteger(page[key as keyof SavedNewsPage]) && Number(page[key as keyof SavedNewsPage]) >= 0) ||
      page.limit < 1 || page.count !== page.articles.length || page.total > page.saved_total ||
      page.count > page.limit || page.offset + page.count > page.total || page.has_more !== (page.offset + page.count < page.total) || typeof page.can_collect !== 'boolean') {
    throw new Error('The server did not return a valid saved-news page. Reload to try again.')
  }
  return page
}
export function savedNewsParams(sort: string, offset: number, excluded: string[]) {
  const params = new URLSearchParams({ sort, offset: String(offset), limit: '20' })
  for (const source of [...excluded].sort()) params.append('exclude_source', source)
  return params.toString()
}

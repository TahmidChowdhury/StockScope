'use client'

import { apiFetch, readApiJson } from '@/lib/api'
import { newsDateLabels, normalizeNewsSentiment, readSavedNewsPage, savedNewsParams, type SavedNewsPage } from '@/lib/news'
import { companyResearchHref } from '@/lib/research-workflow'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Newspaper, RefreshCw, ExternalLink } from 'lucide-react'
import FilterSortBar from './FilterSortBar'

interface NewsArticle {
  title: string
  url: string
  publishedAt: string | null
  provider_seen_at: string | null
  source_type?: string
  provider?: string
  original_source?: string
  username?: string
  message_id?: number | string
  source: {
    name: string
  }
  description?: string
  sentiment?: {
    score: number
    label: string
  }
}

interface NewsComponentProps {
  symbol: string
  className?: string
}

const sortOptions = [
  { id: 'date-desc', label: 'Latest First', direction: 'desc' as const },
  { id: 'date-asc', label: 'Oldest First', direction: 'asc' as const },
  { id: 'sentiment-desc', label: 'Most Positive', direction: 'desc' as const },
  { id: 'sentiment-asc', label: 'Most Negative', direction: 'asc' as const },
]

export default function NewsComponent(props: NewsComponentProps) {
  // A new company starts with its own filters, order, page, and source catalog.
  return <SavedNews key={props.symbol} {...props} />
}

function SavedNews({ symbol, className = '' }: NewsComponentProps) {
  const search = useSearchParams()
  const researchHref = companyResearchHref(symbol, search.get('returnTo') || '', 'analysis')
  const overviewHref = companyResearchHref(symbol, search.get('returnTo') || '')
  const [selection, setSelection] = useState({ sort: 'date-desc', offset: 0, excluded: [] as string[] })
  const [sources, setSources] = useState<string[]>([])
  const params = savedNewsParams(selection.sort, selection.offset, selection.excluded)
  const query = useQuery({
    queryKey: ['saved-news', symbol, params],
    queryFn: async ({ signal }) => readSavedNewsPage(await readApiJson<unknown>(
      await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}/news?${params}`, { signal }),
      'Saved news could not be loaded. Please retry.',
    )),
    staleTime: 0, retry: false, refetchOnWindowFocus: false,
    placeholderData: previous => previous,
  })
  const pageInfo = query.data
  const data = query.isPlaceholderData ? undefined : query.data
  useEffect(() => { if (data) setSources(data.sources) }, [data])
  const articles = data ? transformArticles(data) : []
  const pending = query.isPending || query.isPlaceholderData
  const clearFilters = () => setSelection(previous => ({ ...previous, excluded: [], offset: 0 }))
  return <section className={`surface min-w-0 p-3 sm:p-6 ${className}`} aria-label="Saved news" aria-busy={query.isFetching}>
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">Saved news</h2>
      <button onClick={() => void query.refetch()} disabled={query.isFetching}
        aria-label="Reload saved news" title="Reload saved news"
        className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-400 hover:bg-white/5 hover:text-sage-200">
        <RefreshCw className={`h-4 w-4 ${query.isFetching ? 'animate-spin' : ''}`} />
      </button>
    </div>
    {!!sources.length && <FilterSortBar
      filters={sources.map(source => ({ id: source, label: source, enabled: !selection.excluded.includes(source) }))}
      onFilterChange={(source, enabled) => setSelection(previous => ({ ...previous, offset: 0,
        excluded: enabled ? previous.excluded.filter(value => value !== source) : [...new Set([...previous.excluded, source])],
      }))}
      sortOptions={sortOptions} currentSort={selection.sort}
      onSortChange={sort => setSelection(previous => ({ ...previous, sort, offset: 0 }))}
      className="mb-3"
    />}
    <p role="status" className="mb-3 text-xs text-slate-400">
      {pending ? 'Loading saved articles…' : data ? `${data.count ? data.offset + 1 : 0}–${data.offset + data.count} of ${data.total} matching saved articles · ${data.saved_total} saved in total` : 'Saved article count unavailable'}
    </p>
    {query.isError && <div role="alert" className="mb-4 text-sm text-amber-200">
      <p>Couldn’t load saved news for {symbol}. {query.error.message}</p>
      {data && <p>Previously loaded results are shown.</p>}
      <button onClick={() => void query.refetch()} disabled={query.isFetching} className="button-secondary mt-3">Retry saved news</button>
    </div>}
    {pending && <div aria-hidden="true" className="space-y-4 py-5 motion-safe:animate-pulse">
      {[0, 1, 2].map(index => <div key={index} className="h-12 rounded bg-white/5" />)}
    </div>}
    {data && !query.isError && !articles.length && <div className="py-6 text-center sm:py-8">
      <Newspaper className="mx-auto mb-4 h-12 w-12 text-white/20" />
      {data.saved_total === 0 ? <>
        <p className="text-sm text-white/60">No saved news for {symbol} yet.</p>
        {data.can_collect ? <>
          <p className="mt-2 text-xs leading-5 text-slate-400">Open the research summary to refresh sources and look for articles to save.</p>
          <Link href={researchHref} className="button-primary mt-5">Open research summary<ArrowUpRight className="h-4 w-4" /></Link>
        </> : <>
          <p className="mt-2 text-xs leading-5 text-slate-400">No articles have been saved here. A member or administrator can refresh shared research.</p>
          <Link href={overviewHref} className="button-secondary mt-5">View company overview</Link>
        </>}
      </> : <>
        <p className="text-sm text-white/60">No saved articles match the selected sources.</p>
        <button onClick={clearFilters} className="button-secondary mt-4">Clear source filters</button>
      </>}
    </div>}
    {!!articles.length && <div className="divide-y divide-white/[0.07]">
      {articles.map((article, index) => <EnhancedNewsCard key={`${article.url || article.title}-${index}`} article={article} />)}
    </div>}
    {pageInfo && <nav aria-label="Saved news pagination" className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3">
      <button className="button-secondary" disabled={query.isFetching || query.isError || pageInfo.offset === 0}
        onClick={() => setSelection(previous => ({ ...previous, offset: Math.max(0, pageInfo.offset - pageInfo.limit) }))}>Previous page</button>
      <span className="text-xs text-slate-400">Page {Math.floor(pageInfo.offset / pageInfo.limit) + 1} of {Math.max(1, Math.ceil(pageInfo.total / pageInfo.limit))}</span>
      <button className="button-secondary" disabled={query.isFetching || query.isError || !pageInfo.has_more}
        onClick={() => setSelection(previous => ({ ...previous, offset: pageInfo.offset + pageInfo.limit }))}>Next page</button>
    </nav>}
    {data?.can_collect && articles.length > 0 && <Link href={researchHref} className="mt-3 inline-flex min-h-11 items-center text-xs text-sage-300 hover:underline">Open research summary to refresh sources →</Link>}
  </section>
}

function transformArticles(data: SavedNewsPage): NewsArticle[] {
      const isGenericStocktwitsUrl = (url: string) => {
        const normalizedUrl = url.trim().replace(/\/+$/, '').toLowerCase()
        return [
          'https://stocktwits.com',
          'http://stocktwits.com',
          'https://www.stocktwits.com',
          'http://www.stocktwits.com',
          'https://stocktwits.com/mobile',
          'http://stocktwits.com/mobile',
          'https://www.stocktwits.com/mobile',
          'http://www.stocktwits.com/mobile'
        ].includes(normalizedUrl)
      }

      // Transform the articles to match our interface
      const transformedArticles = data.articles.map((item: {
        title?: string;
        url?: string;
        publishedAt?: string | null;
        provider_seen_at?: string | null;
        source_type?: string;
        provider?: string;
        original_source?: string;
        source?: string;
        username?: string;
        message_id?: number | string;
        description?: string;
        sentiment?: { compound?: number; label?: string } | null
      }) => {
        // Handle missing or invalid URLs better
        let articleUrl = item.url || ''
        const sourceName = (item.source || '').toLowerCase()

        if (sourceName.includes('stocktwits') && item.username && item.message_id) {
          articleUrl = `https://stocktwits.com/${item.username}/message/${item.message_id}`
        }

        // If no URL provided, create appropriate fallback based on source
        if (
          !articleUrl ||
          articleUrl === '#' ||
          articleUrl === 'null' ||
          (sourceName.includes('stocktwits') && isGenericStocktwitsUrl(articleUrl))
        ) {
          articleUrl = ''
        }

        return {
          title: item.title || 'No title available',
          url: articleUrl,
          publishedAt: item.publishedAt && Number.isFinite(Date.parse(item.publishedAt)) ? item.publishedAt : null,
          provider_seen_at: item.provider_seen_at && Number.isFinite(Date.parse(item.provider_seen_at)) ? item.provider_seen_at : null,
          source_type: item.source_type,
          provider: item.provider,
          original_source: item.original_source,
          username: item.username,
          message_id: item.message_id,
          source: {
            name: item.source || 'Unknown Source'
          },
          description: item.description || '',
          sentiment: normalizeNewsSentiment(item.sentiment, item.source_type)
        }
      }) || []

  return transformedArticles
}

function EnhancedNewsCard({ article }: { article: NewsArticle }) {
  const release = article.source_type === 'company_release'
  const dates = newsDateLabels(article.publishedAt, article.provider_seen_at)
  const provider = article.provider === 'gdelt' ? 'GDELT' : article.provider === 'company_ir_rss' ? 'Official company RSS' : null
  const tone = article.sentiment
  const description = article.description?.trim()
  return (
    <article className="py-4 sm:py-5">
      <h3 className="max-w-3xl font-medium leading-snug text-slate-100">
        {article.url ? <a href={article.url} target="_blank" rel="noopener noreferrer" className="hover:text-sage-200 hover:underline">
          {article.title} <ExternalLink aria-hidden="true" className="inline h-3 w-3 text-sage-300" />
        </a> : article.title}
      </h3>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs text-slate-400">
        <span>{article.original_source || article.source.name}{provider && ` · via ${provider}`}</span>
        <span title={article.publishedAt || undefined}>{dates.publication}</span>
        {dates.discovery && <span title={article.provider_seen_at || undefined}>{dates.discovery}</span>}
        {release && <span className="text-sage-200">Company release</span>}
        {tone && <span className={tone.score >= 0.05 ? 'text-sage-300' : tone.score <= -0.05 ? 'text-rose-300' : 'text-slate-400'}>{tone.label} tone</span>}
        {!article.url && <span>Source link unavailable</span>}
      </div>
      {description && description !== article.title.trim() &&
        <p className="mt-2 line-clamp-2 max-w-3xl text-sm leading-relaxed text-slate-300">{description}</p>}
    </article>
  )
}

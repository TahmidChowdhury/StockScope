'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, RefreshCw, X } from 'lucide-react'
import { apiFetch, getAuthSession, readApiJson } from '@/lib/api'
import { companyFundamentalsHref, companyResearchHref } from '@/lib/research-workflow'
import { readSavedNewsPage } from '@/lib/news'
import { collectionLabel } from '@/lib/collection'
import { useAnalysisProgress } from '@/hooks/useAnalysisProgress'
import type { StockAnalysis, StockDashboardProps } from '@/types'
import { LoadingRows } from './ResearchLoading'

function displayDate(value?: string | null) {
  if (!value) return 'Unknown'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString()
}
function safeSourceUrl(value?: string | null) {
  try {
    const url = new URL(value || '')
    return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined
  } catch { return undefined }
}
const providerNames: Record<string, string> = {
  news: 'News', 'news.company_ir_rss': 'Company releases', 'news.finviz': 'Finviz',
  'news.gdelt': 'GDELT discovery', 'news.google_news': 'Google News',
  'news.rss': 'Publisher RSS', 'news.stocktwits': 'Stocktwits',
  'news.yahoo_finance': 'Yahoo Finance', sec_facts: 'SEC facts',
}

export default function StockDashboard(props: StockDashboardProps) {
  return <ResearchSummary key={props.symbol} {...props} />
}
function ResearchSummary({ symbol, onBack, embedded = false }: StockDashboardProps) {
  const search = useSearchParams()
  const returnTo = search.get('returnTo') || ''
  const client = useQueryClient()
  const progress = useAnalysisProgress(symbol)
  const job = progress.data
  const summary = useQuery({
    queryKey: ['research-summary', symbol],
    queryFn: async ({ signal }): Promise<StockAnalysis | null> => {
      const response = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}`, { signal })
      if (response.status === 404) return null
      const data = await readApiJson<StockAnalysis>(response, 'Saved research could not be loaded.')
      if (data.ticker !== symbol || !Array.isArray(data.sources) || !Array.isArray(data.filings)) throw new Error('Saved research was incomplete or belonged to another company.')
      return data
    },
    staleTime: 0, retry: false, refetchOnWindowFocus: false,
  })
  const news = useQuery({
    queryKey: ['saved-news', symbol, 'summary-preview'],
    queryFn: async ({ signal }) => readSavedNewsPage(await readApiJson(await apiFetch(
      `/api/stocks/${encodeURIComponent(symbol)}/news?limit=5&offset=0&sort=date-desc`, { signal },
    ), 'Saved articles could not be loaded.')),
    staleTime: 0, retry: false, refetchOnWindowFocus: false,
  })
  const stockData = summary.data
  const canCollect = news.data?.can_collect ?? ['admin', 'member'].includes(getAuthSession()?.role || '')
  const collecting = progress.starting || progress.active
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const deleteStock = async () => {
    setDeleting(true)
    setDeleteError('')
    try {
      await readApiJson(await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}`, { method: 'DELETE' }), 'Could not delete saved research.')
      await Promise.all([
        client.invalidateQueries({ queryKey: ['watchlist'] }),
        client.invalidateQueries({ queryKey: ['saved-news', symbol] }),
        client.invalidateQueries({ queryKey: ['research-summary', symbol] }),
      ])
      onBack()
    } catch (reason) { setDeleteError(reason instanceof Error ? reason.message : 'Could not delete saved research.') }
    finally { setDeleting(false); setConfirmDelete(false) }
  }
  const sentiment = stockData?.sentiment_metrics?.avg_sentiment
  const filings = stockData?.filings ?? []
  return <section className={`${embedded ? '' : 'min-h-screen bg-slate-950 p-4 sm:p-8'} text-white`} aria-label={`${symbol} research`}>
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {!embedded && <button onClick={onBack} className="mb-3 text-sm text-sage-300">← Back to watchlist</button>}
          <h2 className="text-lg font-medium">{symbol} saved research</h2>
          <p className="mt-1 text-xs text-slate-400">Saved articles and filing events · Original sources and dates below</p>
        </div>
        {canCollect && <button onClick={progress.start}
          disabled={collecting || progress.isPending || progress.isFetching || progress.isError || progress.cooling}
          className="button-primary">
          <RefreshCw className={`h-4 w-4 ${collecting ? 'animate-spin' : ''}`} />
          {progress.starting ? 'Starting collection…' : progress.active ? 'Collecting sources…' : 'Refresh sources'}
        </button>}
      </div>

      <div aria-label="Collection status" data-run-id={job?.run_id || job?.started_at}>
        {progress.isPending && <p role="status" className="text-xs text-slate-400">Checking collection status…</p>}
        {job && <div role="status" className={`border-l-2 pl-3 text-sm ${job.status === 'failed' || job.status === 'partial' ? 'border-amber-300 text-amber-200' : 'border-sage-300 text-sage-200'}`}>
          <p className="font-medium">{collectionLabel(job)}</p>
          <p className="mt-1">{job.message}</p>
          <p className="mt-1 text-xs text-slate-400">Collection started: {displayDate(job.started_at)}{job.completed_at && ` · Collection finished: ${displayDate(job.completed_at)}`}</p>
        </div>}
        {!job && progress.isSuccess && !progress.starting && <p className="text-xs text-slate-400">No collection run is tracked for this company.</p>}
        {progress.startError && <p role="alert" className="mt-3 text-sm text-amber-200">Collection request: {progress.startError.message} Check the tracked status before trying again.</p>}
        {progress.isError && <div role="alert" className="mt-3 text-sm text-amber-200">
          <p>Collection status could not be checked. {progress.error.message}{job ? ' The last known status is shown; the backend job may still be running.' : ''}</p>
          <button disabled={progress.isFetching || progress.cooling} onClick={() => void progress.refetch()} className="button-secondary mt-2">Retry collection status</button>
        </div>}
      </div>

      <section className="surface p-4 sm:p-5" aria-label="Recent saved articles">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-medium">Recent saved articles</h3>
          <Link href={companyResearchHref(symbol, returnTo, 'news')} className="text-xs text-sage-300">Browse saved news →</Link>
        </div>
        {news.isPending && <LoadingRows label="Loading saved articles…" />}
        {news.isError && <div role="alert" className="mt-3 text-sm text-amber-200"><p>{news.error.message}{news.data ? ' Previously loaded articles are shown.' : ''}</p><button disabled={news.isFetching} onClick={() => void news.refetch()} className="button-secondary mt-2">Retry articles</button></div>}
        {news.data && !news.isError && news.data.saved_total === 0 && <div className="mt-3 text-sm text-slate-400">
          <p>No saved articles for {symbol}.</p>
          <p className="mt-1">{collecting ? 'Collection is in progress. Articles will appear if sources return usable evidence.' : canCollect ? 'Use Refresh sources to look for articles to save.' : 'A member or administrator can refresh shared research.'}</p>
        </div>}
        {!!news.data?.articles.length && <ul className="mt-2 divide-y divide-white/10">{news.data.articles.map((article, index) => <li key={article.url || `${article.title}-${index}`} className="py-3">
          <p className="font-medium leading-snug">{safeSourceUrl(article.url) ? <a href={safeSourceUrl(article.url)} target="_blank" rel="noopener noreferrer" className="hover:text-sage-200 hover:underline">{article.title || 'Untitled saved article'} <ExternalLink className="inline h-3 w-3" /></a> : article.title || 'Untitled saved article'}</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">{article.original_source || article.source || 'Source unknown'} · Published: {displayDate(article.publishedAt)}{article.source_type === 'company_release' ? ' · Company release (unscored)' : ''}</p>
          {article.provider_seen_at && <p className="text-xs text-slate-500">Provider discovered: {displayDate(article.provider_seen_at)}</p>}
        </li>)}</ul>}
        {news.data && <p className="mt-2 text-xs text-slate-500">Showing {news.data.count} of {news.data.saved_total} saved articles. This is not a search of all available news.</p>}
      </section>

      <section className="surface p-4 sm:p-5" aria-label="Saved filing events">
        <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-medium">SEC filing events</h3><Link href={companyResearchHref(symbol, returnTo, 'sources')} className="text-xs text-sage-300">Browse SEC evidence →</Link></div>
        {summary.isPending && <LoadingRows label="Loading saved research…" />}
        {summary.isError && <div role="alert" className="mt-3 text-sm text-amber-200"><p>{summary.error.message}{stockData ? ' Previously loaded research is shown.' : ''}</p><button disabled={summary.isFetching} onClick={() => void summary.refetch()} className="button-secondary mt-2">Retry saved research</button></div>}
        {summary.isSuccess && filings.length === 0 && <p className="mt-3 text-sm text-slate-400">No saved filing events are available.</p>}
        {!!filings.length && <ul className="mt-2 divide-y divide-white/10">{filings.map((filing, index) => <li key={`${filing.url}-${index}`} className="py-3">
          <p className="font-medium">{filing.form_type} · {filing.description}</p>
          <p className="mt-1 text-xs text-slate-400">SEC · Filed: {filing.filing_date || 'Unknown'}</p>
          {safeSourceUrl(filing.url) && <a href={safeSourceUrl(filing.url)} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex min-h-11 items-center gap-1 text-sm text-sage-300">Read filing <ExternalLink className="h-3 w-3" /></a>}
        </li>)}</ul>}
      </section>

      {stockData && <p className="text-xs leading-6 text-slate-400">
        Evidence freshness: {stockData.freshness} · {stockData.sources.length} saved sources · {stockData.sentiment_metrics.sample_size} scored news items · News tone: {sentiment == null ? 'Unavailable' : `${sentiment.toFixed(3)} (−1 to +1)`}
      </p>}
      {job && Object.keys(job.providers).length > 0 && <details key={`${job.run_id || job.started_at}-${job.status}`} open={job.status !== 'completed'} className="surface p-4 sm:p-5">
        <summary className="cursor-pointer text-sm font-medium text-sage-300">Collection outcomes by provider</summary>
        <ul className="mt-3 grid gap-3 text-sm sm:grid-cols-2" aria-label="Refresh results">{Object.entries(job.providers).map(([source, outcome]) => <li key={source} className="min-w-0 break-words rounded-lg border border-white/10 p-3">
          <p>{providerNames[source] || source}: {outcome.status.replaceAll('_', ' ')} · {outcome.count} items</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">{outcome.message}</p>
        </li>)}</ul>
      </details>}
      {stockData && <details className="border-b border-white/10 pb-3">
        <summary className="cursor-pointer py-2 text-sm font-medium text-sage-300">Source coverage and dates</summary>
        <div className="overflow-x-auto"><table className="w-full text-left text-xs">
          <thead className="text-slate-400"><tr><th className="p-2">Source</th><th className="p-2">Items</th><th className="p-2">Latest publication / filing</th><th className="p-2">Coverage</th></tr></thead>
          <tbody>{stockData.sources.map(source => <tr key={source.source} className="border-t border-white/10"><th className="p-2 text-left font-medium">{source.source}</th><td className="p-2">{source.count}</td><td className="p-2">{source.source === 'SEC' ? source.latest_update?.slice(0, 10) || 'Unknown' : displayDate(source.latest_update)}</td><td className="p-2">{source.freshness} · {source.unknown_timestamps} undated</td></tr>)}</tbody>
        </table></div>
        <p className="mt-3 text-xs text-slate-500">Evidence summary calculated: {displayDate(stockData.generated_at)}. This is not a publication or collection date.</p>
      </details>}
      <details className="border-b border-white/10 pb-3">
        <summary className="cursor-pointer py-2 text-sm font-medium text-sage-300">Research limitations</summary>
        <ul className="mt-2 list-disc space-y-2 pl-5 text-xs leading-6 text-slate-400">
          <li>Coverage can be incomplete, stale, or undated. A completed collection is not a claim of complete news coverage.</li>
          <li>Text tone measures wording, not company value, expected returns, or the probability of profit. Company releases and SEC events are unscored.</li>
          <li>A filing type alone does not establish positive or negative news. Read the original source.</li>
          <li>Failed or empty provider responses can leave older saved evidence in place. Collection times do not replace publication or filing dates.</li>
        </ul>
      </details>
      <Link href={companyFundamentalsHref(symbol, returnTo)} className="button-secondary">Company fundamentals</Link>
      {deleteError && <p role="alert" className="text-sm text-red-300">{deleteError}</p>}
      {getAuthSession()?.role === 'admin' && stockData && <div className="border-t border-white/10 pt-5">
        {!confirmDelete ? <button disabled={collecting || progress.isPending || progress.isError} onClick={() => setConfirmDelete(true)} className="flex items-center gap-1 text-sm text-red-300"><X className="h-4 w-4" />Delete saved research for {symbol}</button> : <div className="flex flex-wrap items-center gap-3 text-sm"><p>Delete all saved research for {symbol}?</p><button disabled={deleting || collecting} onClick={deleteStock} className="rounded bg-red-700 px-3 py-2">{deleting ? 'Deleting…' : 'Delete'}</button><button disabled={deleting} onClick={() => setConfirmDelete(false)} className="rounded bg-slate-700 px-3 py-2">Cancel</button></div>}
      </div>}
    </div>
  </section>
}

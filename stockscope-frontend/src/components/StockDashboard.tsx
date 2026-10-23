'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { Activity, ExternalLink, FileText, RefreshCw, X } from 'lucide-react'
import { apiFetch, getAuthSession } from '@/lib/api'
import type { InvestmentAdvice, QuantitativeAnalysis, StockAnalysis, StockDashboardProps } from '@/types'

function displayDate(value?: string | null) {
  if (!value) return 'Unknown'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString()
}

function safeSourceUrl(value: string) {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined
  } catch {
    return undefined
  }
}

function pause(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) return reject(new DOMException('Aborted', 'AbortError'))
    const onAbort = () => {
      clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    }
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    signal.addEventListener('abort', onAbort, { once: true })
  })
}

export default function StockDashboard({ symbol, onBack, embedded = false }: StockDashboardProps) {
  const [stockData, setStockData] = useState<StockAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [providerResults, setProviderResults] = useState<Record<string, { status: string; count: number; message: string }>>({})
  const [error, setError] = useState<string | null>(null)
  const [research, setResearch] = useState<InvestmentAdvice | null>(null)
  const [quantitative, setQuantitative] = useState<QuantitativeAnalysis | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const refreshController = useRef<AbortController | null>(null)
  const detailController = useRef<AbortController | null>(null)

  const loadData = useCallback(async (signal?: AbortSignal) => {
    const response = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}`, { signal })
    if (!response.ok) throw new Error(`Saved research is unavailable for ${symbol}. Try refreshing the sources.`)
    const data: StockAnalysis = await response.json()
    if (!signal?.aborted) setStockData(data)
  }, [symbol])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setStockData(null)
    setResearch(null)
    setQuantitative(null)
    setMessage(null)
    setProviderResults({})
    setRefreshing(false)
    setDetailsLoading(false)
    setConfirmDelete(false)
    loadData(controller.signal)
      .catch((reason: Error) => { if (!controller.signal.aborted) setError(reason.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => {
      controller.abort()
      refreshController.current?.abort()
      detailController.current?.abort()
    }
  }, [loadData])

  const refreshSources = async () => {
    detailController.current?.abort()
    setDetailsLoading(false)
    setProviderResults({})
    refreshController.current?.abort()
    const controller = new AbortController()
    refreshController.current = controller
    setRefreshing(true)
    setError(null)
    setMessage('Collecting new articles and filing events…')
    setResearch(null)
    setQuantitative(null)
    try {
      const response = await apiFetch('/api/stocks/analyze', {
        method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, sources: ['news', 'sec_facts'] }),
      })
      if (!response.ok) throw new Error('Could not start the source refresh.')
      const deadline = Date.now() + 240_000
      while (Date.now() < deadline) {
        await pause(1500, controller.signal)
        const statusResponse = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}/status`, { signal: controller.signal })
        if (!statusResponse.ok) throw new Error('Could not read refresh progress. Saved research is still available.')
        const status: { status: string; message: string; providers?: Record<string, { status: string; count: number; message: string }> } = await statusResponse.json()
        setProviderResults(status.providers ?? {})
        setMessage(status.message)
        if (status.status === 'failed') throw new Error(status.message || 'No sources could be refreshed.')
        if (status.status === 'completed' || status.status === 'partial') {
          await loadData(controller.signal)
          setMessage(status.status === 'partial' ? `Partial refresh: ${status.message}` : 'Sources refreshed. Publication dates are shown below.')
          return
        }
      }
      throw new Error('Refresh is taking longer than expected. The job may still be running; reopen this view to check saved results.')
    } catch (reason) {
      if (!controller.signal.aborted) {
        setError(reason instanceof Error ? reason.message : 'Refresh failed.')
        setMessage(null)
      }
    } finally {
      if (!controller.signal.aborted) setRefreshing(false)
    }
  }

  const loadDetails = async (kind: 'research' | 'quantitative') => {
    detailController.current?.abort()
    const controller = new AbortController()
    detailController.current = controller
    setDetailsLoading(true)
    setError(null)
    try {
      const endpoint = kind === 'research' ? 'investment-advice' : 'quantitative'
      const response = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}/${endpoint}`, { signal: controller.signal })
      if (!response.ok) throw new Error('Research details could not be loaded.')
      const data = await response.json()
      if (controller.signal.aborted) return
      if (kind === 'research') { setResearch(data); setQuantitative(null) }
      else { setQuantitative(data); setResearch(null) }
    } catch (reason) {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Could not load details.')
    } finally {
      if (!controller.signal.aborted) setDetailsLoading(false)
    }
  }

  const deleteStock = async () => {
    setDeleting(true)
    try {
      const response = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}`, { method: 'DELETE' })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || 'Could not delete saved research.')
      }
      onBack()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Delete failed.')
    } finally {
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  const sentiment = stockData?.sentiment_metrics?.avg_sentiment
  const sentimentLabel = sentiment == null ? 'Unavailable' : sentiment >= 0.05 ? 'Positive' : sentiment <= -0.05 ? 'Negative' : 'Neutral'
  const freshness = stockData?.freshness ?? 'unknown'
  const filings = stockData?.filings ?? []
  const mixedFreshness = freshness !== 'recent' && stockData?.sources.some(source => source.freshness === 'recent')
  const providerNames: Record<string, string> = {
    news: 'News', 'news.company_ir_rss': 'Company releases', 'news.finviz': 'Finviz',
    'news.gdelt': 'GDELT discovery', 'news.google_news': 'Google News',
    'news.rss': 'Publisher RSS', 'news.stocktwits': 'Stocktwits',
    'news.yahoo_finance': 'Yahoo Finance', sec_facts: 'SEC facts',
  }


  return (
    <section className={`${embedded ? '' : 'min-h-screen bg-slate-950 p-4 sm:p-8'} text-white`} aria-label={`${symbol} research`}>
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            {!embedded && <button onClick={onBack} className="mb-3 text-sm text-blue-300">← Back to watchlist</button>}
            <h2 className="text-2xl font-semibold">{symbol} research</h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-300">News tone and filing events provide context. They do not estimate investment returns or the probability of a profitable trade.</p>
          </div>
          <button onClick={refreshSources} disabled={refreshing || loading} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium hover:bg-blue-500 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing sources…' : 'Refresh sources'}
          </button>
        </div>

        {error && <p role="alert" className="rounded-lg border border-red-400/40 bg-red-950/40 p-4 text-sm text-red-200">{error}</p>}
        {message && <p role="status" className="rounded-lg bg-blue-950/50 p-4 text-sm text-blue-200">{message}</p>}
        {Object.keys(providerResults).length > 0 && <ul className="grid gap-2 text-sm text-slate-300 sm:grid-cols-2" aria-label="Refresh results">{Object.entries(providerResults).map(([source, outcome]) => <li key={source} className="rounded-lg border border-white/10 p-3"><span className="font-medium">{providerNames[source] || source}</span>: {outcome.status.replaceAll('_', ' ')} · {outcome.count} items<p className="mt-1 text-xs text-slate-400">{/timed?\s*out|timeout/i.test(outcome.message) ? 'The provider timed out. Results from other sources remain available.' : outcome.message}</p></li>)}</ul>}
        {loading ? <p role="status" className="py-12 text-center text-slate-300">Loading saved research…</p> : stockData && <>
          <div className={`rounded-xl border p-4 ${freshness === 'recent' ? 'border-slate-600 bg-slate-800/50' : 'border-amber-500/40 bg-amber-950/20'}`}>
            <p className="font-medium">{freshness === 'recent' ? 'Recent source material' : mixedFreshness ? 'Mixed freshness: some sources are stale or undated' : freshness === 'stale' ? 'Source material is stale' : 'Source freshness is unknown'}</p>
            <p className="mt-1 text-sm text-slate-300">Latest source publication: {displayDate(stockData.source_as_of)}. Summary generated: {displayDate(stockData.generated_at)}.</p>
            <p className="mt-1 text-xs text-slate-400">Generating a summary does not make its underlying articles or filings newer. Review each source date before using it.</p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm text-slate-300">News tone</p>
              <p className="mt-2 text-2xl font-semibold">{sentimentLabel}</p>
              <p className="mt-1 text-sm text-slate-400">{sentiment == null ? 'No scored news available' : `${sentiment.toFixed(3)} on a −1 to +1 scale`}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm text-slate-300">Scored news items</p>
              <p className="mt-2 text-2xl font-semibold">{stockData.sentiment_metrics.sample_size.toLocaleString()}</p>
              <p className="mt-1 text-sm text-slate-400">Text tone is separate from company value.</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-5">
              <p className="text-sm text-slate-300">Filing events</p>
              <p className="mt-2 text-2xl font-semibold">{filings.length.toLocaleString()}</p>
              <p className="mt-1 text-sm text-slate-400">Read the original disclosures below.</p>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/10 bg-white/5 p-4 sm:p-6">
            <h3 className="mb-4 text-lg font-semibold">Source coverage</h3>
            <table className="w-full text-left text-sm">
              <thead className="text-slate-400"><tr><th className="pb-3 pr-4">Source</th><th className="pb-3 pr-4">Items</th><th className="pb-3 pr-4">Text tone</th><th className="pb-3">Latest publication</th></tr></thead>
              <tbody>{stockData.sources.map(source => <tr key={source.source} className="border-t border-white/10">
                <td className="py-3 pr-4 font-medium">{source.source}</td>
                <td className="py-3 pr-4">{source.count}</td>
                <td className="py-3 pr-4">{source.avg_sentiment == null ? 'Not scored' : source.avg_sentiment.toFixed(3)}</td>
                <td className="py-3">{source.source === 'SEC' ? source.latest_update?.slice(0, 10) ?? 'Unknown' : displayDate(source.latest_update)}<span className="mt-1 block text-xs text-slate-400">{source.freshness}{source.unknown_timestamps > 0 ? ` · ${source.unknown_timestamps} undated` : ''}</span></td>
              </tr>)}</tbody>
            </table>
          </div>

          <div className="flex flex-wrap gap-3">
            <button disabled={detailsLoading || refreshing} onClick={() => loadDetails('research')} className="flex items-center gap-2 rounded-lg bg-blue-700 px-4 py-3 text-sm disabled:opacity-50"><FileText className="h-4 w-4" />Research summary</button>
            <button disabled={detailsLoading || refreshing} onClick={() => loadDetails('quantitative')} className="flex items-center gap-2 rounded-lg bg-slate-700 px-4 py-3 text-sm disabled:opacity-50"><Activity className="h-4 w-4" />Metric availability</button>
            <Link href={`/fundamentals/${encodeURIComponent(symbol)}`} className="rounded-lg border border-slate-600 px-4 py-3 text-sm">Company fundamentals</Link>
          </div>
          {detailsLoading && <p role="status" className="text-sm text-slate-300">Loading research details…</p>}

          {research && <div className="rounded-xl border border-blue-400/30 bg-blue-950/20 p-5">
            <h3 className="text-lg font-semibold">Research summary</h3>
            <p className="mt-3 text-slate-200">{research.summary}</p>
            <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-300">{research.observations.map((observation, i) => <li key={i}>{observation}</li>)}</ul>
            <h4 className="mt-5 font-medium">Evidence limitations</h4>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-amber-200">{research.limitations.map((limitation, i) => <li key={i}>{limitation}</li>)}</ul>
          </div>}
          {quantitative && <div className="rounded-xl border border-slate-600 bg-slate-800/50 p-5"><h3 className="font-semibold">Quantitative metrics unavailable</h3><p className="mt-2 text-sm text-slate-300">{quantitative.reason}</p></div>}

          <div className="rounded-xl border border-white/10 bg-white/5 p-5">
            <h3 className="text-lg font-semibold">SEC filing events</h3>
            <p className="mt-1 text-sm text-slate-400">A filing type alone does not indicate good or bad news. These events are excluded from the news-tone score.</p>
            {filings.length === 0 ? <p className="mt-4 text-sm text-slate-300">No saved filing events are available.</p> : <ul className="mt-4 divide-y divide-white/10">{filings.map((filing, i) => <li key={`${filing.url}-${i}`} className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-medium">{filing.form_type} · {filing.description}</span>{safeSourceUrl(filing.url) && <a href={safeSourceUrl(filing.url)} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-sm text-blue-300">Read filing <ExternalLink className="h-3 w-3" /></a>}</div>
              <p className="mt-1 text-sm text-slate-400">Filed: {filing.filing_date ?? 'Unknown'}</p>
            </li>)}</ul>}
          </div>
        </>}

        {getAuthSession()?.role === 'admin' && stockData && <div className="border-t border-white/10 pt-5">
          {!confirmDelete ? <button disabled={refreshing} onClick={() => setConfirmDelete(true)} className="flex items-center gap-1 text-sm text-red-300"><X className="h-4 w-4" />Delete saved research for {symbol}</button> : <div className="flex flex-wrap items-center gap-3 text-sm"><p>Delete all saved research for {symbol}?</p><button disabled={deleting || refreshing} onClick={deleteStock} className="rounded bg-red-700 px-3 py-2">{deleting ? 'Deleting…' : 'Delete'}</button><button disabled={deleting} onClick={() => setConfirmDelete(false)} className="rounded bg-slate-700 px-3 py-2">Cancel</button></div>}
        </div>}
      </div>
    </section>
  )
}

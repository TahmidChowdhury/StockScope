'use client'

import AnimatedSelect from '@/components/ui/AnimatedSelect'

import AnimatedAccordion from '@/components/ui/AnimatedAccordion'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '@/lib/api'

interface SecFact {
  fact_id: string
  cik: string | null
  taxonomy: string | null
  concept: string | null
  label: string | null
  unit: string | null
  value: number | null
  start: string | null
  end: string | null
  filed: string | null
  accession: string | null
  form: string | null
  fiscal_year: number | null
  fiscal_period: string | null
  frame: string | null
  period_kind: 'instant' | 'duration' | 'unknown'
  duration_days: number | null
  validation_issues: string[] | null
  source_url: string | null
  filing_url: string | null
  raw_fact?: Record<string, unknown>
}

interface SecFactsResponse {
  symbol: string
  configured: boolean
  saved: boolean
  status: string
  cik: string | null
  entity_name: string | null
  facts: SecFact[]
  total: number
  total_saved: number
  offset: number
  limit: number
  has_more: boolean
  concepts: { key: string; taxonomy: string | null; concept: string | null; label: string | null; units: string[]; count: number }[]
  metadata: {
    collected_at?: string | null
    retrieved_at?: string | null
    as_of?: string | null
    as_of_basis?: string | null
    latest_filed?: string | null
    facts_latest_filed?: string | null
    filings_latest_filed?: string | null
    companyfacts_url?: string | null
    submissions_url?: string | null
    concept_filter?: string[] | null
    limitations?: string[] | null
    collections?: Record<string, { status: string; error?: string | null; from_cache?: boolean; retrieved_at?: string | null; record_count?: number }>
  }
}

interface RefreshStatus {
  status: string
  message?: string
  providers?: Record<string, { status: string; count: number; message: string }>
}

function secLink(value?: string | null): string | undefined {
  if (!value) return undefined
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && ['www.sec.gov', 'data.sec.gov', 'sec.gov'].includes(url.hostname) ? url.href : undefined
  } catch {
    return undefined
  }
}

function timestamp(value?: string | null) {
  if (!value) return 'Unknown'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString()
}

function pause(signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) return reject(new DOMException('Aborted', 'AbortError'))
    const cancel = () => {
      clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    }
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', cancel)
      resolve()
    }, 1500)
    signal.addEventListener('abort', cancel, { once: true })
  })
}

export default function SecFactsPanel({ symbol }: { symbol: string }) {
  const [data, setData] = useState<SecFactsResponse | null>(null)
  const [concept, setConcept] = useState('')
  const [unit, setUnit] = useState('')
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [readFailed, setReadFailed] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const loadController = useRef<AbortController | null>(null)
  const refreshController = useRef<AbortController | null>(null)
  const pageSize = 50

  const loadSaved = useCallback(async (signal: AbortSignal) => {
    const query = new URLSearchParams({ offset: String(offset), limit: String(pageSize) })
    if (concept) query.set('concept', concept)
    if (unit) query.set('unit', unit)
    const response = await apiFetch(`/api/fundamentals/${encodeURIComponent(symbol)}/sec-facts?${query}`, { signal })
    if (!response.ok) throw new Error('Saved SEC facts could not be read. Please try again.')
    return await response.json() as SecFactsResponse
  }, [symbol, concept, unit, offset])

  useEffect(() => {
    const controller = new AbortController()
    loadController.current = controller
    let timedOut = false
    const timeout = setTimeout(() => { timedOut = true; controller.abort() }, 20_000)
    setLoading(true)
    setReadFailed(false)
    setError(null)
    loadSaved(controller.signal)
      .then(next => { if (!controller.signal.aborted) setData(next) })
      .catch(reason => {
        if (loadController.current !== controller) return
        if (timedOut || !controller.signal.aborted) {
          setReadFailed(true)
          setError(timedOut ? 'Reading saved SEC facts timed out. Try reopening this page.' : reason instanceof Error ? reason.message : 'Saved SEC facts are unavailable.')
        }
      })
      .finally(() => {
        clearTimeout(timeout)
        if (loadController.current === controller && (!controller.signal.aborted || timedOut)) setLoading(false)
      })
    return () => {
      clearTimeout(timeout)
      controller.abort()
      if (loadController.current === controller) loadController.current = null
    }
  }, [loadSaved])

  useEffect(() => {
    setConcept('')
    setUnit('')
    setOffset(0)
    setData(null)
    setMessage(null)
    setRefreshing(false)
    return () => {
      refreshController.current?.abort()
      refreshController.current = null
    }
  }, [symbol])

  const units = useMemo(() => {
    const options = data?.concepts.filter(item => !concept || item.key === concept) ?? []
    return [...new Set(options.flatMap(item => item.units))].sort()
  }, [data, concept])

  const refresh = async () => {
    loadController.current?.abort()
    refreshController.current?.abort()
    const controller = new AbortController()
    refreshController.current = controller
    let timedOut = false
    const timeout = setTimeout(() => { timedOut = true; controller.abort() }, 240_000)
    const previousCollection = data?.metadata.collected_at
    setRefreshing(true)
    setLoading(false)
    setError(null)
    setMessage('Requesting SEC facts and recent filing records…')
    try {
      const response = await apiFetch('/api/stocks/analyze', {
        method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, sources: ['sec_facts'] }),
      })
      if (!response.ok) throw new Error(response.status === 429 ? 'Other refreshes are running. Try again after one finishes.' : 'Could not start the SEC refresh.')
      while (!controller.signal.aborted) {
        await pause(controller.signal)
        const statusResponse = await apiFetch(`/api/stocks/${encodeURIComponent(symbol)}/status`, { signal: controller.signal })
        if (!statusResponse.ok) throw new Error('Refresh progress is unavailable. Saved facts remain unchanged; check again later.')
        const status: RefreshStatus = await statusResponse.json()
        if (controller.signal.aborted) return
        setMessage(status.message || 'Collecting SEC evidence…')
        if (['completed', 'partial', 'failed'].includes(status.status)) {
          if (status.status === 'failed') throw new Error(status.message || 'The SEC refresh could not be completed. Saved facts remain unchanged.')
          const outcome = status.providers?.sec_facts
          if (!outcome) throw new Error('The existing refresh did not include SEC facts. Start a SEC refresh after it finishes.')
          if (!['completed', 'partial'].includes(outcome.status)) throw new Error(`${outcome.message || 'SEC returned no new financial evidence.'} Saved facts have not been refreshed.`)
          const saved = await loadSaved(controller.signal)
          if (controller.signal.aborted) return
          setData(saved)
          setReadFailed(false)
          const changed = saved.saved && saved.metadata.collected_at !== previousCollection
          setMessage(changed
            ? `${outcome.status === 'partial' ? 'Partial SEC collection' : 'SEC evidence saved'}. Check retrieval and filing dates below; cached SEC responses may be reused.`
            : 'SEC collection finished without a new financial snapshot. Any saved facts below are unchanged.')
          return
        }
      }
    } catch (reason) {
      if (refreshController.current === controller && (!controller.signal.aborted || timedOut)) {
        setError(timedOut ? 'The SEC refresh is taking longer than expected. The server may still be working; reopen this page to check saved results.' : reason instanceof Error ? reason.message : 'SEC refresh failed.')
        setMessage(null)
      }
    } finally {
      clearTimeout(timeout)
      if (refreshController.current === controller) {
        refreshController.current = null
        setRefreshing(false)
      }
    }
  }

  const currentData = data?.symbol === symbol.toUpperCase() ? data : null
  const busy = loading || refreshing
  return (
    <section aria-labelledby="sec-facts-heading" className="rounded-xl border border-white/20 bg-white/5 p-5 text-white sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id="sec-facts-heading" className="text-2xl font-semibold">SEC reported financial facts</h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-300">Read the company’s reported values alongside the provider financial metrics. These are raw filing facts, not TTM totals. A quarter label can accompany a year-to-date value: compare the exact dates and units.</p>
        </div>
        <button type="button" onClick={() => void refresh()} disabled={busy || !currentData?.configured} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50">
          {refreshing ? 'Collecting SEC evidence…' : 'Refresh SEC evidence'}
        </button>
      </div>
      {error && <p role="alert" className="mt-4 rounded-lg bg-red-950/60 p-3 text-sm text-red-200">{error}</p>}
      {message && <p role="status" className="mt-4 rounded-lg bg-blue-950/60 p-3 text-sm text-blue-200">{message}</p>}
      {loading && <p role="status" className="mt-4 text-sm text-slate-300">Loading saved SEC evidence…</p>}
      {currentData && <>
        {!currentData.configured && <p className="mt-4 text-sm text-amber-200">SEC collection needs a real contact email configured by the app operator. Previously saved facts remain readable.</p>}
        {!currentData.saved && !loading && <p className="mt-4 text-sm text-slate-300">No SEC financial snapshot is saved for {symbol}. {currentData.configured ? 'Use Refresh SEC evidence to collect one.' : 'Collection will be available after configuration.'}</p>}
        {currentData.saved && <>
          <div className="mt-4 space-y-1 text-sm text-slate-300">
            <p>{currentData.entity_name || symbol} · CIK {currentData.cik ?? 'Unknown'} · Saved collection: {currentData.status}</p>
            <p>Oldest source retrieval: {timestamp(currentData.metadata.retrieved_at)} · Collection attempted: {timestamp(currentData.metadata.collected_at)}</p>
            <p>Latest financial fact filing date: {currentData.metadata.facts_latest_filed ?? 'Unknown'} · Latest recent submission: {currentData.metadata.filings_latest_filed ?? 'Unknown'}</p>
            <p>Repeated periods can represent amendments or later filings. Each reported version stays separate.</p>
            {currentData.metadata.concept_filter && <p>Stored concepts are limited by a configured allowlist ({currentData.metadata.concept_filter.length} concepts).</p>}
            <div className="flex flex-wrap gap-4">
              {secLink(currentData.metadata.companyfacts_url) && <a href={secLink(currentData.metadata.companyfacts_url)} target="_blank" rel="noreferrer" className="text-blue-300 underline">SEC company facts source</a>}
              {secLink(currentData.metadata.submissions_url) && <a href={secLink(currentData.metadata.submissions_url)} target="_blank" rel="noreferrer" className="text-blue-300 underline">SEC submissions source</a>}
            </div>
          </div>
          <div className="mt-5 flex flex-wrap items-end gap-4">
            <label className="min-w-0 flex-1 text-sm text-slate-300">Reported concept
              <AnimatedSelect value={concept} disabled={refreshing} onValueChange={value => { setConcept(value); setUnit(''); setOffset(0) }} className="mt-1 block w-full rounded-lg border border-white/20 bg-slate-900 p-2 text-white">
                <option value="">All saved concepts</option>
                {currentData.concepts.map(item => <option key={item.key} value={item.key}>{item.label || item.concept} ({item.key}) · {item.count} versions</option>)}
              </AnimatedSelect>
            </label>
            <label className="text-sm text-slate-300">Unit
              <AnimatedSelect value={unit} disabled={refreshing} onValueChange={value => { setUnit(value); setOffset(0) }} className="mt-1 block w-full rounded-lg border border-white/20 bg-slate-900 p-2 text-white">
                <option value="">All units</option>
                {units.map(value => <option key={value} value={value}>{value}</option>)}
              </AnimatedSelect>
            </label>
          </div>
          {!loading && !readFailed && <>
            <p className="mt-4 text-sm text-slate-400">{currentData.total.toLocaleString()} matching reported versions · {currentData.total_saved.toLocaleString()} saved facts across {currentData.concepts.length} concepts</p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <caption className="sr-only">SEC facts for {symbol}, ordered by filing date. Different units and filing versions are not combined.</caption>
                <thead className="border-b border-white/20 text-slate-300"><tr><th className="p-3">Concept</th><th className="p-3">Reported value / unit</th><th className="p-3">Exact period</th><th className="p-3">Filing version</th><th className="p-3">Filing context</th></tr></thead>
                <tbody>{currentData.facts.map(fact => <tr key={fact.fact_id} className="border-b border-white/10 align-top">
                  <td className="max-w-xs p-3"><p>{fact.label || fact.concept || 'Unknown concept'}</p><p className="mt-1 break-words text-xs text-slate-400">{fact.taxonomy}:{fact.concept}</p>{(fact.validation_issues?.length ?? 0) > 0 && <p className="mt-2 text-xs text-amber-200">Incomplete record: {fact.validation_issues?.map(issue => issue.replaceAll('_', ' ')).join('; ')}</p>}</td>
                  <td className="p-3 tabular-nums">{fact.value != null && Number.isFinite(fact.value) ? fact.value.toLocaleString('en-US', { maximumSignificantDigits: 15 }) : 'Unknown'}<p className="mt-1 text-xs text-slate-400">{fact.unit ?? 'Unknown unit'}</p></td>
                  <td className="whitespace-nowrap p-3">{fact.period_kind === 'instant' ? `At ${fact.end ?? 'unknown date'}` : `${fact.start ?? 'Unknown start'} → ${fact.end ?? 'Unknown end'}`}<p className="mt-1 text-xs text-slate-400">{fact.duration_days != null ? `${fact.duration_days} days` : fact.period_kind === 'instant' ? 'Point in time' : 'Period unknown'}</p></td>
                  <td className="p-3"><p>{fact.form ?? 'Unknown form'} · {fact.filed ?? 'Unknown filing date'}</p>{secLink(fact.filing_url) ? <a href={secLink(fact.filing_url)} target="_blank" rel="noreferrer" className="mt-1 block text-xs text-blue-300 underline">{fact.accession || 'Open filing'}</a> : <p className="mt-1 text-xs text-slate-400">{fact.accession ?? 'Accession unavailable'}</p>}</td>
                  <td className="p-3 text-xs text-slate-400">FY {fact.fiscal_year ?? 'unknown'} · {fact.fiscal_period ?? 'Period label unknown'}<p className="mt-1">Frame: {fact.frame ?? 'Not supplied'}</p></td>
                </tr>)}</tbody>
              </table>
              {currentData.facts.length === 0 && <p className="py-6 text-sm text-slate-300">No saved facts match these filters.</p>}
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
              <p className="text-slate-400">{currentData.total > 0 ? `${Math.min(currentData.offset + 1, currentData.total)}–${Math.min(currentData.offset + currentData.facts.length, currentData.total)} of ${currentData.total}` : '0 records'}</p>
              <div className="flex gap-2">
                <button type="button" disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))} className="rounded border border-white/20 px-3 py-2 disabled:opacity-40">Previous</button>
                <button type="button" disabled={busy || !currentData.has_more} onClick={() => setOffset(offset + pageSize)} className="rounded border border-white/20 px-3 py-2 disabled:opacity-40">Next</button>
              </div>
            </div>
          </>}
          <AnimatedAccordion className="mt-5 text-sm text-slate-400" triggerClassName="text-slate-300" title="Coverage and source limitations">
            <ul className="mt-2 list-disc space-y-1 pl-5">{(currentData.metadata.limitations ?? []).map(item => <li key={item}>{item}</li>)}</ul>
            {Object.entries(currentData.metadata.collections ?? {}).map(([name, collection]) => <p key={name} className="mt-2">{name.replaceAll('_', ' ')}: {collection.status}{collection.from_cache ? ' · cached source response' : ''}{collection.error ? ` · ${collection.error}` : ''}</p>)}
          </AnimatedAccordion>
        </>}
      </>}
    </section>
  )
}

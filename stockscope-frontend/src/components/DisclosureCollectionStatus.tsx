'use client'

import AnimatedAccordion from '@/components/ui/AnimatedAccordion'

import { useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, CheckCircle2, Clock3, Database, RefreshCw } from 'lucide-react'
import { getAuthSession } from '@/lib/api'
import { tradingRequest, type DisclosureCollection } from '@/lib/trading'

const collectionKey = ['disclosure-collection']
const pollingLimit = 5 * 60_000

function timestamp(value?: string | null) {
  if (!value) return 'Not yet'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Unavailable' : date.toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
  })
}

function safeLink(value?: string) {
  try {
    const url = new URL(value || '')
    return url.protocol === 'https:' ? url.href : undefined
  } catch { return undefined }
}

/** Collection is a server task: navigating away does not cancel it. */
export default function DisclosureCollectionStatus({ onCollected }: { onCollected?: () => void }) {
  const client = useQueryClient()
  const pollingStarted = useRef<number | null>(null)
  const awaitingAttempt = useRef<{ at: number; attempt: string | null; success: string | null } | null>(null)
  const lastSuccess = useRef<string | null | undefined>(undefined)
  const query = useQuery({
    queryKey: collectionKey,
    queryFn: () => tradingRequest<DisclosureCollection>('/congress/collection'),
    staleTime: 30_000,
    retry: 1,
    refetchInterval: (current) => {
      const waiting = awaitingAttempt.current
      if (waiting && (current.state.data?.enabled === false || current.state.data?.last_attempt !== waiting.attempt || current.state.data?.last_success !== waiting.success || Date.now() - waiting.at >= pollingLimit)) awaitingAttempt.current = null
      const active = current.state.data?.state === 'running'
      if (!active && !awaitingAttempt.current) { pollingStarted.current = null; return false }
      pollingStarted.current ??= Date.now()
      return Date.now() - pollingStarted.current < pollingLimit ? 5_000 : false
    },
  })
  const refresh = useMutation({
    mutationFn: () => tradingRequest<DisclosureCollection>('/congress/collection/refresh', {}),
    onSuccess: (data) => {
      pollingStarted.current = Date.now()
      awaitingAttempt.current = { at: Date.now(), attempt: data.last_attempt, success: data.last_success }
      client.setQueryData(collectionKey, data)
      void query.refetch()
    },
  })
  const data = query.data
  const running = data?.enabled && (data.state === 'running' || Boolean(awaitingAttempt.current && Date.now() - awaitingAttempt.current.at < pollingLimit))
  const failed = data?.state === 'failed' || data?.state === 'interrupted'
  const source = data?.source
  const sourceUrl = safeLink(source?.source_url)
  const licenseUrl = safeLink(source?.license_url)
  const outdated = Boolean(data?.enabled && data.last_success && Date.now() - Date.parse(data.last_success) > (data.interval_hours || 6) * 3 * 60 * 60_000)
  const admin = getAuthSession()?.role === 'admin'
  const label = running ? 'Collecting' : !data?.enabled ? 'Paused' : failed ? 'Needs attention' : outdated ? 'Update delayed' : data.last_success ? 'Scheduled' : 'Ready to collect'

  useEffect(() => {
    const success = data?.last_success
    if (!success || (lastSuccess.current && Date.parse(success) <= Date.parse(lastSuccess.current))) return
    // Advance the guard before notifying a parent that may immediately rerender.
    lastSuccess.current = success
    void client.invalidateQueries({ queryKey: ['congress'] })
    onCollected?.()
  }, [client, data, onCollected])

  if (query.isPending) return <div role="status" className="surface flex items-center gap-2 p-4 text-xs text-slate-400"><Database className="h-4 w-4 text-violet-300" /> Checking automatic collection…</div>
  if (!data) return <div role="alert" className="surface flex flex-wrap items-center justify-between gap-3 p-4 text-xs text-slate-400"><p>Collection status is unavailable. Saved disclosures can still be browsed.</p><button className="button-secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>Check again</button></div>

  return <section aria-label="Automatic disclosure collection" className="surface overflow-hidden">
    <div className="flex flex-wrap items-start justify-between gap-4 p-4 sm:p-5">
      <div className="flex min-w-0 gap-3">
        <div className="h-fit rounded-xl border border-violet-300/15 bg-violet-300/10 p-2.5"><Database className="h-4 w-4 text-violet-300" /></div>
        <div>
          <div className="flex flex-wrap items-center gap-2.5"><h2 className="text-sm font-semibold text-slate-200">Automatic collection</h2><span role="status" className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium ${failed || outdated ? 'bg-amber-300/10 text-amber-200' : data.enabled ? 'bg-emerald-300/10 text-emerald-300' : 'bg-white/5 text-slate-400'}`}>
            {running ? <RefreshCw className="h-3 w-3 animate-spin" /> : data.enabled && data.last_success && !failed && !outdated ? <CheckCircle2 className="h-3 w-3" /> : <Clock3 className="h-3 w-3" />}{label}
          </span></div>
          <p className="mt-1.5 text-xs leading-5 text-slate-400">{data.row_count.toLocaleString()} collected records · {data.enabled ? `Checks every ${data.interval_hours || 6} hours` : 'Saved activity is available'}</p>
        </div>
      </div>
      <div className="flex gap-2">
        {running && <button disabled={query.isFetching} className="button-secondary" onClick={() => { pollingStarted.current = Date.now(); void query.refetch() }}>Check status</button>}
        {admin && data.enabled && <button className="button-secondary" disabled={running || refresh.isPending} onClick={() => refresh.mutate()}><RefreshCw className={`h-3.5 w-3.5 ${running || refresh.isPending ? 'animate-spin' : ''}`} />{running || refresh.isPending ? 'Collecting…' : 'Refresh now'}</button>}
      </div>
    </div>

    {(failed || query.isError || refresh.isError) && <div role="alert" className="mx-4 mb-4 rounded-lg border border-amber-300/15 bg-amber-300/5 px-3 py-2 text-xs leading-5 text-amber-200 sm:mx-5">
      {refresh.isError ? refresh.error.message : query.isError ? 'Status could not be updated. The last known state is shown.' : data.last_error || 'The last collection did not finish. The next scheduled check will retry.'}
      {Boolean(data.row_count) && <span> Saved records remain available.</span>}
    </div>}



    <AnimatedAccordion className="border-t border-white/[0.06] px-4 py-3 text-xs sm:px-5" triggerClassName="text-slate-400 hover:text-violet-200" title="Collection details & sources">
      <div className="mt-3 space-y-2 leading-5 text-slate-500">
          <p className="mt-1.5 max-w-2xl text-xs leading-5 text-slate-400">{data.enabled ? `Checks a public House and Senate dataset every ${data.interval_hours || 6} hours. New disclosures appear here automatically.` : 'Scheduled collection is paused. Previously collected records and CSV imports remain available.'}</p>
          <p className="mt-1 text-[11px] leading-5 text-slate-500">Filing dates estimate availability. “First observed” is when StockScope found a transaction.</p>
          {source?.coverage_end && <p className="mt-1 text-[11px] leading-5 text-slate-400">Latest available filing date {source.coverage_end}{source.source_checked_at ? ` · Publisher checked ${timestamp(source.source_checked_at)}` : ''}</p>}
    <dl className="grid grid-cols-2 gap-x-5 gap-y-3 py-3 text-xs sm:grid-cols-3">
      <div><dt className="text-[10px] text-slate-500">Last successful check</dt><dd className="mt-1 text-slate-300">{timestamp(data.last_success)}</dd></div>
      <div><dt className="text-[10px] text-slate-500">Next check</dt><dd className="mt-1 text-slate-300">{running ? 'In progress' : data.enabled ? data.next_run ? timestamp(data.next_run) : 'Starting shortly' : 'Paused'}</dd></div>
      <div><dt className="text-[10px] text-slate-500">Collected records, including revisions</dt><dd className="mt-1 text-slate-300">{data.row_count.toLocaleString()}</dd></div>
    </dl>
        <p>Third-party normalized filing data can contain extraction errors. Confirm transactions in the original linked filing. Reported amount ranges do not show exact allocations or current holdings.</p>
        <div className="flex flex-wrap gap-x-5 gap-y-1 text-slate-400">
          {source?.years?.length ? <span>Collection years {source.years.join(', ')}</span> : null}
          {source?.coverage_start && <span>Dataset window {source.coverage_start}–{source.coverage_end || 'present'}</span>}
          {source?.generated_at && <span>Publisher updated {timestamp(source.generated_at)}</span>}
          {source?.revision && <span>Snapshot <code className="text-[10px]">{source.revision.slice(0, 12)}</code></span>}
        </div>
        {source?.excluded_counts && Object.values(source.excluded_counts).some((count) => count > 0) && <p>Some source rows are excluded when the transaction, symbol, or dates cannot be used reliably.</p>}
        <p>Automatic records use the filing day as an estimate, not a verified publication timestamp. Tests default to the date StockScope first observed them; historical filing-date tests require an explicit choice. CSV dates remain importer supplied.</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {sourceUrl && <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-violet-300 hover:underline">{source?.provider === 'congressional_stock_trades' ? 'Congressional Stock Trades dataset' : source?.provider || 'Dataset source'}<ArrowUpRight className="h-3 w-3" /></a>}
          {licenseUrl && <a href={licenseUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-violet-300 hover:underline">Source license<ArrowUpRight className="h-3 w-3" /></a>}
        </div>
        <p>For personal research. Review the source terms before redistributing disclosure data.</p>
      </div>
    </AnimatedAccordion>
  </section>
}

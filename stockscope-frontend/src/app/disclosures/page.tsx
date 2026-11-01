'use client'

import AnimatedSelect from '@/components/ui/AnimatedSelect'
import AnimatedAccordion from '@/components/ui/AnimatedAccordion'
import DisclosureRecord from '@/components/DisclosureRecord'

import { Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, FileText, FlaskConical, Landmark, Search } from 'lucide-react'
import AppShell from '@/components/AppShell'
import DisclosureCollectionStatus from '@/components/DisclosureCollectionStatus'
import { companyResearchHref } from '@/lib/research-workflow'
import { DisclosureResearch, tradingRequest } from '@/lib/trading'

const pageSize = 20

export default function DisclosuresPage() {
  return <Suspense fallback={<div className="min-h-dvh bg-[#111513]" />}><DisclosureWorkspace /></Suspense>
}

function DisclosureWorkspace() {
  const search = useSearchParams()
  const router = useRouter()
  const params = new URLSearchParams()
  for (const key of ['q', 'member', 'symbol', 'side']) {
    const value = search.get(key)?.trim()
    if (value) params.set(key, key === 'symbol' ? value.toUpperCase() : value)
  }
  const requestedOffset = Number(search.get('offset') || 0)
  const offset = Number.isSafeInteger(requestedOffset) && requestedOffset >= 0 && requestedOffset <= 60000 ? requestedOffset : 0
  if (offset) params.set('offset', String(offset))
  const queryString = params.toString()
  const returnTo = `/disclosures${queryString ? `?${queryString}` : ''}`
  const member = params.get('member') || ''
  const symbol = params.get('symbol') || ''
  const side = params.get('side') || ''
  const query = useQuery({
    queryKey: ['congress', 'research', queryString],
    queryFn: async () => {
      const response = await tradingRequest<DisclosureResearch>(`/congress?${queryString}&limit=${pageSize}`)
      if (!response.summary || !response.filtered_summary || !Array.isArray(response.member_profiles) || !Array.isArray(response.symbols)) {
        throw new Error('This version of the disclosure list is unavailable. Try again later.')
      }
      return response
    },
  })
  const data = query.data
  const summary = data?.filtered_summary
  const profile = data?.member_profiles.find((person) => person.member === member)
  const hasFilters = ['q', 'member', 'symbol', 'side'].some((key) => params.has(key))
  function navigate(changes: Record<string, string>) {
    const next = new URLSearchParams(queryString)
    next.delete('offset')
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    router.push(`/disclosures${next.size ? `?${next}` : ''}`, { scroll: false })
  }
  function testMember(name: string) {
    const next = new URLSearchParams({ tab: 'backtest', member: name, handoff: crypto.randomUUID() })
    router.push(`/trading?${next}`)
  }
  return <AppShell><div className="space-y-6">
    <header>
      <h1 className="page-title">Congressional disclosures</h1>
      <p className="mt-2 text-sm text-slate-400">Reported transactions by members of Congress and their households.</p>
    </header>
    <details className="border-y border-white/[0.08] text-sm">
      <summary className="cursor-pointer py-3 font-medium text-sage-300">Coverage and collection</summary>
      <div className="space-y-3 pb-4">
        {summary && <p className="text-xs leading-5 text-slate-400">
          {summary.member_count.toLocaleString()} members · {summary.symbol_count.toLocaleString()} companies and assets
          {summary.average_lag_days != null && ` · Average reporting lag ${summary.average_lag_days.toFixed(1)} days`}
        </p>}
        <DisclosureCollectionStatus />
        <Link href="/trading?tab=congress" className="inline-flex min-h-11 items-center gap-2 text-xs text-sage-300 hover:underline"><FileText className="h-4 w-4" /> Manage imports</Link>
      </div>
    </details>
    {member && profile ? <section className="surface overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-5 p-5 sm:p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-sage-300/15 bg-sage-300/10 text-lg text-sage-200">{member.split(/\s+/).map((word) => word[0]).slice(0, 2).join('')}</div>
          <div><p className="eyebrow">Member activity</p><h2 className="mt-1 text-lg font-semibold">{member}</h2><p className="mt-1 text-xs text-slate-400">{profile.total} transactions · {profile.buys} buys · {profile.sells} sells · All available records</p></div>
        </div>
        <button className="button-primary" onClick={() => testMember(member)}><FlaskConical className="h-4 w-4" /> Test following this member</button>
      </div>
      <p className="border-t border-white/5 px-5 py-3 text-xs leading-5 text-slate-400">This activity can include a spouse or dependent. Reported ranges do not establish exact allocations, current holdings, or the member’s investment return.</p>
    </section> : null}

    <section className="surface overflow-hidden" aria-labelledby="activity-title">
      <div className="border-b border-white/[0.07] p-4 sm:p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><h2 id="activity-title" className="font-semibold">Transaction feed</h2><p className="text-xs text-slate-400">{summary && `${summary.total.toLocaleString()} records · `}Newest reported availability first</p></div>
        <form key={params.get('q') || ''} onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); navigate({ q: String(form.get('q') || '').trim() }) }} className="flex items-end gap-2">
          <label className="min-w-0 flex-1 text-xs text-slate-400">Search disclosures
            <input name="q" defaultValue={params.get('q') || ''} maxLength={120} placeholder="Member, owner, ticker…" className="field-input" />
          </label>
          <button className="button-secondary shrink-0" aria-label="Search disclosures"><Search className="h-4 w-4" /></button>
        </form>
        <AnimatedAccordion className="mt-3" triggerClassName="text-xs text-slate-300" title={`Filters${[member, symbol, side].filter(Boolean).length ? ` · ${[member, symbol, side].filter(Boolean).length} active` : ''}`}>
          <div className="grid grid-cols-1 gap-4 pb-3 pt-2 sm:grid-cols-3">
            <label className="min-w-0 text-xs text-slate-400">Member
              <AnimatedSelect className="field-input" value={member} onValueChange={(value) => navigate({ member: value })}>
                <option value="">All members</option>{member && !data?.members.includes(member) && <option>{member}</option>}{data?.members.map((name) => <option key={name}>{name}</option>)}
              </AnimatedSelect>
            </label>
            <label className="min-w-0 text-xs text-slate-400">Symbol
              <AnimatedSelect className="field-input" value={symbol} onValueChange={(value) => navigate({ symbol: value })}>
                <option value="">All symbols</option>{symbol && !data?.symbols.includes(symbol) && <option>{symbol}</option>}{data?.symbols.map((name) => <option key={name}>{name}</option>)}
              </AnimatedSelect>
            </label>
            <label className="min-w-0 text-xs text-slate-400">Activity
              <AnimatedSelect className="field-input" value={side} onValueChange={(value) => navigate({ side: value })}><option value="">Buys & sells</option><option value="buy">Buys</option><option value="sell">Sells</option></AnimatedSelect>
            </label>
          </div>
        </AnimatedAccordion>
        {hasFilters && <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          {['q', 'member', 'symbol', 'side'].map(key => params.get(key) && <button key={key} onClick={() => navigate({ [key]: '' })} aria-label={`Remove ${key} filter: ${params.get(key)}`} className="min-h-11 max-w-full rounded-lg border border-white/10 px-3 text-left text-slate-300">{params.get(key)} <span aria-hidden="true" className="ml-2 text-slate-500">×</span></button>)}
          <button className="min-h-11 px-2 text-sage-300 hover:underline" onClick={() => router.push('/disclosures', { scroll: false })}>Clear all</button>
        </div>}
      </div>

      {query.isPending ? <p role="status" className="p-6 text-sm text-slate-400">Loading disclosed activity…</p> : query.isError ? <div role="alert" className="p-6 text-sm text-amber-200"><p>Disclosures could not be loaded. {query.error.message}</p><button onClick={() => void query.refetch()} className="button-secondary mt-4">Try again</button></div> : !data?.records.length ? <div className="mx-auto max-w-xl px-6 py-12 text-center">
        <Landmark className="mx-auto mb-4 h-8 w-8 text-sage-300/70" />
        <h3 className="text-lg font-medium">{data?.summary.total ? 'No activity matches this view' : 'No disclosures collected yet'}</h3>
        <p className="mt-3 text-sm leading-6 text-slate-400">{data?.summary.total ? 'Try another member or ticker, or clear the filters.' : data?.collection?.enabled ? 'The next scheduled check will look for transactions. An administrator can also refresh the collection or import a CSV.' : 'An administrator can import congressional transactions with links to the filings.'}</p>
        <Link className="button-primary mt-6" href={data?.summary.total ? '/disclosures' : '/trading?tab=congress'}>{data?.summary.total ? 'View all disclosures' : 'Open disclosure imports'}<ArrowRight className="h-4 w-4" /></Link>
      </div> : <>
        <div className="divide-y divide-white/[0.06]">{data.records.map((record) => <DisclosureRecord key={record.disclosure_id} record={record} companyHref={companyResearchHref(record.symbol, returnTo)} onMember={(name) => navigate({ member: name })} />)}</div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.07] px-5 py-4 text-xs text-slate-400"><span>{offset + 1}–{Math.min(offset + data.records.length, data.total)} of {data.total} disclosures</span><div className="flex gap-2"><button disabled={!offset} className="button-secondary disabled:opacity-30" onClick={() => navigate({ offset: String(Math.max(0, offset - pageSize)) })}>Previous</button><button disabled={offset + pageSize >= data.total} className="button-secondary disabled:opacity-30" onClick={() => navigate({ offset: String(offset + pageSize) })}>Next</button></div></div>
      </>}
    </section>

  </div></AppShell>
}

'use client'

import AnimatedSelect from '@/components/ui/AnimatedSelect'

import { Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ArrowUpRight, Clock3, FileText, FlaskConical, Landmark, Search, Users } from 'lucide-react'
import AppShell from '@/components/AppShell'
import DisclosureCollectionStatus from '@/components/DisclosureCollectionStatus'
import { companyResearchHref } from '@/lib/research-workflow'
import { DisclosureResearch, disclosureChamberLabel, disclosureOwnerLabel, tradingDate, tradingRequest } from '@/lib/trading'

const pageSize = 20

export default function DisclosuresPage() {
  return <Suspense fallback={<div className="min-h-dvh bg-[#101218]" />}><DisclosureWorkspace /></Suspense>
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
        throw new Error('This view needs the updated disclosure API. Try again after the backend update finishes.')
      }
      return response
    },
  })
  const data = query.data
  const summary = data?.filtered_summary
  const profile = data?.member_profiles.find((person) => person.member === member)
  const people = [...(data?.member_profiles || [])].sort((a, b) => (b.latest_available_date || '').localeCompare(a.latest_available_date || '') || a.member.localeCompare(b.member)).slice(0, 6)
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
    <header className="flex flex-wrap items-start justify-between gap-5">
      <div>
        <p className="eyebrow">Follow the evidence</p>
        <h1 className="page-title mt-2">Disclosed activity</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Explore Congress transactions, research the companies, and test a following rule with explicit disclosure timing.</p>
      </div>
      <Link href="/trading?tab=congress" className="button-secondary"><FileText className="h-4 w-4" /> Manage imports</Link>
    </header>

    <DisclosureCollectionStatus />

    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {[
        { label: 'Matching disclosures', value: summary?.total, Icon: FileText },
        { label: 'Members in view', value: summary?.member_count, Icon: Users },
        { label: 'Companies & assets', value: summary?.symbol_count, Icon: Landmark },
        { label: 'Average reported lag', value: summary?.average_lag_days == null ? undefined : `${summary.average_lag_days.toFixed(1)} days`, Icon: Clock3 },
      ].map(({ label, value, Icon }) => <div key={label} className="surface p-4 sm:p-5">
        <div className="flex items-center justify-between gap-2 text-xs text-slate-400"><span>{label}</span><Icon className="h-4 w-4 text-violet-300/70" /></div>
        <p className="mt-3 text-2xl font-semibold tracking-tight">{value ?? '—'}</p>
      </div>)}
    </div>

    {member && profile ? <section className="surface overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-5 bg-gradient-to-r from-violet-500/10 to-transparent p-5 sm:p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-violet-300/15 bg-violet-300/10 text-lg text-violet-200">{member.split(/\s+/).map((word) => word[0]).slice(0, 2).join('')}</div>
          <div><p className="eyebrow">Member activity</p><h2 className="mt-1 text-lg font-semibold">{member}</h2><p className="mt-1 text-xs text-slate-400">{profile.total} transactions · {profile.buys} buys · {profile.sells} sells · All available records</p></div>
        </div>
        <button className="button-primary" onClick={() => testMember(member)}><FlaskConical className="h-4 w-4" /> Test following this member</button>
      </div>
      <p className="border-t border-white/5 px-5 py-3 text-xs leading-5 text-slate-400">This activity can include a spouse or dependent. Reported ranges do not establish exact allocations, current holdings, or the member’s investment return.</p>
    </section> : !hasFilters && people.length > 0 ? <section aria-labelledby="people-title">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 id="people-title" className="text-sm font-semibold">Explore members</h2><p className="text-xs text-slate-500">Recent filing / imported public dates</p></div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{people.map((person) => <button key={person.member} onClick={() => navigate({ member: person.member })} className="surface group p-4 text-left transition-colors hover:border-violet-400/30">
        <div className="flex items-center justify-between gap-3"><span className="font-medium text-slate-200">{person.member}</span><ArrowUpRight className="h-4 w-4 shrink-0 text-slate-500 group-hover:text-violet-300" /></div>
        <p className="mt-2 text-xs text-slate-400">{person.total} disclosures · {person.symbol_count} {person.symbol_count === 1 ? 'symbol' : 'symbols'}</p>
        <p className="mt-3 text-[11px] text-slate-500">Latest recorded availability {person.latest_available_date}</p>
      </button>)}</div>
    </section> : null}

    <section className="surface overflow-hidden" aria-labelledby="activity-title">
      <div className="border-b border-white/[0.07] p-5 sm:p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><h2 id="activity-title" className="font-semibold">Transaction feed</h2><p className="text-xs text-slate-500">Newest filing / imported public date first</p></div>
        <form key={queryString} onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); navigate({ q: String(form.get('q') || '').trim() }) }} className="flex flex-wrap gap-3">
          <label className="min-w-[180px] flex-1 text-xs text-slate-400">Search disclosures
            <div className="mt-1 flex gap-2"><input name="q" defaultValue={params.get('q') || ''} maxLength={120} placeholder="Member, owner, ticker…" className="field-input !mt-0" /><button className="button-secondary" aria-label="Search disclosures"><Search className="h-4 w-4" /></button></div>
          </label>
          <label className="min-w-0 flex-1 text-xs text-slate-400 sm:max-w-[210px]">Member
            <AnimatedSelect className="field-input" value={member} onValueChange={(value) => navigate({ member: value })}>
              <option value="">All members</option>{member && !data?.members.includes(member) && <option>{member}</option>}{data?.members.map((name) => <option key={name}>{name}</option>)}
            </AnimatedSelect>
          </label>
          <label className="min-w-[110px] flex-1 text-xs text-slate-400 sm:max-w-[150px]">Symbol
            <AnimatedSelect className="field-input" value={symbol} onValueChange={(value) => navigate({ symbol: value })}>
              <option value="">All symbols</option>{symbol && !data?.symbols.includes(symbol) && <option>{symbol}</option>}{data?.symbols.map((name) => <option key={name}>{name}</option>)}
            </AnimatedSelect>
          </label>
          <label className="min-w-[110px] flex-1 text-xs text-slate-400 sm:max-w-[140px]">Activity
            <AnimatedSelect className="field-input" value={side} onValueChange={(value) => navigate({ side: value })}><option value="">Buys & sells</option><option value="buy">Buys</option><option value="sell">Sells</option></AnimatedSelect>
          </label>
        </form>
        {hasFilters && <button className="mt-3 text-xs text-violet-300 hover:underline" onClick={() => router.push('/disclosures', { scroll: false })}>Clear filters</button>}
      </div>

      {query.isPending ? <p role="status" className="p-6 text-sm text-slate-400">Loading disclosed activity…</p> : query.isError ? <div role="alert" className="p-6 text-sm text-amber-200"><p>Disclosures could not be loaded. {query.error.message}</p><button onClick={() => void query.refetch()} className="button-secondary mt-4">Try again</button></div> : !data?.records.length ? <div className="mx-auto max-w-xl px-6 py-12 text-center">
        <Landmark className="mx-auto mb-4 h-8 w-8 text-violet-300/70" />
        <h3 className="text-lg font-medium">{data?.summary.total ? 'No activity matches this view' : 'Your disclosure collection starts here'}</h3>
        <p className="mt-3 text-sm leading-6 text-slate-400">{data?.summary.total ? 'Try another member, symbol, or search. Your filters are saved in this page’s URL.' : data?.collection?.enabled ? 'Automatic collection brings in source-linked transactions on its next successful check. An admin can refresh now above or add a CSV import. Records include filing dates, household owners, and reported ranges.' : 'An admin can import source-linked Congress transactions. They will appear here with filing dates, household owners, and reported ranges. Automatic collection status is shown above.'}</p>
        <Link className="button-primary mt-6" href={data?.summary.total ? '/disclosures' : '/trading?tab=congress'}>{data?.summary.total ? 'View all disclosures' : 'Open disclosure imports'}<ArrowRight className="h-4 w-4" /></Link>
      </div> : <>
        <div className="divide-y divide-white/[0.06]">{data.records.map((record) => <article key={record.disclosure_id} className="grid gap-4 p-5 sm:p-6 xl:grid-cols-[minmax(180px,1fr)_minmax(240px,1.5fr)_auto]">
          <div><button className="text-left text-sm font-medium text-slate-100 hover:text-violet-300" onClick={() => navigate({ member: record.member })}>{record.member}</button><p className="mt-1 text-xs text-slate-500">Owner · {disclosureOwnerLabel(record.owner)}{record.chamber ? ` · ${disclosureChamberLabel(record.chamber)}` : ''}</p><div className="mt-3 flex flex-wrap items-center gap-2"><span className={`rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-wider ${record.side === 'buy' ? 'bg-emerald-400/10 text-emerald-300' : 'bg-rose-400/10 text-rose-300'}`}>{record.side}</span><span className="text-xs text-slate-400">{record.asset_type}</span>{record.is_amendment && <span className="text-[10px] text-amber-200">Amendment</span>}{record.partial_sale && <span className="text-[10px] text-slate-500">Partial sale</span>}</div></div>
          <div><Link href={companyResearchHref(record.symbol, returnTo)} className="inline-flex items-center gap-2 text-lg font-semibold text-violet-200 hover:text-white">{record.symbol}<ArrowUpRight className="h-4 w-4" /></Link>{record.asset_description && <p className="mt-1 max-w-md text-xs leading-5 text-slate-500">{record.asset_description}</p>}<p className="mt-1 text-sm text-slate-300">{record.amount_range}<span className="ml-2 text-xs text-slate-500">reported range</span></p><div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs"><span className="text-slate-500">Traded <span className="text-slate-300">{record.transaction_date}</span></span><span className="text-slate-500">{record.availability_basis === 'filing_day_estimate' ? 'Filed (estimate)' : 'Public (imported)'} <span className="text-slate-300">{record.filed_date || record.available_date}</span></span>{record.first_seen_at && <span className="text-slate-500">First observed <span className="text-slate-300">{tradingDate(record.first_seen_at)}</span></span>}</div></div>
          <div className="flex items-center justify-between gap-4 xl:flex-col xl:items-end"><span className="inline-flex items-center gap-1.5 text-xs text-slate-400"><Clock3 className="h-3.5 w-3.5" />{record.lag_days}-day reported lag</span><a href={record.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-violet-300 hover:underline">Original evidence<ArrowUpRight className="h-3 w-3" /></a></div>
        </article>)}</div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.07] px-5 py-4 text-xs text-slate-400"><span>{offset + 1}–{Math.min(offset + data.records.length, data.total)} of {data.total} disclosures</span><div className="flex gap-2"><button disabled={!offset} className="button-secondary disabled:opacity-30" onClick={() => navigate({ offset: String(Math.max(0, offset - pageSize)) })}>Previous</button><button disabled={offset + pageSize >= data.total} className="button-secondary disabled:opacity-30" onClick={() => navigate({ offset: String(offset + pageSize) })}>Next</button></div></div>
      </>}
    </section>

    <section className="grid gap-5 rounded-xl border border-white/[0.06] p-5 text-xs leading-6 text-slate-400 md:grid-cols-3">
      <div><p className="mb-1 font-medium text-slate-200">01 · Inspect the evidence</p><p>Check the original filing, household owner, asset type, and reported range. Automatic data is normalized by a third party; CSV dates are importer supplied.</p></div>
      <div><p className="mb-1 font-medium text-slate-200">02 · Research the company</p><p>Open a ticker to examine fundamentals, valuation, news tone, and original sources before forming a thesis.</p></div>
      <div><p className="mb-1 font-medium text-slate-200">03 · Test the timing</p><p>Tests default to first observed dates for automatic records. Filing-date estimates are an explicit historical option. Orders wait for the next observed session after your chosen delay; unsupported assets are excluded.</p></div>
    </section>
  </div></AppShell>
}

'use client'

import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import AnimatedAccordion from '@/components/ui/AnimatedAccordion'
import { disclosureChamberLabel, disclosureOwnerLabel, tradingDate, type Disclosure } from '@/lib/trading'

/** The same evidence hierarchy in the feed and company previews. */
export default function DisclosureRecord({ record, companyHref, onMember, showSymbol = true }: {
  record: Disclosure
  companyHref?: string
  onMember?: (member: string) => void
  showSymbol?: boolean
}) {
  let source: string | undefined
  try {
    const url = new URL(record.source_url)
    if (url.protocol === 'https:') source = url.href
  } catch { /* Invalid source links are not actionable. */ }
  const details = <div className="space-y-3 pb-1 text-xs leading-5">
    {record.asset_description && <p className="text-slate-400">{record.asset_description}</p>}
    <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
      <div><dt className="text-slate-500">Household owner</dt><dd className="text-slate-300">{disclosureOwnerLabel(record.owner)}</dd></div>
      <div><dt className="text-slate-500">Asset type</dt><dd className="text-slate-300">{record.asset_type}{record.chamber ? ` · ${disclosureChamberLabel(record.chamber)}` : ''}</dd></div>
      <div><dt className="text-slate-500">{record.availability_basis === 'filing_day_estimate' ? 'Filed (estimate)' : 'Public (imported)'}</dt><dd className="text-slate-300">{record.filed_date || record.available_date}</dd></div>
      <div><dt className="text-slate-500">Reported lag</dt><dd className="text-slate-300">{record.lag_days} {record.lag_days === 1 ? 'day' : 'days'}</dd></div>
      {record.first_seen_at && <div><dt className="text-slate-500">First observed</dt><dd className="text-slate-300">{tradingDate(record.first_seen_at)}</dd></div>}
    </dl>
    {source ? <a href={source} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center gap-1.5 text-violet-300 hover:underline">Original evidence<ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" /></a> : <p className="text-slate-500">Source unavailable</p>}
  </div>
  return <article className="min-w-0 p-4 sm:grid sm:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] sm:gap-6 sm:p-6">
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {showSymbol && companyHref ? <Link href={companyHref} className="inline-flex min-h-9 items-center gap-1 text-base font-semibold text-slate-100 hover:text-violet-200">{record.symbol}<ArrowUpRight className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" /></Link> : <span className="text-sm font-medium text-slate-200">{record.member}</span>}
        <span className={`rounded px-2 py-1 text-[10px] font-medium ${record.side === 'buy' ? 'bg-emerald-400/10 text-emerald-300' : 'bg-rose-400/10 text-rose-300'}`}>{record.side === 'buy' ? 'Buy' : record.partial_sale ? 'Partial sale' : 'Sell'}</span>
        {record.is_amendment && <span className="text-[10px] text-amber-200">Amendment</span>}
      </div>
      {showSymbol && (onMember ? <button className="mt-1 min-h-9 text-left text-xs text-slate-400 hover:text-violet-200" onClick={() => onMember(record.member)}>{record.member}</button> : <p className="mt-2 text-xs text-slate-400">{record.member}</p>)}
      <p className="mt-2 text-sm font-medium tabular-nums text-slate-200">{record.amount_range}<span className="ml-2 text-[10px] font-normal text-slate-500">reported range</span></p>
      <p className="mt-2 text-xs text-slate-400">Traded <time dateTime={record.transaction_date}>{record.transaction_date}</time></p>
    </div>
    <AnimatedAccordion className="mt-2 sm:hidden" triggerClassName="text-xs text-slate-400" title={<>View details<span className="sr-only"> for {record.member} · {record.symbol} · {record.transaction_date}</span></>}>
      <div className="border-t border-white/[0.06] pt-3">{details}</div>
    </AnimatedAccordion>
    <div className="hidden sm:block">{details}</div>
  </article>
}

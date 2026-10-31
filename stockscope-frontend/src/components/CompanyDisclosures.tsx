'use client'

import { useId } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Landmark, RefreshCw } from 'lucide-react'
import { tradingRequest, type DisclosureResearch } from '@/lib/trading'

import DisclosureRecord from './DisclosureRecord'

const API_UPDATE_MESSAGE = 'Company disclosures are waiting for a compatible server update. Try again shortly.'

export default function CompanyDisclosures({ symbol }: { symbol: string }) {
  const headingId = useId()
  const query = useQuery({
    queryKey: ['congress', 'company', symbol],
    queryFn: async () => {
      const data = await tradingRequest<DisclosureResearch>(
        `/congress?${new URLSearchParams({ symbol, limit: '5' })}`,
      )
      // Older servers ignore the symbol filter. Never label their full feed as company activity.
      if (
        !data || !Array.isArray(data.records) || !Array.isArray(data.symbols)
        || !data.summary || !data.filtered_summary
        || !['csv_import', 'automatic_and_csv'].includes(data.mode)
        || !['user_supplied_csv', 'mixed_disclosures'].includes(data.provenance?.source)
        || data.provenance?.dates_verified !== false
        || !data.records.every((record) => record?.symbol === symbol)
      ) throw new Error(API_UPDATE_MESSAGE)
      return data
    },
    staleTime: 60_000,
  })
  const records = query.data?.records ?? []
  const disclosureHref = `/disclosures?${new URLSearchParams({ symbol })}`

  return (
    <section aria-labelledby={headingId} className="surface overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl border border-violet-400/15 bg-violet-400/10 p-2.5">
            <Landmark className="h-4 w-4 text-violet-300" aria-hidden="true" />
          </div>
          <div>
            <h2 id={headingId} className="text-sm font-semibold text-slate-100">
              Disclosed activity
            </h2>
            <p className="mt-1 text-xs leading-5 text-slate-400">
              Congressional transactions involving {symbol}.
            </p>
            <span className="mt-2 inline-flex rounded-full border border-white/10 px-2 py-0.5 text-[10px] font-medium text-slate-400">
              {query.data?.mode === 'automatic_and_csv' ? 'Collected & imported records' : 'Imported records'}
            </span>
          </div>
        </div>
        <Link
          href={disclosureHref}
          className="inline-flex items-center gap-1.5 rounded-lg py-1 text-xs font-medium text-violet-300 hover:text-violet-200"
        >
          Explore disclosures <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>

      {query.isError && (
        <div role="alert" className="mx-5 mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-200 sm:mx-6">
          <p>
            {query.error?.message === API_UPDATE_MESSAGE ? API_UPDATE_MESSAGE : 'Disclosures could not be reloaded.'}
            {query.data ? ' Previously loaded records are shown below.' : ' Try loading them again.'}
          </p>
          <button
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
            className="inline-flex items-center gap-1.5 rounded px-2 py-1 font-medium hover:bg-white/5 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${query.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" />
            Retry
          </button>
        </div>
      )}

      {query.isPending ? (
        <div role="status" className="space-y-3 px-5 pb-5 sm:px-6">
          <span className="sr-only">Loading {symbol} disclosures…</span>
          {[0, 1].map((index) => (
            <div key={index} className="h-16 animate-pulse rounded-lg bg-white/5" />
          ))}
        </div>
      ) : query.data && records.length === 0 ? (
        <div className="mx-5 mb-5 rounded-xl border border-dashed border-white/10 px-4 py-5 sm:mx-6 sm:mb-6">
          <p className="text-sm text-slate-300">No recorded disclosures for {symbol} yet.</p>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-500">
            Browse collection coverage and source-linked records in the disclosure workspace.
            An empty result does not establish whether members traded this company.
          </p>
        </div>
      ) : records.length > 0 ? (
        <>
          <ul className="divide-y divide-white/[0.06] border-y border-white/[0.07]">
            {records.map(record => <li key={record.disclosure_id}><DisclosureRecord record={record} showSymbol={false} /></li>)}
          </ul>
          <div className="flex flex-wrap justify-between gap-2 px-5 py-3 text-[10px] leading-5 text-slate-500 sm:px-6">
            <p>Filing dates estimate availability; CSV dates are importer supplied. Review the original source.</p>
            <p>{records.length} of {query.data?.total.toLocaleString()} records</p>
          </div>
        </>
      ) : null}
    </section>
  )
}

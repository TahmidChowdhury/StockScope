'use client'

import { priceAmount, unitLabel } from '@/lib/financial-format'
import ResearchPanel from './ResearchPanel'
import { Skeleton } from './ResearchLoading'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { apiFetch, ApiError, readApiJson } from '@/lib/api'

interface CompanyInfo {
  stale?: boolean
  currentPrice?: number | null
  marketCap?: number | null
  priceToEarningsRatio?: number | null
  dividendYield?: number | null
  dayLow?: number | null
  dayHigh?: number | null
  fiftyTwoWeekLow?: number | null
  fiftyTwoWeekHigh?: number | null
  volume?: number | null
  averageVolume?: number | null
  beta?: number | null
  earningsPerShare?: number | null
  priceToBook?: number | null
  priceToSalesTrailing12Months?: number | null
  currency?: string | null
  quote_as_of?: string | null
  retrieved_at?: string | null
}
const timestamp = (value?: string | null) => {
  if (!value || Number.isNaN(Date.parse(value))) return 'Unavailable'
  return new Date(value).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'America/New_York',
    timeZoneName: 'short',
  })
}

export default function KeyMetrics({
  symbol,
  className = '',
}: {
  symbol: string
  className?: string
}) {
  const { data, error, isPending, isError, isFetching, refetch } = useQuery({
    queryKey: ['company-info', symbol],
    retry: false,
    staleTime: 60 * 60_000,
    refetchOnWindowFocus: false,
    queryFn: async ({ signal }): Promise<CompanyInfo> => {
      const response = await apiFetch(
        `/api/stocks/${encodeURIComponent(symbol)}/info`,
        { signal },
      )
      return readApiJson<CompanyInfo>(response, 'Company metrics could not be loaded.')
    },
  })
  const limited = error instanceof ApiError && error.status === 429
  const number = (
    value?: number | null,
    style: 'number' | 'money' | 'compact' | 'percent' = 'number',
  ) => {
    if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
    if (style === 'money') return priceAmount(value, data?.currency)
    return new Intl.NumberFormat('en-US', {
      ...(style === 'percent' ? { style: 'percent' } : {}),
      ...(style === 'compact' ? { notation: 'compact' } : {}),
      maximumFractionDigits: 2,
    }).format(value)
  }
  const range = (low?: number | null, high?: number | null) =>
    low == null || high == null
      ? '—'
      : `${number(low, 'money')} – ${number(high, 'money')}`
  const sections = [
    {
      title: 'Valuation',
      rows: [
        ['Market cap', number(data?.marketCap, 'compact')],
        ['P/E ratio', number(data?.priceToEarningsRatio)],
        ['Price / book', number(data?.priceToBook)],
        ['Price / sales', number(data?.priceToSalesTrailing12Months)],
      ],
    },
    {
      title: 'Trading',
      rows: [
        ['Day range', range(data?.dayLow, data?.dayHigh)],
        [
          '52-week range',
          range(data?.fiftyTwoWeekLow, data?.fiftyTwoWeekHigh),
        ],
        ['Volume', number(data?.volume, 'compact')],
        ['Average volume', number(data?.averageVolume, 'compact')],
        ['Beta', number(data?.beta)],
      ],
    },
    {
      title: 'Per share',
      rows: [
        // EPS has no independently supplied unit in this response.
        ['Earnings / share', priceAmount(data?.earningsPerShare, null)],
        ['Trailing dividend yield', number(data?.dividendYield, 'percent')],
      ],
    },
  ]
  return (
    <ResearchPanel pending={isPending}
      aria-labelledby="metrics-heading"
      className={`surface p-5 ${className}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <h2
          id="metrics-heading"
          className="text-sm font-semibold text-slate-100"
        >
          At a glance
        </h2>
        <button
          onClick={() => void refetch()}
          disabled={isFetching || limited}
          aria-label="Reload company metrics"
          title="Reload provider metrics; responses may be cached for up to one hour"
          className="rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-slate-200 disabled:opacity-40"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`}
          />
        </button>
      </div>
      {isPending && <span role="status" className="sr-only">Loading company metrics…</span>}
      {isError && (
        <div role="alert" className="mb-4 text-xs leading-5 text-amber-200">
          {error?.message}
          {data
            ? ' Previously loaded observations are shown.'
            : limited ? '' : ' Use the reload button to try again.'}
        </div>
      )}
      {data?.stale && <p role="status" className="mb-4 text-xs leading-5 text-amber-200">Showing saved metrics. The provider could not be refreshed; observation dates are unchanged.</p>}
      {(data || isPending) && (
        <>
          <div className="mb-5 border-b border-white/[0.07] pb-5">
            <p className="text-[10px] font-semibold tracking-widest text-slate-400">
              Provider quote · {unitLabel(data?.currency)}
            </p>
            <p className="mt-2 text-3xl font-semibold tracking-tight tabular-nums text-white">
              {isPending ? <Skeleton className="h-9 w-24" /> : number(data?.currentPrice, 'money')}
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-400">
              {isPending ? <Skeleton className="my-1 h-3 w-32" /> : `As of ${timestamp(data?.quote_as_of)}`}
            </p>
          </div>
          {sections.map((section) => (
            <div key={section.title} className="mb-5">
              <h3 className="eyebrow mb-3">{section.title}</h3>
              <dl className="space-y-2">
                {section.rows.map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-baseline justify-between gap-3 text-xs"
                  >
                    <dt className="text-slate-400">{label}</dt>
                    <dd className="text-right font-medium tabular-nums text-slate-200">
                      {isPending ? <Skeleton className="h-3 w-14" /> : value}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
          <div className="border-t border-white/[0.07] pt-4 text-xs leading-5 text-slate-400">
            <p>{isPending ? <Skeleton className="my-1 h-3 w-32" /> : `Retrieved ${timestamp(data?.retrieved_at)}`}</p>
            <p>
              Provider data may be delayed and cached for up to one hour. —
              means unavailable.{data && !data.currency && ' Currency unavailable.'}
            </p>
          </div>
        </>
      )}
    </ResearchPanel>
  )
}

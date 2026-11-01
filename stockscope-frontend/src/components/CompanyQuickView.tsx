'use client'

import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { ArrowUpRight, X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import * as Popover from '@animate-ui/react/primitives/radix-ui/popover'
import { apiFetch } from '@/lib/api'
import { amount, observed, percent } from '@/lib/financial-format'
import type { FundamentalsTTM, StockMetadata } from '@/types'

export const shareClass = (symbol: string) => symbol === 'GOOGL' ? 'Class A' : symbol === 'GOOG' ? 'Class C' : null

function dateLabel(value?: string | null) {
  if (!value || Number.isNaN(Date.parse(value))) return 'Not available'
  return new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
}

type Preview = { saved: boolean; sentiment?: { avg_sentiment: number | null; sample_size: number }; quote?: { price: number | null; currency: string | null; as_of: string | null }; ttm?: FundamentalsTTM | null; metadata?: { retrieved_at?: string | null; currency?: string | null; source?: string | null } }

/** Animate UI's anchored animation with hover intent and an accessible tap/focus popover. */
export default function CompanyQuickView({ stock, children }: { stock: Pick<StockMetadata, 'symbol'> & Partial<StockMetadata>; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const titleId = useId()
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const held = useRef(false)
  const restoreFocus = useRef(false)
  const content = useRef<HTMLDivElement>(null)
  const cancelTimer = () => { if (timer.current) clearTimeout(timer.current); timer.current = null }
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])
  const changeOpen = (next: boolean) => { cancelTimer(); setOpen(next); if (!next) { restoreFocus.current = held.current; held.current = false } }
  const leave = () => {
    cancelTimer()
    if (!held.current) timer.current = setTimeout(() => setOpen(false), 180)
  }
  const preview = useQuery({
    queryKey: ['company-preview', stock.symbol],
    enabled: open,
    queryFn: async ({ signal }): Promise<Preview> => {
      const response = await apiFetch(`/api/fundamentals/${encodeURIComponent(stock.symbol)}/preview`, { signal })
      if (!response.ok) throw new Error('Saved financials are unavailable.')
      return response.json()
    },
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  })
  const ttm = preview.data?.ttm
  const quote = preview.data?.quote
  const sentiment = preview.data?.sentiment ? preview.data.sentiment.avg_sentiment : stock.avg_sentiment
  const kind = shareClass(stock.symbol)
  return <Popover.Root open={open} onOpenChange={changeOpen}>
    <Popover.Trigger asChild>
      <button type="button" aria-label={`Quick view ${stock.symbol}`} className="group/preview min-w-0 flex-1 basis-28 rounded-md text-left outline-none focus-visible:ring-2 focus-visible:ring-[#b6c8ab] focus-visible:ring-offset-4 focus-visible:ring-offset-[#171a22]"
        onPointerEnter={event => { if (event.pointerType !== 'mouse') return; cancelTimer(); timer.current = setTimeout(() => setOpen(true), 250) }}
        onPointerLeave={leave}
        onClick={event => { event.preventDefault(); held.current = true; changeOpen(true) }}
        onKeyDown={event => { if (event.key === 'ArrowDown') { event.preventDefault(); if (open) content.current?.focus(); else { held.current = true; changeOpen(true) } } }}>
        {children}
      </button>
    </Popover.Trigger>
    <Popover.Portal>
      <Popover.Content data-company-preview ref={content} tabIndex={-1} aria-labelledby={titleId} side="bottom" align="start" sideOffset={10} collisionPadding={16}
        transition={{ type: 'spring', stiffness: 320, damping: 30 }}
        className="z-[80] max-h-[min(620px,var(--radix-popover-content-available-height))] w-[360px] max-w-[calc(100vw-32px)] overflow-y-auto rounded-2xl border border-white/15 bg-[#1b201d] p-5 text-slate-200 shadow-2xl shadow-black/50 outline-none"
        onOpenAutoFocus={event => event.preventDefault()}
        onCloseAutoFocus={event => { if (!restoreFocus.current) event.preventDefault() }}
        onPointerEnter={cancelTimer} onPointerLeave={leave}
        onFocusCapture={() => { held.current = true; cancelTimer() }}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0"><p className="text-[10px] uppercase tracking-[0.18em] text-[#b6c8ab]">Quick view · Saved research</p><h3 id={titleId} className="mt-2 text-xl font-semibold">{stock.symbol}{kind && <span className="ml-2 text-xs font-normal text-slate-400">{kind}</span>}</h3><p className="mt-1 text-sm text-slate-400">{stock.companyName || 'Company research'}</p></div>
          <Popover.Close className="-mr-2 -mt-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-lg hover:bg-white/5" aria-label="Close quick view"><X className="h-4 w-4" /></Popover.Close>
        </div>
        {kind && <p className="mt-3 rounded-lg bg-white/5 p-3 text-xs leading-5 text-slate-300">Alphabet has two listed share classes: GOOGL (Class A) and GOOG (Class C). Both belong to the same company; each ticker keeps its own research view.</p>}
        <dl className="mt-5 grid grid-cols-2 gap-4 border-y border-white/10 py-4 text-xs">
          <div>
            <dt className="text-slate-400">Saved stock price</dt>
            <dd className="mt-1 text-base tabular-nums">{observed(quote?.price)
              ? `${quote.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${quote.currency ?? ''}`.trim()
              : preview.isPending ? 'Loading…' : 'Unavailable'}</dd>
            {observed(quote?.price) && <dd className="mt-1 text-slate-400">{quote.as_of ? dateLabel(quote.as_of) : 'Quote date unknown'}</dd>}
          </div>
          <div>
            <dt className="text-slate-400">Average news sentiment</dt>
            <dd className="mt-1 text-base">{observed(sentiment)
              ? sentiment >= 0.05 ? 'Positive' : sentiment <= -0.05 ? 'Negative' : 'Neutral'
              : preview.isPending ? 'Loading…' : preview.isError ? 'Unavailable' : 'Unscored'}</dd>
            {observed(sentiment) && <dd className="mt-1 tabular-nums text-slate-400">{sentiment > 0 ? '+' : ''}{sentiment.toFixed(3)} on −1 to +1{preview.data?.sentiment && ` · ${preview.data.sentiment.sample_size} scored`}</dd>}
          </div>
          <div><dt className="text-slate-400">Saved evidence</dt><dd className="mt-1 text-base tabular-nums">{stock.total_posts == null ? 'Not available' : stock.total_posts.toLocaleString()}</dd></div>
          <div><dt className="text-slate-400">Latest evidence</dt><dd className="mt-1">{dateLabel(stock.last_updated)}</dd></div>
          <div className="col-span-2"><dt className="text-slate-400">Sources in the library</dt><dd className="mt-1">{stock.sources?.length ? stock.sources.map(source => source === 'sec' ? 'SEC filings' : source === 'news' ? 'News' : source).join(' · ') : 'No saved sources'}</dd></div>
        </dl>
        <div className="py-4">
          <h4 className="text-xs font-medium text-slate-300">Saved fundamentals{preview.data?.metadata?.currency ? ` · ${preview.data.metadata.currency}` : ''}</h4>
          {preview.isPending ? <p role="status" className="mt-3 text-xs text-slate-400">Checking saved financials…</p> : preview.isError ? <p role="status" className="mt-3 text-xs leading-5 text-slate-400">Saved financials couldn’t be loaded. The library summary is still available.</p> : ttm ? <>
            <dl className="mt-3 grid grid-cols-2 gap-4 text-xs">
              {[['Revenue · TTM', amount(ttm.revenue_ttm)], ['Revenue growth', percent(ttm.revenue_growth_yoy)], ['Free cash flow · TTM', amount(ttm.fcf_ttm)], ['Operating margin', percent(ttm.operating_margin_ttm)]].map(([label, value]) => <div key={label}><dt className="text-slate-400">{label}</dt><dd className="mt-1 text-base tabular-nums">{value}</dd></div>)}
            </dl><p className="mt-3 text-[11px] leading-5 text-slate-400">Retrieved {dateLabel(preview.data?.metadata?.retrieved_at)} · Missing values show —.</p>
          </> : <p className="mt-3 text-xs leading-5 text-slate-400">No saved financials yet. Open the company’s Financials view to load them.</p>}
        </div>
        <p className="text-[11px] leading-5 text-slate-500">Previewing uses saved data only. Figures may be older than the latest filings.</p>
        <Link href={`/stock/${encodeURIComponent(stock.symbol)}`} className="mt-4 flex min-h-11 items-center justify-between rounded-lg bg-[#b6c8ab] px-4 text-xs font-medium text-[#111613]">Open full research<ArrowUpRight className="h-4 w-4" /></Link>
      </Popover.Content>
    </Popover.Portal>
  </Popover.Root>
}

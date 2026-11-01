'use client'

import { useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch, readApiJson } from '@/lib/api'

type Quote = { symbol: string; change: number; as_of: string | null }
const percentage = new Intl.NumberFormat('en-US', {
  style: 'percent', signDisplay: 'exceptZero', minimumFractionDigits: 2,
})
const marketTime = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York', month: 'short', day: 'numeric', year: 'numeric',
  hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
})
const marketDate = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York', month: 'short', day: 'numeric', year: 'numeric',
})
const strip = 'mb-5 flex h-7 items-center border-y border-white/10 text-xs tabular-nums'

export default function MarketTape() {
  const [paused, setPaused] = useState(false)
  const [selected, setSelected] = useState<Quote | null>(null)
  const detail = useRef<HTMLDialogElement>(null)
  const { data: quotes = [], isPending } = useQuery({
    queryKey: ['market-tape'],
    queryFn: async ({ signal }) => readApiJson<Quote[]>(
      await apiFetch('/api/market-tape', { signal }), 'Market changes unavailable.',
    ),
    staleTime: 300_000,
    refetchInterval: 300_000,
  })
  if (!quotes.length) return <p role="status" className={`${strip} px-3 text-slate-400`}>
    {isPending ? 'Loading market changes…' : 'Market changes unavailable'}
  </p>

  const dates = quotes.map(quote => quote.as_of ? marketDate.format(new Date(quote.as_of)) : 'Date unknown')
  const sharedDate = dates.every(date => date === dates[0]) ? dates[0] : null
  const moving = quotes.length > 1
  function items(copy = false) {
    return quotes.map((quote, index) => (
      <button type="button" key={quote.symbol} tabIndex={copy ? -1 : undefined}
        onClick={() => { setSelected(quote); detail.current?.showModal() }}
        className="inline-flex items-center gap-2 px-3">
        <span className="font-medium text-slate-300">{quote.symbol}</span>
        <span className={quote.change > 0 ? 'text-sage-300' : quote.change < 0 ? 'text-rose-300' : 'text-slate-400'}>
          {percentage.format(quote.change / 100)}
        </span>
        {!sharedDate && <span className="text-slate-400">{dates[index]}</span>}
      </button>
    ))
  }

  return <section aria-label="Saved daily percentage changes" className={strip}>
    {sharedDate && <span className="shrink-0 border-r border-white/10 pr-3 text-slate-400">{sharedDate}</span>}
    <div className="market-tape-window min-w-0 flex-1 overflow-hidden">
      <div className={moving ? 'market-tape-track' : ''} style={{ animationPlayState: paused || selected ? 'paused' : undefined }}>
        <div className="market-tape-set">{items()}</div>
        {moving && <div aria-hidden="true" className="market-tape-set">{items(true)}</div>}
      </div>
    </div>
    {moving && <button type="button" aria-label={paused ? 'Resume ticker' : 'Pause ticker'} onClick={() => setPaused(!paused)} className="market-tape-control h-full w-8 text-slate-400">
      {paused ? '▶' : 'Ⅱ'}
    </button>}
    <dialog ref={detail} aria-labelledby="market-quote-title" onClose={() => setSelected(null)}
      className="m-auto rounded-lg border border-white/10 bg-[#111613] p-5 text-slate-300 backdrop:bg-black/50">
      {selected && <>
        <h2 id="market-quote-title" className="text-base font-medium">{selected.symbol} {percentage.format(selected.change / 100)}</h2>
        <p className="mt-2">Regular session · {selected.as_of ? marketTime.format(new Date(selected.as_of)) : 'Quote time unavailable'}</p>
        <p className="mt-1 text-slate-400">Source: Yahoo Finance</p>
      </>}
      <form method="dialog" className="mt-4"><button className="button-secondary">Close</button></form>
    </dialog>
  </section>
}

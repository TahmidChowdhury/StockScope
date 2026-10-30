'use client'

import AnimatedSelect from '@/components/ui/AnimatedSelect'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Description,
} from '@headlessui/react'
import { ArrowUpRight, Building2, Search, Trash2 } from 'lucide-react'
import CompanyLogo from './CompanyLogo'
import SpotlightCard from './ui/SpotlightCard'
import AnimatedAction from './ui/AnimatedAction'
import { useWatchlist } from '@/hooks/useWatchlist'
import { apiFetch, getAuthSession } from '@/lib/api'

function dateLabel(value?: string | null) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? 'Date unavailable'
    : date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        timeZone: 'America/New_York',
      })
}

export default function Watchlist() {
  const { data: stocks = [], isPending, isError, refetch } = useWatchlist()
  const [filter, setFilter] = useState('')
  const [sort, setSort] = useState('symbol')
  const [managing, setManaging] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [confirm, setConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [notice, setNotice] = useState('')
  const admin = getAuthSession()?.role === 'admin'
  const filtered = useMemo(
    () =>
      stocks
        .filter((s) =>
          `${s.symbol} ${s.companyName ?? ''}`
            .toLowerCase()
            .includes(filter.toLowerCase()),
        )
        .sort((a, b) =>
          sort === 'updated'
            ? (Date.parse(b.last_updated ?? '') || 0) -
              (Date.parse(a.last_updated ?? '') || 0)
            : a.symbol.localeCompare(b.symbol),
        ),
    [stocks, filter, sort],
  )
  const remove = async () => {
    setDeleting(true)
    const failed: string[] = []
    for (const symbol of selected) {
      try {
        const response = await apiFetch(
          `/api/stocks/${encodeURIComponent(symbol)}`,
          { method: 'DELETE' },
        )
        if (!response.ok) failed.push(symbol)
      } catch {
        failed.push(symbol)
      }
    }
    setNotice(
      failed.length
        ? `Could not delete ${failed.join(', ')}. Please try again.`
        : 'Selected research deleted.',
    )
    setSelected(failed)
    setDeleting(false)
    setConfirm(false)
    if (!failed.length) setManaging(false)
    void refetch()
  }
  return (
    <section id="watchlist" aria-labelledby="watchlist-heading">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h2
              id="watchlist-heading"
              className="text-lg font-semibold tracking-tight"
            >
              Your watchlist
            </h2>
            <span className="rounded-md border border-white/10 px-1.5 py-0.5 text-[10px] tabular-nums text-slate-400">
              {stocks.length}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Follow the business. Keep the evidence close.
          </p>
        </div>
        {admin && (
          <AnimatedAction
            className="button-secondary text-xs"
            onClick={() => {
              setManaging(!managing)
              setSelected([])
            }}
          >
            {managing ? 'Done' : 'Manage watchlist'}
          </AnimatedAction>
        )}
      </div>
      <div className="surface overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-3">
          <label className="flex min-w-0 flex-1 basis-full items-center gap-2 text-slate-500 sm:basis-auto">
            <Search className="h-4 w-4" />
            <input
              aria-label="Filter watchlist"
              placeholder="Find a company…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="min-h-11 w-full min-w-0 bg-transparent py-2 text-base text-slate-200 placeholder:text-slate-500 focus:outline-none sm:min-h-0 sm:w-44 sm:text-xs"
            />
          </label>
          <AnimatedSelect
            aria-label="Sort watchlist"
            value={sort}
            onValueChange={(value) => setSort(value)}
            className="min-h-11 w-full max-w-full rounded-md border border-white/[0.08] bg-[#171a22] px-2 py-1.5 text-base text-slate-300 sm:min-h-0 sm:w-auto sm:text-xs"
          >
            <option value="symbol">Ticker A–Z</option>
            <option value="updated">Recently updated</option>
          </AnimatedSelect>
        </div>
        {isError && stocks.length > 0 && (
          <div
            role="status"
            className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-5 py-3 text-xs text-amber-200"
          >
            <span>
              Could not update the watchlist. Previously loaded research is
              shown.
            </span>
            <AnimatedAction
              onClick={() => void refetch()}
              className="underline underline-offset-4"
            >
              Retry
            </AnimatedAction>
          </div>
        )}
        {notice && (
          <p
            role="status"
            className="border-b border-white/10 px-5 py-3 text-xs text-amber-200"
          >
            {notice}
          </p>
        )}
        {isPending ? (
          <div aria-label="Loading watchlist" className="space-y-5 p-5">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-12 animate-pulse rounded-lg bg-white/5"
              />
            ))}
          </div>
        ) : isError && !stocks.length ? (
          <div role="alert" className="p-8 text-center">
            <p className="text-sm text-slate-300">
              The watchlist could not be loaded.
            </p>
            <AnimatedAction
              onClick={() => void refetch()}
              className="button-secondary mt-4"
            >
              Try again
            </AnimatedAction>
          </div>
        ) : !stocks.length ? (
          <div className="px-6 py-14 text-center">
            <Building2 className="mx-auto mb-4 h-8 w-8 text-violet-300" />
            <h3 className="text-base font-medium">Your research starts here</h3>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-400">
              Search for a company above to collect its research and add it to
              the shared watchlist.
            </p>
          </div>
        ) : !filtered.length ? (
          <p className="p-10 text-center text-sm text-slate-400">
            No companies match “{filter}”.
          </p>
        ) : (
          <div className="p-3 sm:p-4">
            {managing && (
              <label className="mb-3 flex min-h-11 w-fit cursor-pointer items-center gap-3 px-2 text-xs text-slate-300">
                <input
                  type="checkbox"
                  aria-label="Select all visible companies"
                  className="h-4 w-4 accent-violet-400"
                  checked={filtered.every((stock) => selected.includes(stock.symbol))}
                  onChange={(event) =>
                    setSelected(event.target.checked ? filtered.map((stock) => stock.symbol) : [])
                  }
                />
                Select all visible companies
              </label>
            )}
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {filtered.map((stock) => (
                <SpotlightCard key={stock.symbol} selected={selected.includes(stock.symbol)} className="flex flex-col p-5">
                  <div className="mb-6 flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <CompanyLogo symbol={stock.symbol} />
                      <div className="min-w-0">
                        <h3 className="font-semibold tracking-tight text-slate-100">{stock.symbol}</h3>
                        <p className="mt-1 truncate text-xs text-slate-400">
                          {stock.companyName || 'Company research'}
                        </p>
                      </div>
                    </div>
                    {managing && (
                      <label className="-mr-2 -mt-2 flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-lg hover:bg-white/5">
                        <input
                          type="checkbox"
                          aria-label={`Select ${stock.symbol}`}
                          className="h-4 w-4 accent-violet-400"
                          checked={selected.includes(stock.symbol)}
                          onChange={(event) => setSelected((current) =>
                            event.target.checked
                              ? [...current, stock.symbol]
                              : current.filter((symbol) => symbol !== stock.symbol),
                          )}
                        />
                      </label>
                    )}
                  </div>
                  <dl className="grid grid-cols-2 gap-4">
                    <div>
                      <dt className="text-[10px] uppercase tracking-wider text-slate-500">Daily price</dt>
                      <dd className="mt-1.5 text-2xl font-medium tracking-tight tabular-nums text-white">
                        {stock.currentPrice != null && Number.isFinite(stock.currentPrice)
                          ? `$${stock.currentPrice.toFixed(2)}` : '—'}
                      </dd>
                      <dd className="mt-1 text-[10px] text-slate-500">{dateLabel(stock.price_as_of)}</dd>
                    </div>
                    <div className="text-right">
                      <dt className="mb-3 text-[10px] uppercase tracking-wider text-slate-500">News tone</dt>
                      <dd className={`inline-flex rounded-md px-2 py-1 text-[11px] ${stock.avg_sentiment == null ? 'bg-white/5 text-slate-400' : stock.avg_sentiment >= 0.05 ? 'bg-emerald-400/[0.08] text-emerald-300' : stock.avg_sentiment <= -0.05 ? 'bg-rose-400/[0.08] text-rose-300' : 'bg-amber-400/[0.08] text-amber-200'}`}>
                        {stock.avg_sentiment == null ? 'Unavailable' : stock.avg_sentiment >= 0.05 ? 'Positive' : stock.avg_sentiment <= -0.05 ? 'Negative' : 'Neutral'}
                      </dd>
                    </div>
                  </dl>
                  <div className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.07] pt-4 text-[11px] text-slate-400">
                    <span>{stock.total_posts == null ? 'Count unavailable' : `${stock.total_posts.toLocaleString()} evidence records`}</span>
                    <span>Updated {dateLabel(stock.last_updated)}</span>
                  </div>
                  <AnimatedAction asChild className="mt-5 inline-flex min-h-11 items-center justify-between gap-2 rounded-lg border border-violet-400/20 bg-violet-400/[0.08] px-3 text-xs font-medium text-violet-200 hover:border-violet-400/40 hover:bg-violet-400/[0.14]">
                    <Link href={`/stock/${encodeURIComponent(stock.symbol)}`} aria-label={`View details for ${stock.symbol}`}>
                      View details
                      <ArrowUpRight aria-hidden="true" className="h-4 w-4" />
                    </Link>
                  </AnimatedAction>
                </SpotlightCard>
              ))}
            </div>
          </div>
        )}
        {managing && (
          <div className="flex items-center justify-between gap-3 border-t border-white/10 px-5 py-3">
            <span className="text-xs text-slate-400">
              {selected.length} selected
            </span>
            <AnimatedAction
              disabled={!selected.length}
              onClick={() => setConfirm(true)}
              className="button-secondary text-xs text-rose-300 disabled:opacity-40"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete selected
            </AnimatedAction>
          </div>
        )}
      </div>
      <p className="mt-3 text-[11px] leading-5 text-slate-500">
        Prices are saved observations. News tone describes article wording.
        Opening a company does not refresh saved research.
      </p>
      <Dialog
        open={confirm}
        onClose={() => {
          if (!deleting) setConfirm(false)
        }}
        className="relative z-[60]"
      >
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm" />
        <div className="fixed inset-0 overflow-y-auto p-5">
          <div className="flex min-h-full items-center justify-center">
          <DialogPanel className="surface w-full max-w-md p-6">
            <DialogTitle className="text-lg font-semibold">
              Delete selected research?
            </DialogTitle>
            <Description className="mt-3 text-sm leading-6 text-slate-400">
              Saved research for {selected.join(', ')} will be permanently
              deleted from the shared workspace. This cannot be undone.
            </Description>
            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <AnimatedAction
                disabled={deleting}
                onClick={() => setConfirm(false)}
                className="button-secondary"
              >
                Cancel
              </AnimatedAction>
              <AnimatedAction
                disabled={deleting}
                onClick={() => void remove()}
                className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete research'}
              </AnimatedAction>
            </div>
          </DialogPanel>
          </div>
        </div>
      </Dialog>
    </section>
  )
}

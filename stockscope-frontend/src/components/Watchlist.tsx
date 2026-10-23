'use client'

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
          <button
            className="button-secondary text-xs"
            onClick={() => {
              setManaging(!managing)
              setSelected([])
            }}
          >
            {managing ? 'Done' : 'Manage watchlist'}
          </button>
        )}
      </div>
      <div className="surface overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-3">
          <label className="flex items-center gap-2 text-slate-500">
            <Search className="h-4 w-4" />
            <input
              aria-label="Filter watchlist"
              placeholder="Find a company…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-44 bg-transparent py-1 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none"
            />
          </label>
          <select
            aria-label="Sort watchlist"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="rounded-md border border-white/[0.08] bg-[#171a22] px-2 py-1.5 text-xs text-slate-300"
          >
            <option value="symbol">Ticker A–Z</option>
            <option value="updated">Recently updated</option>
          </select>
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
            <button
              onClick={() => void refetch()}
              className="underline underline-offset-4"
            >
              Retry
            </button>
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
            <button
              onClick={() => void refetch()}
              className="button-secondary mt-4"
            >
              Try again
            </button>
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
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/[0.07] text-[10px] uppercase tracking-wider text-slate-500">
                  {managing && (
                    <th className="w-10 py-3 pl-5">
                      <input
                        type="checkbox"
                        aria-label="Select all visible companies"
                        checked={
                          filtered.length > 0 &&
                          filtered.every((s) => selected.includes(s.symbol))
                        }
                        onChange={(e) =>
                          setSelected(
                            e.target.checked
                              ? filtered.map((s) => s.symbol)
                              : [],
                          )
                        }
                      />
                    </th>
                  )}
                  <th className="px-5 py-3 font-medium">Company</th>
                  <th className="px-4 py-3 text-right font-medium">
                    Daily price
                  </th>
                  <th className="hidden px-4 py-3 font-medium sm:table-cell">
                    News tone
                  </th>
                  <th className="hidden px-4 py-3 font-medium sm:table-cell">
                    Latest evidence
                  </th>
                  <th className="w-10">
                    <span className="sr-only">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05]">
                {filtered.map((stock) => (
                  <tr
                    key={stock.symbol}
                    className="group transition-colors hover:bg-white/[0.025]"
                  >
                    {managing && (
                      <td className="pl-5">
                        <input
                          type="checkbox"
                          aria-label={`Select ${stock.symbol}`}
                          checked={selected.includes(stock.symbol)}
                          onChange={(e) =>
                            setSelected(
                              e.target.checked
                                ? [...selected, stock.symbol]
                                : selected.filter((s) => s !== stock.symbol),
                            )
                          }
                        />
                      </td>
                    )}
                    <td className="px-3 py-4 sm:px-5">
                      <Link
                        href={`/stock/${encodeURIComponent(stock.symbol)}`}
                        className="flex items-center gap-3"
                      >
                        <span className="hidden sm:block">
                          <CompanyLogo symbol={stock.symbol} />
                        </span>
                        <span>
                          <span className="font-semibold text-slate-100 group-hover:text-violet-200">
                            {stock.symbol}
                          </span>
                          <span className="mt-0.5 block max-w-[95px] truncate sm:max-w-48 text-xs text-slate-500">
                            {stock.companyName || 'Company research'}
                          </span>
                        </span>
                      </Link>
                    </td>
                    <td className="px-2 py-4 text-right tabular-nums sm:px-4">
                      <span className="font-medium">
                        {stock.currentPrice != null &&
                        Number.isFinite(stock.currentPrice)
                          ? `$${stock.currentPrice.toFixed(2)}`
                          : '—'}
                      </span>
                      <span className="mt-0.5 block text-[10px] text-slate-500">
                        {dateLabel(stock.price_as_of)}
                      </span>
                    </td>
                    <td className="hidden px-4 py-4 sm:table-cell">
                      <span
                        className={`rounded-md px-2 py-1 text-[11px] ${stock.avg_sentiment == null ? 'bg-white/5 text-slate-400' : stock.avg_sentiment >= 0.05 ? 'bg-emerald-400/[0.08] text-emerald-300' : stock.avg_sentiment <= -0.05 ? 'bg-rose-400/[0.08] text-rose-300' : 'bg-amber-400/[0.08] text-amber-200'}`}
                      >
                        {stock.avg_sentiment == null
                          ? 'Unavailable'
                          : stock.avg_sentiment >= 0.05
                            ? 'Positive'
                            : stock.avg_sentiment <= -0.05
                              ? 'Negative'
                              : 'Neutral'}
                      </span>
                    </td>
                    <td className="hidden px-4 py-4 text-xs text-slate-400 sm:table-cell">
                      {dateLabel(stock.last_updated)}
                      <span className="mt-1 block text-[10px] text-slate-500">
                        {stock.total_posts == null
                          ? 'Count unavailable'
                          : `${stock.total_posts.toLocaleString()} evidence records`}
                      </span>
                    </td>
                    <td className="pr-2 sm:pr-4">
                      <Link
                        href={`/stock/${encodeURIComponent(stock.symbol)}`}
                        aria-label={`Open ${stock.symbol} research`}
                        className="inline-flex rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-violet-300"
                      >
                        <ArrowUpRight className="h-4 w-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {managing && (
          <div className="flex items-center justify-between gap-3 border-t border-white/10 px-5 py-3">
            <span className="text-xs text-slate-400">
              {selected.length} selected
            </span>
            <button
              disabled={!selected.length}
              onClick={() => setConfirm(true)}
              className="button-secondary text-xs text-rose-300 disabled:opacity-40"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete selected
            </button>
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
        <div className="fixed inset-0 flex items-center justify-center p-5">
          <DialogPanel className="surface w-full max-w-md p-6">
            <DialogTitle className="text-lg font-semibold">
              Delete selected research?
            </DialogTitle>
            <Description className="mt-3 text-sm leading-6 text-slate-400">
              Saved research for {selected.join(', ')} will be permanently
              deleted from the shared workspace. This cannot be undone.
            </Description>
            <div className="mt-6 flex justify-end gap-3">
              <button
                disabled={deleting}
                onClick={() => setConfirm(false)}
                className="button-secondary"
              >
                Cancel
              </button>
              <button
                disabled={deleting}
                onClick={() => void remove()}
                className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete research'}
              </button>
            </div>
          </DialogPanel>
        </div>
      </Dialog>
    </section>
  )
}

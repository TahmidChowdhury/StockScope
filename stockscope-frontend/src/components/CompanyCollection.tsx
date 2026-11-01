'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Pin, ArrowUpRight } from 'lucide-react'
import { useWatchlist } from '@/hooks/useWatchlist'
import { useLists, useListAction } from '@/hooks/useLists'
import SaveCompany from './SaveCompany'
import CompanyLogo from './CompanyLogo'
import CompanyQuickView, { shareClass } from './CompanyQuickView'

export default function CompanyCollection({ compact = false, listId = '' }: { compact?: boolean; listId?: string }) {
  const { data: stocks = [], isPending, isError, refetch } = useWatchlist()
  const { data: lists = [] } = useLists()
  const action = useListAction()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [notice, setNotice] = useState('')
  const list = lists.find(value => value.id === listId)
  const pinned = new Set((list ? [list] : lists).flatMap(value => value.items.filter(item => item.pinned).map(item => item.symbol)))
  const deskStocks = compact ? [...stocks, ...[...pinned].filter(symbol => !stocks.some(stock => stock.symbol === symbol)).map(symbol => ({ symbol, companyName: symbol, last_updated: null }))] : stocks
  const source = list ? list.items.map(item => stocks.find(stock => stock.symbol === item.symbol) || { symbol: item.symbol, companyName: item.symbol, last_updated: null }) : deskStocks
  const filtered = source.filter(stock => `${stock.symbol} ${stock.companyName}`.toLowerCase().includes(search.toLowerCase()))
    .slice().sort((a, b) => Number(pinned.has(b.symbol)) - Number(pinned.has(a.symbol)) || a.symbol.localeCompare(b.symbol))
  const pageSize = compact ? 6 : 25
  const currentPage = Math.min(page, Math.max(0, Math.ceil(filtered.length / pageSize) - 1))
  const shown = filtered.slice(currentPage * pageSize, currentPage * pageSize + pageSize)
  return <section className="surface overflow-hidden" aria-label={list?.name || 'Saved companies'}>
    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 p-5">
      <div><h2 className="font-medium">{list?.name || (compact ? 'On your desk' : 'Research library')}</h2><p className="mt-1 text-xs text-slate-500">{compact ? (list ? `${filtered.length} saved companies · Private list` : 'Shared research') : `${filtered.length} ${filtered.length === 1 ? 'company' : 'companies'} · ${list ? 'Private list' : 'Shared research'}`}</p></div>
      {compact ? <Link href={list ? `/lists?list=${encodeURIComponent(list.id)}` : "/lists?view=shared"} className="inline-flex min-h-11 items-center text-xs text-sage-300">{list ? "View list →" : "All companies & lists →"}</Link> : <input aria-label="Find a company in this list" placeholder="Find a company…" value={search} onChange={e => { setSearch(e.target.value); setPage(0) }} className="field-input w-full sm:w-56" />}
    </div>
    {isError && <div role="status" className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-5 text-sm text-amber-200"><p>Research could not be updated. {stocks.length ? 'Previously loaded summaries are shown.' : 'Your lists are still available.'}</p><button onClick={() => void refetch()} className="underline">Retry loading research</button></div>}
    {isPending && !list ? <p role="status" className="p-8 text-sm text-slate-400">Loading saved companies…</p> : shown.length ? <ul className="divide-y divide-white/[0.06]">{shown.map(stock => {
      const item = list?.items.find(value => value.symbol === stock.symbol)
      return <li key={stock.symbol} className="grid grid-cols-[auto_minmax(0,1fr)_auto_auto] items-center gap-x-3 gap-y-2 px-4 py-2 sm:flex sm:flex-wrap sm:gap-4 sm:px-5">
        <CompanyLogo symbol={stock.symbol} size="small" />
        <CompanyQuickView stock={stock}><span className="flex items-center gap-2 font-medium group-hover/preview:text-sage-300">{stock.symbol}{pinned.has(stock.symbol) && <Pin aria-label="Pinned" className="h-3 w-3 text-sage-300" />}</span><span className="mt-1 block truncate text-xs text-slate-500">{stock.companyName || 'Company research'}{shareClass(stock.symbol) ? ` · ${shareClass(stock.symbol)}` : ''}</span></CompanyQuickView>
        <p className="hidden text-xs text-slate-500 md:block">{stock.last_updated ? `Evidence · ${new Date(stock.last_updated).toLocaleDateString('en-US', { timeZone: 'UTC' })}` : 'Evidence date unavailable'}</p>
        {list && item ? (
          <div className="col-span-2 col-start-2 row-start-2 flex items-center gap-2">
            <button disabled={action.isPending} onClick={() => {
              setNotice('')
              action.mutate({ path: `/api/lists/${list.id}/items`, method: 'PUT', body: { symbol: stock.symbol, pinned: !item.pinned } }, {
                onSuccess: () => setNotice(`${item.pinned ? 'Unpinned' : 'Pinned'} ${stock.symbol} in “${list.name}”.`),
              })
            }} aria-label={`${item.pinned ? 'Unpin' : 'Pin'} ${stock.symbol}`} className="flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/5">
              <Pin className={`h-4 w-4 ${item.pinned ? 'text-sage-300' : 'text-slate-500'}`} />
            </button>
            <button disabled={action.isPending} onClick={() => {
              setNotice('')
              action.mutate({ path: `/api/lists/${list.id}/items/${encodeURIComponent(stock.symbol)}`, method: 'DELETE' }, {
                onSuccess: () => setNotice(`Removed ${stock.symbol} from “${list.name}”.`),
              })
            }} aria-label={`Remove ${stock.symbol} from ${list.name}`} className="min-h-11 rounded-md px-2 text-xs text-slate-300 hover:bg-white/5">
              Remove
            </button>
          </div>
        ) : !compact && <div className="col-start-3 row-start-1"><SaveCompany symbol={stock.symbol} compact /></div>}
        <Link href={`/stock/${encodeURIComponent(stock.symbol)}`} aria-label={`View ${stock.symbol} details`} className="col-start-4 row-start-1 flex h-11 min-w-11 items-center justify-center gap-2 text-xs text-sage-300">{(list && item) ? <span className="hidden sm:inline">View details</span> : <span className="sr-only sm:not-sr-only">View details</span>}<ArrowUpRight className="h-3 w-3" /></Link>
      </li>
    })}</ul> : isError && !list && !source.length ? null : <div className="p-8 text-sm leading-6 text-slate-400">{search ? 'No companies match your search.' : list ? 'Add a ticker above to start this list. Saving a ticker does not trigger a data refresh.' : 'No saved companies yet. Open a company to begin your research.'}</div>}
    {notice && <p role="status" className="p-4 text-sm text-sage-300">{notice}</p>}
    {action.error && <p role="alert" className="p-4 text-sm text-amber-200">{action.error.message}</p>}
    {!compact && filtered.length > pageSize && <div className="flex items-center justify-between border-t border-white/10 p-4 text-xs"><button className="button-secondary" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous</button><span className="text-slate-400">{currentPage * pageSize + 1}–{Math.min((currentPage + 1) * pageSize, filtered.length)} of {filtered.length}</span><button className="button-secondary" disabled={(currentPage + 1) * pageSize >= filtered.length} onClick={() => setPage(currentPage + 1)}>Next</button></div>}
  </section>
}

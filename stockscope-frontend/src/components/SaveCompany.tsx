'use client'

import Link from 'next/link'
import { Dialog, DialogPanel, DialogTitle, Description } from '@headlessui/react'
import { Bookmark, Check, FolderPlus, X } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { useState, type FormEvent } from 'react'
import { getAuthSession } from '@/lib/api'
import { useLists, useListAction, type PersonalList } from '@/hooks/useLists'

export default function SaveCompany({ symbol, compact = false }: { symbol: string; compact?: boolean }) {
  const { data: lists = [], isPending, isError, isFetching, refetch } = useLists()
  const action = useListAction()
  const reduced = useReducedMotion()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [notice, setNotice] = useState('')
  const [creating, setCreating] = useState(false)
  const memberships = lists.filter(list => list.items.some(item => item.symbol === symbol))
  const busy = creating || action.isPending

  const toggle = (list: PersonalList, saved: boolean) => {
    setNotice('')
    const path = `/api/lists/${encodeURIComponent(list.id)}/items`
    action.mutate(saved
      ? { path: `${path}/${encodeURIComponent(symbol)}`, method: 'DELETE' }
      : { path: `${path}/batch`, method: 'PUT', body: { symbols: [symbol] } }, {
      onSuccess: () => setNotice(saved ? `Removed ${symbol} from ${list.name}.` : `Added ${symbol} to ${list.name}.`),
    })
  }

  const create = async (event: FormEvent) => {
    event.preventDefault()
    if (busy || !name.trim()) return
    setNotice('')
    setCreating(true)
    try {
      const created: PersonalList = await action.mutateAsync({ path: '/api/lists', method: 'POST', body: { name: name.trim(), initial_symbol: symbol } })
      setName('')
      // Older local backends create the list without initial_symbol support.
      // Keep that list available if adding fails so the user can retry its checkbox.
      if (!created.items.some(item => item.symbol === symbol)) {
        setNotice(`Created ${created.name}. If saving fails, select this list to retry.`)
        await action.mutateAsync({ path: `/api/lists/${encodeURIComponent(created.id)}/items/batch`, method: 'PUT', body: { symbols: [symbol] } })
      }
      setNotice(`Created ${created.name} and added ${symbol}.`)
    } catch { /* The mutation error is displayed in the modal. */ }
    finally { setCreating(false) }
  }

  return <>
    <button type="button" onClick={() => setOpen(true)} aria-label={`Manage lists for ${symbol}`} aria-haspopup="dialog" title={memberships.length ? `${symbol} saved — manage lists` : `Save ${symbol} to a list`} className={`inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg text-[#b6c8ab] hover:bg-white/5 ${compact ? 'w-11' : 'px-2 text-xs'}`}>
      <motion.span key={memberships.length ? 'saved' : 'unsaved'} initial={reduced ? false : { scale: 0.65, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 400, damping: 20 }}>
        {memberships.length ? <Check aria-hidden="true" className="h-4 w-4" /> : <Bookmark aria-hidden="true" className="h-4 w-4" />}
      </motion.span>
      {!compact && (memberships.length ? 'Saved' : 'Save to lists')}
    </button>
    <Dialog open={open} onClose={setOpen} className="relative z-[100]">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-end justify-center p-3 sm:items-center sm:p-6">
        <DialogPanel className="surface flex max-h-[calc(100dvh-1.5rem)] w-full max-w-lg flex-col overflow-hidden rounded-2xl shadow-2xl sm:max-h-[85dvh]">
          <div className="flex shrink-0 items-start justify-between gap-3 border-b border-white/10 p-5">
            <div><DialogTitle className="text-lg font-semibold text-white">Your lists</DialogTitle><Description className="mt-1 text-sm text-slate-400">Choose where to save {symbol}. Changes save immediately.</Description></div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close lists" className="-mr-2 -mt-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-white/5"><X aria-hidden="true" className="h-5 w-5" /></button>
          </div>
          <div className="min-h-0 overflow-y-auto overscroll-contain p-5">
            {!getAuthSession()?.user ? <Link href="/account" className="inline-flex min-h-11 items-center text-sm text-[#b6c8ab]">Sign in with a personal account →</Link> : isPending ? <p role="status" className="py-6 text-sm text-slate-400">Loading your lists…</p> : isError ? <p role="alert" className="text-sm text-amber-200">Couldn’t load your lists. <button disabled={isFetching} className="min-h-11 underline" onClick={() => void refetch()}>Retry</button></p> : <>
              {lists.length ? <fieldset disabled={busy} className="space-y-2">
                <legend className="sr-only">Lists containing {symbol}</legend>
                {lists.map(list => {
                  const saved = memberships.some(member => member.id === list.id)
                  return <div key={list.id} className={`rounded-xl border p-3 ${saved ? 'border-[#b6c8ab]/40 bg-[#b6c8ab]/5' : 'border-white/10'}`}>
                    <label className="flex min-h-11 cursor-pointer items-center gap-3">
                      <input type="checkbox" aria-label={`${symbol} in ${list.name}`} checked={saved} onChange={() => toggle(list, saved)} className="h-5 w-5 shrink-0 accent-[#b6c8ab]" />
                      <span className="min-w-0 flex-1"><span className="block break-words text-sm font-medium text-slate-200">{list.name}</span><span className="mt-1 block text-xs text-slate-500">{list.items.length} {list.items.length === 1 ? 'company' : 'companies'}</span></span>
                    </label>
                    <div className="ml-8 mt-2 flex flex-wrap gap-1.5" aria-label={`Companies in ${list.name}`}>
                      {list.items.length ? list.items.map(item => <span key={item.symbol} className="rounded-md bg-white/5 px-2 py-1 text-xs text-slate-400">{item.symbol}</span>) : <span className="text-xs text-slate-500">No companies yet</span>}
                    </div>
                    <Link href={`/lists?list=${encodeURIComponent(list.id)}`} onClick={() => setOpen(false)} className="ml-8 mt-1 inline-flex min-h-11 items-center text-xs text-[#b6c8ab]">Open list →</Link>
                  </div>
                })}
              </fieldset> : <p className="pb-5 text-sm text-slate-400">Create your first list to keep {symbol} close.</p>}
              <form onSubmit={event => void create(event)} className="mt-5 border-t border-white/10 pt-5">
                <label htmlFor={`new-list-${symbol}-${compact ? 'row' : 'header'}`} className="flex items-center gap-2 text-sm font-medium text-slate-200"><FolderPlus aria-hidden="true" className="h-4 w-4" />Create a new list</label>
                <input id={`new-list-${symbol}-${compact ? 'row' : 'header'}`} aria-label="New list name" className="field-input mt-3 block w-full" maxLength={80} disabled={busy} required placeholder="e.g. Long-term picks" value={name} onChange={e => setName(e.target.value)} />
                <button className="button-primary mt-3 min-h-11 w-full" disabled={busy || !name.trim()}>{creating ? 'Creating…' : `Create list and add ${symbol}`}</button>
              </form>
            </>}
            {action.error && <p role="alert" className="mt-3 text-sm text-amber-200">{action.error.message}</p>}
            <p role="status" className="mt-3 text-xs text-[#b6c8ab]">{busy ? 'Saving…' : notice}</p>
          </div>
          <div className="shrink-0 border-t border-white/10 px-5 py-3"><button type="button" onClick={() => setOpen(false)} className="button-secondary min-h-11 w-full">Done</button></div>
        </DialogPanel>
      </div>
    </Dialog>
  </>
}

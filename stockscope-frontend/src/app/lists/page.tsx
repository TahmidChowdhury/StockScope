'use client'
import { useEffect, useState, type FormEvent } from 'react'
import AppShell from '@/components/AppShell'
import CompanyCollection from '@/components/CompanyCollection'
import AnimatedSelect from '@/components/ui/AnimatedSelect'
import AnimatedAccordion from '@/components/ui/AnimatedAccordion'
import { useLists, useListAction } from '@/hooks/useLists'
import { getAuthSession } from '@/lib/api'
import Link from 'next/link'

export default function ListsPage() {
  const { data: lists = [], isError, isPending } = useLists()
  const action = useListAction()
  const [selected, setSelected] = useState('')
  const [name, setName] = useState('')
  const [ticker, setTicker] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [rename, setRename] = useState('')
  const list = lists.find(value => value.id === selected)
  const individual = !!getAuthSession()?.user
  useEffect(() => { setSelected(new URLSearchParams(window.location.search).get('list') || '') }, [])
  const selectList = (id: string) => {
    setSelected(id); setConfirm(false); setRename('')
    window.history.replaceState(null, '', id ? `/lists?list=${encodeURIComponent(id)}` : '/lists')
  }
  const create = async (event: FormEvent) => {
    event.preventDefault()
    try { const result = await action.mutateAsync({ path: '/api/lists', method: 'POST', body: { name } }); selectList(result.id); setName('') } catch {}
  }
  const add = async (event: FormEvent) => {
    event.preventDefault()
    if (!list) return
    try { await action.mutateAsync({ path: `/api/lists/${list.id}/items/batch`, method: 'PUT', body: { symbols: ticker.toUpperCase().split(/[\s,]+/).filter(Boolean) } }); setTicker('') } catch {}
  }
  return <AppShell><h1 className="font-serif text-3xl">Companies & lists</h1><p className="mt-3 text-sm leading-6 text-slate-400">Your lists are personal. Saved company research is shared with approved members.</p>
    {!individual ? <p className="my-6 text-sm text-amber-200"><Link href="/account" className="underline">Set up your owner account</Link> to start using personal lists.</p> : <div className="my-7 grid gap-4 sm:grid-cols-2 sm:items-end"><label className="min-w-0 text-xs text-slate-400">View<AnimatedSelect aria-label="Choose a list" value={selected} onValueChange={selectList} className="field-input mt-2 w-full"><option value="">All saved research</option>{lists.map(value => <option key={value.id} value={value.id}>{value.name} ({value.items.length})</option>)}</AnimatedSelect></label><form onSubmit={create} className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-2"><label className="text-xs text-slate-400">New list<input required maxLength={80} placeholder="e.g. Earnings watch" value={name} onChange={e => setName(e.target.value)} className="field-input mt-2 block" /></label><button disabled={action.isPending || !name.trim()} className="button-secondary">Create list</button></form></div>}
    {individual && isPending && <p className="my-4 text-sm text-slate-400">Loading your lists…</p>}
    {isError && <p role="alert" className="my-4 text-sm text-amber-200">Your lists could not be loaded. Please reload to try again.</p>}
    {list && <div className="mb-6 rounded-xl border border-white/10 p-5"><form onSubmit={add} className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[minmax(0,1fr)_auto]"><label className="text-xs text-slate-400">Add tickers<input required maxLength={550} value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} placeholder="AAPL, MSFT, NVDA" className="field-input mt-2 block w-full" /></label><button disabled={action.isPending} className="button-secondary">Add to list</button><p className="text-xs leading-5 text-slate-500 sm:col-span-2">Paste up to 50 tickers, separated by commas or spaces.</p></form><AnimatedAccordion title="Manage list" className="mt-4 border-t border-white/10 pt-2" triggerClassName="text-xs text-slate-400"><div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 pb-3"><input aria-label="Rename list" value={rename} placeholder={list.name} maxLength={80} onChange={e => setRename(e.target.value)} className="field-input text-xs" /><button disabled={!rename.trim() || action.isPending} className="min-h-11 px-2 text-xs text-slate-400" onClick={() => action.mutate({ path: `/api/lists/${list.id}`, method: 'PUT', body: { name: rename } })}>Rename</button><button onClick={() => setConfirm(!confirm)} className="min-h-11 text-left text-xs text-slate-500">Delete list</button></div>{confirm && <div className="mt-4 flex flex-wrap items-center gap-4 text-sm"><p>Delete “{list.name}”? Shared research stays saved.</p><button className="text-red-300" disabled={action.isPending} onClick={async () => { try { await action.mutateAsync({ path: `/api/lists/${list.id}`, method: 'DELETE' }); selectList('') } catch {} }}>Delete this list</button><button onClick={() => setConfirm(false)}>Cancel</button></div>}</AnimatedAccordion></div>}
    {action.error && <p role="alert" className="mb-4 text-sm text-amber-200">{action.error.message}</p>}
    <CompanyCollection key={list?.id || 'library'} listId={list?.id} />
  </AppShell>
}

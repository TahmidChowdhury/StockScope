'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useRef, useState, type FormEvent } from 'react'
import SavedConfirmation from '@/components/SavedConfirmation'
import AppShell from '@/components/AppShell'
import CompanyCollection from '@/components/CompanyCollection'
import AnimatedSelect from '@/components/ui/AnimatedSelect'
import { useLists, useListAction, type PersonalList } from '@/hooks/useLists'
import { getAuthSession } from '@/lib/api'

function selectList(id: string, addSymbol = '') {
  window.history.pushState(null, '', id ? `/lists?list=${encodeURIComponent(id)}${addSymbol ? `&add=${encodeURIComponent(addSymbol)}` : ''}` : '/lists?view=shared')
}

function ListControls({ list, onDelete, initialTicker = '' }: { list: PersonalList; onDelete: () => void; initialTicker?: string }) {
  const action = useListAction()
  const [ticker, setTicker] = useState(initialTicker)
  const [rename, setRename] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [notice, setNotice] = useState('')
  const symbols = [...new Set(ticker.toUpperCase().split(/[\s,]+/).filter(Boolean))]
  const path = `/api/lists/${encodeURIComponent(list.id)}`
  const add = (event: FormEvent) => {
    event.preventDefault()
    if (!symbols.length || symbols.length > 50) return
    setNotice('')
    action.mutate({ path: `${path}/items/batch`, method: 'PUT', body: { symbols } }, {
      onSuccess: () => {
        setTicker('')
        setNotice(symbols.length === 1 ? `${symbols[0]} is in “${list.name}”.` : `All ${symbols.length} tickers are in “${list.name}”.`)
      },
    })
  }

  return (
    <section aria-label={`Manage ${list.name}`} className="surface mb-6 space-y-4 p-5">
      <form onSubmit={add} className="grid items-end gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
        <label className="text-sm">Add tickers to “{list.name}”
          <input required maxLength={550} value={ticker} disabled={action.isPending}
            onChange={event => setTicker(event.target.value.toUpperCase())} placeholder="AAPL, MSFT, NVDA"
            aria-describedby="ticker-hint" className="field-input mt-2 block w-full" />
        </label>
        <button disabled={action.isPending || !symbols.length || symbols.length > 50} className="button-secondary">Add to list</button>
        <p id="ticker-hint" className="text-xs text-slate-400 sm:col-span-2">{symbols.length > 50 ? 'Reduce your selection to 50 tickers.' : 'Enter up to 50 tickers, separated by commas or spaces.'}</p>
      </form>
      <div className="flex flex-wrap items-start justify-between gap-3 border-t border-white/10 pt-3">
        <details className="min-w-0">
          <summary className="min-h-11 cursor-pointer py-3 text-sm text-slate-300">Rename list</summary>
          <form className="flex flex-wrap items-end gap-2" onSubmit={event => {
            event.preventDefault()
            setNotice('')
            action.mutate({ path, method: 'PUT', body: { name: rename.trim() } }, { onSuccess: result => {
              setRename('')
              setNotice(`List renamed to “${result.name}”.`)
            } })
          }}>
            <label className="text-xs text-slate-400">New name<input required maxLength={80} placeholder={list.name} value={rename}
              disabled={action.isPending} onChange={event => setRename(event.target.value)} className="field-input mt-1 block w-full" /></label>
            <button disabled={action.isPending || !rename.trim() || rename.trim() === list.name} className="button-secondary">Rename</button>
          </form>
        </details>
        <button type="button" aria-expanded={confirm} disabled={action.isPending}
          onClick={() => setConfirm(!confirm)} className="min-h-11 text-sm text-red-300">Delete list</button>
      </div>
      {confirm && <div className="rounded-lg border border-red-300/25 p-4">
        <p className="text-sm">Delete “{list.name}”? This removes the list and its memberships. Shared research stays available.</p>
        <div className="mt-2 flex flex-wrap gap-4 text-sm">
          <button className="min-h-11 text-red-300" disabled={action.isPending} onClick={() => {
            setNotice('')
            void action.mutateAsync({ path, method: 'DELETE' }).then(onDelete, () => {})
          }}>Delete this list</button>
          <button className="min-h-11" disabled={action.isPending} onClick={() => setConfirm(false)}>Cancel</button>
        </div>
      </div>}
      {notice && <SavedConfirmation>{notice}</SavedConfirmation>}
      {action.error && <p role="alert" className="text-sm text-amber-200">{action.error.message}</p>}
    </section>
  )
}

function ListsWorkspace() {
  const params = useSearchParams()
  const addSymbol = params.get('add') || ''
  const pendingTicker = /^[A-Z][A-Z0-9.-]{0,9}$/.test(addSymbol) ? addSymbol : ''
  const createInput = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (pendingTicker) {
      createInput.current?.focus({ preventScroll: true })
      createInput.current?.scrollIntoView({ block: 'center', behavior: 'instant' })
    }
  }, [pendingTicker])
  const session = getAuthSession()
  const individual = !!session?.user
  const { data: lists = [], isError, isPending, refetch } = useLists()
  const selected = params.get('list') || (params.has('list') || params.get('view') === 'shared' || pendingTicker ? '' : (lists.find(list => list.items.length > 0) || lists[0])?.id || '')
  const create = useListAction()
  const [name, setName] = useState('')
  const [notice, setNotice] = useState<{ id: string; text: string } | null>(null)
  const list = lists.find(value => value.id === selected)
  const missing = individual && selected && !list && !isPending && !isError

  return <>
    <h1 className="font-serif text-3xl">Companies &amp; lists</h1>
    <p className="mt-3 text-sm text-slate-400">Your lists are personal. Saved research is shared with approved members.</p>
    {pendingTicker && !list && <p role="status" className="mt-4 text-sm text-[#b6c8ab]">Create a list to save {pendingTicker}, or choose an existing list.</p>}
    {individual ? <div className="my-6 grid gap-4 sm:grid-cols-2 sm:items-end">
      <label className="min-w-0 text-xs text-slate-400">View
        <AnimatedSelect aria-label="Choose a list" value={selected} onValueChange={id => { setNotice(null); selectList(id, pendingTicker) }} className="field-input mt-2 w-full">
          <option value="">All saved research</option>
          {selected && !list && <option value={selected} disabled>{isPending ? 'Loading selected list…' : 'Selected list unavailable'}</option>}
          {lists.map(value => <option key={value.id} value={value.id}>{value.name} ({value.items.length})</option>)}
        </AnimatedSelect>
      </label>
      <form onSubmit={event => {
        event.preventDefault()
        setNotice(null)
        create.mutate({ path: '/api/lists', method: 'POST', body: { name: name.trim(), ...(pendingTicker ? { initial_symbol: pendingTicker } : {}) } }, { onSuccess: result => {
          setName('')
          setNotice({ id: result.id, text: pendingTicker ? `Created “${result.name}” and saved ${pendingTicker}.` : `Created “${result.name}”.` })
          selectList(result.id)
        } })
      }} className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-2">
        <label className="text-xs text-slate-400">New list<input ref={createInput} required maxLength={80} disabled={create.isPending}
          placeholder="e.g. Earnings watch" value={name} onChange={event => setName(event.target.value)} className="field-input mt-2 block w-full" /></label>
        <button disabled={create.isPending || !name.trim()} className="button-secondary">{create.isPending ? 'Creating…' : 'Create list'}</button>
      </form>
    </div> : <p className="my-6 text-sm text-slate-300">
      <Link href="/account" className="underline">{session?.role === 'admin' ? 'Set up your owner account' : 'Sign in with an individual account'}</Link> to use personal lists.
    </p>}
    {individual && isPending && <p role="status" className="mb-4 text-sm text-slate-400">Loading your lists…</p>}
    {individual && isError && <p role="alert" className="mb-4 text-sm text-amber-200">Your lists could not be loaded. <button className="underline" onClick={() => void refetch()}>Retry</button></p>}
    {missing && <p role="status" className="mb-4 text-sm text-slate-300">This list is unavailable. <Link href="/lists?view=shared" className="underline">View all saved research</Link></p>}
    {notice?.id === selected && <p role="status" className="mb-4 text-sm text-[#b6c8ab]">{notice.text}</p>}
    {create.error && <p role="alert" className="mb-4 text-sm text-amber-200">{create.error.message}</p>}
    {individual && list && !isError && <ListControls key={`controls-${list.id}-${pendingTicker}`} list={list} initialTicker={pendingTicker} onDelete={() => {
      setNotice({ id: '', text: `Deleted “${list.name}”.` })
      selectList('')
    }} />}
    {(!selected || (individual && list && !isError)) && <CompanyCollection key={`companies-${selected}`} listId={selected} />}
    {!individual && selected && <Link href="/lists?view=shared" className="text-sm underline">View all saved research</Link>}
  </>
}

export default function ListsPage() {
  return <AppShell><Suspense fallback={<p role="status">Loading lists…</p>}><ListsWorkspace /></Suspense></AppShell>
}

'use client'

import Link from 'next/link'
import { useState, type FormEvent } from 'react'
import { getAuthSession } from '@/lib/api'
import { useLists, useListAction, type PersonalList } from '@/hooks/useLists'

export default function SaveCompany({ symbol }: { symbol: string }) {
  const { data: lists = [], isPending, isError, refetch } = useLists()
  const action = useListAction()
  const [name, setName] = useState('')
  const [notice, setNotice] = useState('')
  const memberships = lists.filter(list => list.items.some(item => item.symbol === symbol))

  if (!getAuthSession()?.user) {
    return <Link className="text-xs underline" href="/account">Sign in with a personal account to use lists</Link>
  }

  const toggle = (list: PersonalList, saved: boolean) => {
    setNotice('')
    const path = `/api/lists/${list.id}/items`
    action.mutate(saved
      ? { path: `${path}/${encodeURIComponent(symbol)}`, method: 'DELETE' }
      : { path: `${path}/batch`, method: 'PUT', body: { symbols: [symbol] } }, {
      onSuccess: () => setNotice(saved ? `Removed ${symbol} from ${list.name}.` : `Added ${symbol} to ${list.name}.`),
    })
  }

  const create = (event: FormEvent) => {
    event.preventDefault()
    setNotice('')
    action.mutate({ path: '/api/lists', method: 'POST', body: { name: name.trim(), initial_symbol: symbol } }, {
      onSuccess: (created: PersonalList) => {
        setNotice(created.items.some(item => item.symbol === symbol)
          ? `Created ${created.name} and added ${symbol}.`
          : `Created ${created.name}. Select it above to add ${symbol}.`)
        setName('')
      },
    })
  }

  return (
    <details className="min-w-0 text-sm">
      <summary className="cursor-pointer py-3 text-[#b6c8ab]" aria-label={`Manage lists for ${symbol}`}>
        {memberships.length ? `Saved in ${memberships.length} ${memberships.length === 1 ? 'list' : 'lists'}` : 'Save to lists'}
      </summary>
      <div className="space-y-2 rounded-lg border border-white/10 p-3">
        {isPending ? <p role="status">Loading lists…</p> : isError ? (
          <p role="alert">Couldn’t load your lists. <button className="underline" onClick={() => void refetch()}>Retry</button></p>
        ) : (
          <>
            <fieldset disabled={action.isPending}>
              <legend className="text-xs text-slate-400">Lists containing {symbol}</legend>
              {lists.map(list => {
                const saved = memberships.some(member => member.id === list.id)
                const pending = action.isPending && action.variables?.path.startsWith(`/api/lists/${list.id}/items`)
                return <label key={list.id} className="flex min-h-11 cursor-pointer items-center gap-2">
                  <input type="checkbox" checked={pending ? action.variables?.method === 'PUT' : saved} onChange={() => toggle(list, saved)} />
                  {list.name}
                </label>
              })}
            </fieldset>
            <form onSubmit={create} className="flex flex-wrap gap-2">
              <input aria-label="New list name" className="field-input min-w-0 flex-1" maxLength={80} disabled={action.isPending} required placeholder="New list name" value={name} onChange={e => setName(e.target.value)} />
              <button className="button-secondary text-xs" disabled={action.isPending || !name.trim()}>Create list and add {symbol}</button>
            </form>
          </>
        )}
        {action.error && <p role="alert" className="text-xs text-amber-200">{action.error.message}</p>}
        <p role="status" className="text-xs text-slate-300">{action.isPending ? 'Saving…' : notice}</p>
      </div>
    </details>
  )
}

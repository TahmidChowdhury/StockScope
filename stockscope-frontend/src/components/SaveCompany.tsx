'use client'
import Link from 'next/link'
import { useState } from 'react'
import { useLists, useListAction } from '@/hooks/useLists'
import AnimatedSelect from './ui/AnimatedSelect'
export default function SaveCompany({ symbol }: { symbol: string }) {
  const { data: lists = [], isError } = useLists()
  const action = useListAction()
  const [listId, setListId] = useState('')
  const target = lists.find(list => list.id === listId)
  if (!lists.length) return <Link href="/lists" className="text-xs text-[#b6c8ab] underline underline-offset-4">{isError ? 'Lists unavailable' : 'Create a list to save companies'}</Link>
  return <div className="grid w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-2 sm:w-auto">
    <AnimatedSelect aria-label={`Save ${symbol} to list`} value={listId} onValueChange={setListId} className="field-input !mt-0 min-w-0 text-xs sm:w-44"><option value="">Save to list…</option>{lists.map(list => <option key={list.id} value={list.id}>{list.name}</option>)}</AnimatedSelect>
    {target && <button disabled={action.isPending} className="button-secondary text-xs" onClick={() => action.mutate({ path: `/api/lists/${target.id}/items`, method: 'PUT', body: { symbol, pinned: target.items.find(item => item.symbol === symbol)?.pinned ?? false } })}>{action.isPending ? 'Saving…' : target.items.some(item => item.symbol === symbol) ? 'Saved' : 'Save'}</button>}
    {action.error && <p role="alert" className="col-span-2 text-xs text-amber-200">{action.error.message}</p>}
  </div>
}

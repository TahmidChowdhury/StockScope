'use client'
import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/AppShell'
import MarketTape from '@/components/MarketTape'
import StockSearch from '@/components/StockSearch'
import CompanyCollection from '@/components/CompanyCollection'
import { useLists } from '@/hooks/useLists'
import AnimatedSelect from '@/components/ui/AnimatedSelect'
import { getAuthSession } from '@/lib/api'

export default function Home() {
  const router = useRouter()
  const [opening, startTransition] = useTransition()
  const session = getAuthSession()
  const { data: lists = [], isPending, isError, refetch } = useLists()
  const [selected, setSelected] = useState('')
  const personalList = lists.find(list => list.id === selected) || lists.find(list => list.items.length > 0) || lists[0]
  return <AppShell>
    <header className="mb-5">
      <h1 className="page-title">Company research</h1>
      {session?.isFirstSession && <p className="mt-2 text-sm leading-6 text-slate-400">Welcome to StockScope. Search for a company, then save it to a list.</p>}
    </header>
    <MarketTape />
    <div className="mb-6 max-w-2xl"><StockSearch compact isLoading={opening} onAnalyze={symbol => startTransition(() => router.push(`/stock/${encodeURIComponent(symbol)}`))} /></div>
    {session?.user && isPending ? <p role="status" className="text-sm text-slate-400">Loading your saved lists…</p> : session?.user && isError ? <p role="alert" className="text-sm text-amber-200">Your saved lists could not be loaded. <button onClick={() => void refetch()} className="min-h-11 underline">Retry</button></p> : <>
      {personalList && lists.length > 1 && <label className="mb-4 block max-w-sm text-xs text-slate-400">Your saved lists<AnimatedSelect aria-label="Overview saved list" value={personalList.id} onValueChange={setSelected} className="mt-2">{lists.map(list => <option key={list.id} value={list.id}>{list.name} ({list.items.length})</option>)}</AnimatedSelect></label>}
      <CompanyCollection key={personalList?.id || 'library'} compact listId={personalList?.id} />
    </>}
  </AppShell>
}

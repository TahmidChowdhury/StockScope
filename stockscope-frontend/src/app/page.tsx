'use client'
import Link from 'next/link'
import { useState } from 'react'
import AnimatedSelect from '@/components/ui/AnimatedSelect'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/AppShell'
import StockSearch from '@/components/StockSearch'
import CompanyCollection from '@/components/CompanyCollection'
import { useLists } from '@/hooks/useLists'
import { getAuthSession } from '@/lib/api'

export default function Home() {
  const router = useRouter()
  const { data: lists = [], isPending, isError, refetch } = useLists()
  const [selected, setSelected] = useState('')
  const personalList = lists.find(list => list.id === selected) || lists.find(list => list.items.length > 0) || lists[0]
  const individual = !!getAuthSession()?.user
  const name = getAuthSession()?.user?.name
  return <AppShell>
    <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
      <div><p className="text-xs uppercase tracking-[0.18em] text-[#b6c8ab]">Your research desk</p><h1 className="mt-3 font-serif text-3xl tracking-tight sm:text-4xl">{name ? `Welcome back, ${name.split(' ')[0]}.` : 'A clearer view of your companies.'}</h1><p className="mt-3 text-sm leading-6 text-slate-400">Keep a short list. Follow the evidence. Pick up where you left off.</p></div>
      <Link href="/screener" className="button-secondary text-sm">Discover companies →</Link>
    </div>
    <div className="mb-8 max-w-2xl"><StockSearch compact onAnalyze={symbol => router.push(`/stock/${encodeURIComponent(symbol)}`)} /></div>
    {lists.length > 0 && <div className="mb-8 flex flex-wrap gap-2" aria-label="Your lists">{lists.slice(0, 4).map(list => <Link key={list.id} aria-label={`${list.name}, ${list.items.length} companies`} href={`/lists?list=${list.id}`} className="rounded-lg border border-white/10 px-4 py-3 text-sm text-slate-300 hover:bg-white/5">{list.name}<span className="ml-3 text-xs text-slate-500">{list.items.length}</span></Link>)}<Link href="/lists" className="px-4 py-3 text-sm text-slate-500">Manage lists →</Link></div>}
    {individual && isPending ? <p role="status">Loading your saved lists…</p> : individual && isError ? <p role="alert">Your lists could not be loaded. <button onClick={() => void refetch()} className="min-h-11 underline">Retry</button></p> : <>
      {personalList && lists.length > 1 && <label className="mb-4 block max-w-sm text-xs text-slate-400">Your saved lists<AnimatedSelect aria-label="Overview saved list" value={personalList.id} onValueChange={setSelected} className="mt-2">{lists.map(list => <option key={list.id} value={list.id}>{list.name} ({list.items.length})</option>)}</AnimatedSelect></label>}
      <CompanyCollection key={personalList?.id || 'library'} compact listId={personalList?.id} />
    </>}
    <div className="mt-8 grid gap-6 border-t border-white/10 pt-6 sm:grid-cols-2"><div><p className="text-sm text-slate-300">Find your next question</p><p className="mt-2 text-xs leading-6 text-slate-500">Explore fundamentals, compare a few companies, or follow new disclosures.</p><div className="mt-3 flex gap-5 text-xs text-[#b6c8ab]"><Link href="/compare">Compare →</Link><Link href="/disclosures">Disclosures →</Link></div></div><div><p className="text-sm text-slate-300">Saved first. Refreshed thoughtfully.</p><p className="mt-2 text-xs leading-6 text-slate-500">Opening your desk uses saved summaries. Research refreshes are shared across the workspace, with a six-hour cooldown per company.</p></div></div>
  </AppShell>
}

'use client'
import { useTransition } from 'react'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/AppShell'
import MarketTape from '@/components/MarketTape'
import StockSearch from '@/components/StockSearch'
import CompanyCollection from '@/components/CompanyCollection'
import { useWorkspaceDraft } from '@/hooks/useWorkspaceDraft'
import { useLists } from '@/hooks/useLists'
import AnimatedSelect from '@/components/ui/AnimatedSelect'
import { getAuthSession } from '@/lib/api'

const validView = (value: unknown): value is string | null =>
  value === null || (typeof value === 'string' && value.length <= 200)

export default function Home() {
  const router = useRouter()
  const [opening, startTransition] = useTransition()
  const session = getAuthSession()
  const { data: lists = [], isPending, isError, refetch } = useLists()
  // null keeps the initial personal-list default; an empty string explicitly
  // selects shared research and must not fall back to a personal list.
  const preference = useWorkspaceDraft<string | null>('dashboard-view:v1', null, validView)
  const selected = preference.value
  const personalList = selected === null
    ? lists.find(list => list.items.length > 0) || lists[0]
    : lists.find(list => list.id === selected)
  return <AppShell>
    <header className="mb-6">
      <h1 className="page-title">Company research</h1>
      <p className="mt-2 text-sm leading-6 text-slate-400">{session?.isFirstSession ? 'Search for a company, then save it to a list.' : 'Saved companies and research evidence'}</p>
    </header>
    <MarketTape />
    <div className="mb-6 max-w-2xl"><StockSearch compact isLoading={opening} onAnalyze={symbol => startTransition(() => router.push(`/stock/${encodeURIComponent(symbol)}`))} /></div>
    {session?.user && <label className="mb-4 block max-w-sm text-xs text-slate-400">Research view
      <AnimatedSelect aria-label="Research view" value={personalList?.id || ''} onValueChange={preference.setValue} disabled={!preference.ready} className="mt-2">
        <option value="">Shared research</option>
        {lists.map(list => <option key={list.id} value={list.id}>{list.name} ({list.items.length})</option>)}
      </AnimatedSelect>
    </label>}
    {preference.message && <p role="status" className="mb-4 text-xs text-amber-200">Your view selection could not be saved in this browser. It will be remembered for this visit only.</p>}
    {preference.ready && selected && !isPending && !isError && !personalList && <p role="status" className="mb-4 text-xs text-slate-400">Your previously selected list is unavailable. Showing shared research.</p>}
    {session?.user && isError && <p role="alert" className="mb-4 text-sm text-amber-200">Your saved lists could not be loaded. Shared research is still available. <button onClick={() => void refetch()} className="min-h-11 underline">Retry</button></p>}
    {!preference.ready || (session?.user && isPending && selected !== '') ? <p role="status" className="text-sm text-slate-400">Loading your saved lists…</p> : <>
      <CompanyCollection key={personalList?.id || 'library'} compact listId={personalList?.id} />
    </>}
  </AppShell>
}

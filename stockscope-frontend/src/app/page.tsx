'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/AppShell'
import StockSearch from '@/components/StockSearch'
import CompanyCollection from '@/components/CompanyCollection'
import { useLists } from '@/hooks/useLists'

export default function Home() {
  const router = useRouter()
  const { data: lists = [] } = useLists()

  return (
    <AppShell>
      <h1 className="mb-4 font-serif text-2xl tracking-tight sm:text-3xl">Your research desk</h1>
      <div className="mb-5 max-w-2xl">
        <StockSearch compact onAnalyze={symbol => router.push(`/stock/${encodeURIComponent(symbol)}`)} />
      </div>
      <CompanyCollection compact />
      {lists.length > 0 && (
        <nav aria-label="Your lists" className="mt-5 flex flex-wrap items-center gap-2">
          {lists.slice(0, 4).map(list => (
            <Link
              key={list.id}
              aria-label={`${list.name}, ${list.items.length} companies`}
              href={`/lists?list=${encodeURIComponent(list.id)}`}
              className="rounded-lg border border-white/10 px-4 py-3 text-sm text-slate-300 hover:bg-white/5"
            >
              {list.name}<span className="ml-3 text-xs text-slate-500">{list.items.length}</span>
            </Link>
          ))}
          <Link href="/lists" className="px-4 py-3 text-sm text-slate-400">Manage lists →</Link>
        </nav>
      )}
    </AppShell>
  )
}

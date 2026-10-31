'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight } from 'lucide-react'
import SideNav from './SideNav'
import SaveCompany from './SaveCompany'
import { useLists } from '@/hooks/useLists'
import { useWatchlist } from '@/hooks/useWatchlist'
import { getAuthSession } from '@/lib/api'
import { useMobileScrollRestoration } from '@/hooks/useMobileScrollRestoration'

export default function AppShell({
  children,
  company,
}: {
  children: ReactNode
  company?: string
}) {
  const { data: stocks = [], isPending, isError, refetch } = useWatchlist()
  const { data: lists = [] } = useLists()
  const pinned = [...new Set(lists.flatMap(list => list.items.filter(item => item.pinned).map(item => item.symbol)))]
  const sidebarStocks = pinned.slice(0, 5).map(symbol => stocks.find(stock => stock.symbol === symbol) || { symbol, sources: [], total_posts: null, avg_sentiment: null, last_updated: null })
  const role = getAuthSession()?.role
  const pathname = usePathname()
  const mainRef = useMobileScrollRestoration()
  const activePage = pathname.startsWith('/lists') ? 'lists' : pathname.startsWith('/access') ? 'access' : pathname.startsWith('/account') ? 'account' : pathname.startsWith('/compare')
    ? 'compare'
    : pathname.startsWith('/screener')
      ? 'screener'
      : pathname.startsWith('/disclosures')
        ? 'disclosures'
      : pathname.startsWith('/trading')
        ? 'trading'
        : 'dashboard'
  const pageLabel = {
    dashboard: 'Overview',
    lists: 'Companies & lists', access: 'Workspace access', account: 'Your account',
    compare: 'Compare',
    screener: 'Screener',
    disclosures: 'Disclosures',
    trading: 'Paper & tests',
  }[activePage]
  return (
    <div className="app-shell flex min-h-dvh text-slate-100">
      <SideNav
        stocks={sidebarStocks}
        currentStock={company}
        activePage={activePage}
        watchlistLoading={isPending}
        watchlistError={isError}
        onWatchlistRetry={() => void refetch()}
      />
      <div className="shell-content min-w-0 flex-1">
        <header className="shell-topbar sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-white/[0.07] px-5 sm:px-8 lg:px-10">
          <div className="flex min-w-0 items-center gap-2 text-xs text-slate-400">
            <Link href="/" className="transition-colors hover:text-white">
              Research
            </Link>
            <ChevronRight className="h-3 w-3 shrink-0" />
            {company ? (
              <>
                <Link href="/" className="hover:text-white">
                  Companies
                </Link>
                <ChevronRight className="h-3 w-3 shrink-0" />
                <span className="font-medium text-slate-100">{company}</span>
              </>
            ) : (
              <span className="text-slate-100">{pageLabel}</span>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2.5 text-xs text-slate-400">
            <span className="hidden sm:inline">StockScope / Research desk</span>
            <span className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 capitalize text-slate-300">
              {role ?? 'Member'}
            </span>
          </div>
        </header>
        <main
          ref={mainRef}
          id="main-content"
          tabIndex={-1}
          className="shell-main mx-auto min-w-0 max-w-[1440px] px-4 py-6 sm:px-8 sm:py-9 lg:px-10"
        >
          <div>
            {!getAuthSession()?.user && role === 'admin' && <p className="mb-6 rounded-lg border border-[#b6c8ab]/20 p-4 text-sm text-[#b6c8ab]"><Link href="/account">Set up your individual owner account to enable private lists and invite friends →</Link></p>}
            {company && <div className="mb-5"><SaveCompany symbol={company} /></div>}
            {children}
            <footer className="mt-8 text-right">
              <a
                href="https://elbstream.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-base text-slate-400 underline-offset-4 hover:text-slate-200 hover:underline"
              >
                Logos provided by Elbstream
              </a>
            </footer>
          </div>
        </main>
      </div>
    </div>
  )
}

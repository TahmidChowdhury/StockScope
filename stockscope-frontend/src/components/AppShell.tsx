'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight, PanelTop } from 'lucide-react'
import SideNav from './SideNav'
import { useWatchlist } from '@/hooks/useWatchlist'
import { getAuthSession } from '@/lib/api'

export default function AppShell({
  children,
  company,
}: {
  children: ReactNode
  company?: string
}) {
  const { data: stocks = [], isPending, isError, refetch } = useWatchlist()
  const role = getAuthSession()?.role
  const pathname = usePathname()
  const activePage = pathname.startsWith('/compare')
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
    compare: 'Compare',
    screener: 'Screener',
    disclosures: 'Disclosures',
    trading: 'Paper & tests',
  }[activePage]
  return (
    <div className="app-shell flex min-h-dvh text-slate-100">
      <SideNav
        stocks={stocks}
        currentStock={company}
        activePage={activePage}
        watchlistLoading={isPending}
        watchlistError={isError}
        onWatchlistRetry={() => void refetch()}
      />
      <div className="min-w-0 flex-1">
        <header className="shell-topbar sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-white/[0.07] px-5 sm:px-8 lg:px-10">
          <div className="flex min-w-0 items-center gap-2 text-xs text-slate-400">
            <PanelTop className="mr-2 hidden h-4 w-4 sm:block" />
            <Link href="/" className="transition-colors hover:text-white">
              Workspace
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
            <span className="hidden sm:inline">Shared research workspace</span>
            <span className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 capitalize text-slate-300">
              {role ?? 'Member'}
            </span>
          </div>
        </header>
        <main
          id="main-content"
          tabIndex={-1}
          className="shell-main mx-auto min-w-0 max-w-[1440px] px-4 py-6 sm:px-8 sm:py-9 lg:px-10"
        >
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
        </main>
      </div>
    </div>
  )
}

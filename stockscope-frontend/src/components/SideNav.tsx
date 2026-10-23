'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import {
  ArrowUpRight,
  ChartNoAxesCombined,
  FlaskConical,
  LayoutDashboard,
  Landmark,
  LogOut,
  Menu,
  ScanLine,
  Scale,
  X,
} from 'lucide-react'
import { clearAuthSession } from '@/lib/api'
import CompanyLogo from './CompanyLogo'
import type { StockMetadata } from '@/types'

interface SideNavProps {
  stocks?: StockMetadata[]
  onLogout?: () => void
  onStockSelect?: (symbol: string) => void
  currentStock?: string
  activePage?: 'dashboard' | 'compare' | 'screener' | 'trading' | 'disclosures'
  watchlistLoading?: boolean
  watchlistError?: boolean
  onWatchlistRetry?: () => void
  hideMobileToggle?: boolean
}
const items = [
  { id: 'dashboard', href: '/', label: 'Overview', Icon: LayoutDashboard },
  { id: 'screener', href: '/screener', label: 'Screener', Icon: ScanLine },
  { id: 'compare', href: '/compare', label: 'Compare', Icon: Scale },
  { id: 'disclosures', href: '/disclosures', label: 'Disclosures', Icon: Landmark },
  {
    id: 'trading',
    href: '/trading',
    label: 'Paper & tests',
    Icon: FlaskConical,
  },
] as const

export default function SideNav({
  stocks = [],
  onLogout = clearAuthSession,
  onStockSelect,
  currentStock,
  activePage = 'dashboard',
  watchlistLoading = false,
  watchlistError = false,
  onWatchlistRetry,
}: SideNavProps) {
  const [open, setOpen] = useState(false)
  const logo = (
    <Link
      href="/"
      className="flex items-center gap-3 px-6 py-7"
      onClick={() => setOpen(false)}
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-500 text-white shadow-lg shadow-violet-500/15">
        <ChartNoAxesCombined className="h-5 w-5" />
      </span>
      <span className="text-lg font-semibold tracking-tight text-white">
        StockScope
        <span className="mt-0.5 block whitespace-nowrap text-[9px] font-medium uppercase tracking-[0.14em] text-slate-500">
          Research workspace
        </span>
      </span>
    </Link>
  )
  const links = (
    <nav aria-label="Main navigation" className="space-y-1 px-3">
      {items.map(({ id, href, label, Icon }) => (
        <Link
          key={id}
          href={href}
          aria-current={activePage === id ? 'page' : undefined}
          onClick={() => setOpen(false)}
          className={`flex items-center gap-3 rounded-lg px-3 py-3 text-sm transition-colors ${activePage === id ? 'bg-violet-400/10 font-medium text-violet-200' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
        >
          <Icon className="h-[18px] w-[18px]" />
          {label}
          {activePage === id && (
            <span className="ml-auto h-1.5 w-1.5 rounded-full bg-violet-400" />
          )}
        </Link>
      ))}
    </nav>
  )
  const watchlist = (
    <div className="mt-8 px-3">
      <div className="mb-3 flex items-center justify-between px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
        <span>Watchlist</span>
        <span>{stocks.length}</span>
      </div>
      {watchlistError && (
        <div
          role="status"
          className="mb-3 px-3 text-xs leading-5 text-amber-200"
        >
          <p>Watchlist update unavailable.</p>
          {onWatchlistRetry && (
            <button
              onClick={onWatchlistRetry}
              className="underline underline-offset-4"
            >
              Retry
            </button>
          )}
        </div>
      )}
      {watchlistLoading ? (
        <p role="status" className="px-3 text-xs text-slate-500">
          Loading saved companies…
        </p>
      ) : stocks.length ? (
        <div className="max-h-72 space-y-1 overflow-y-auto">
          {stocks.slice(0, 12).map((stock) => (
            <Link
              key={stock.symbol}
              href={`/stock/${encodeURIComponent(stock.symbol)}`}
              onClick={(e) => {
                if (onStockSelect) {
                  e.preventDefault()
                  onStockSelect(stock.symbol)
                }
                setOpen(false)
              }}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-white/5 ${currentStock === stock.symbol ? 'bg-white/5 text-white' : 'text-slate-400'}`}
            >
              <CompanyLogo symbol={stock.symbol} size="small" />
              <span className="font-medium">{stock.symbol}</span>
              <ArrowUpRight className="ml-auto h-3 w-3 text-slate-600" />
            </Link>
          ))}
        </div>
      ) : (
        !watchlistError && (
          <p className="px-3 text-xs leading-5 text-slate-500">
            Your saved companies will appear here.
          </p>
        )
      )}
      {stocks.length > 12 && (
        <Link
          href="/#watchlist"
          onClick={() => setOpen(false)}
          className="mt-3 block px-3 text-xs text-violet-300"
        >
          View all {stocks.length} companies →
        </Link>
      )}
    </div>
  )
  const footer = (
    <div className="mt-auto px-4 pb-5 pt-8">
      <div className="mb-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
        <p className="text-xs font-medium text-slate-300">
          Built for a closer look.
        </p>
        <p className="mt-1 text-[11px] leading-5 text-slate-500">
          Fundamentals. Sources. Perspective.
        </p>
      </div>
      <button
        onClick={onLogout}
        className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-xs text-slate-400 hover:bg-white/5 hover:text-white"
      >
        <LogOut className="h-4 w-4" />
        Sign out
      </button>
    </div>
  )
  return (
    <>
      <a
        href="#main-content"
        className="sr-only z-[100] rounded bg-violet-600 p-3 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to content
      </a>
      <aside className="shell-sidebar sticky top-0 hidden h-dvh w-60 shrink-0 flex-col overflow-y-auto border-r border-white/[0.07] lg:flex">
        {logo}
        {links}
        {watchlist}
        {footer}
      </aside>
      <nav
        aria-label="Mobile navigation"
        className="shell-mobile-nav fixed inset-x-0 bottom-0 z-40 flex border-t border-white/10 bg-[#101218]/95 backdrop-blur-xl lg:hidden"
      >
        {items.map(({ id, href, label, Icon }) => (
          <Link
            key={id}
            href={href}
            aria-current={activePage === id ? 'page' : undefined}
            className={`flex min-h-16 flex-1 flex-col items-center justify-center gap-1 text-[10px] ${activePage === id ? 'text-violet-300' : 'text-slate-400'}`}
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        ))}
        <button
          aria-label="Open workspace menu"
          onClick={() => setOpen(true)}
          className="flex min-h-16 flex-1 flex-col items-center justify-center gap-1 text-[10px] text-slate-400"
        >
          <Menu className="h-5 w-5" />
          Menu
        </button>
      </nav>
      <Dialog open={open} onClose={setOpen} className="relative z-50 lg:hidden">
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" />
        <DialogPanel className="shell-sidebar fixed inset-y-0 left-0 flex w-72 max-w-[90vw] flex-col overflow-y-auto">
          <DialogTitle className="sr-only">Workspace menu</DialogTitle>
          <button
            aria-label="Close workspace menu"
            onClick={() => setOpen(false)}
            className="absolute right-2 top-2 rounded-lg p-2 text-slate-400"
          >
            <X className="h-4 w-4" />
          </button>
          {logo}
          {links}
          {watchlist}
          {footer}
        </DialogPanel>
      </Dialog>
    </>
  )
}

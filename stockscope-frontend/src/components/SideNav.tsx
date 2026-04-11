'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  HomeIcon,
  ScaleIcon,
  FunnelIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  ChartBarSquareIcon,
} from '@heroicons/react/24/outline'
import type { StockMetadata } from '@/types'

interface SideNavProps {
  stocks?: StockMetadata[]
  onLogout?: () => void
  onStockSelect?: (symbol: string) => void
  currentStock?: string
  activePage?: 'dashboard' | 'compare' | 'screener'
  /** Kept for backward compat — no longer used */
  hideMobileToggle?: boolean
}

const NAV_ITEMS = [
  { id: 'dashboard', href: '/', label: 'Dashboard', Icon: HomeIcon },
  { id: 'compare',   href: '/compare',  label: 'Compare',   Icon: ScaleIcon },
  { id: 'screener',  href: '/screener', label: 'Screener',  Icon: FunnelIcon },
] as const

export default function SideNav({
  stocks = [],
  onLogout,
  onStockSelect,
  currentStock,
  activePage = 'dashboard',
}: SideNavProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)

  const NavLinks = () => (
    <nav className="px-3 py-4 space-y-0.5">
      <div className="text-xs font-semibold text-white/25 uppercase tracking-widest mb-3 px-3">
        Navigation
      </div>
      {NAV_ITEMS.map(item => (
        <Link
          key={item.id}
          href={item.href}
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-medium ${
            activePage === item.id
              ? 'bg-purple-600/25 text-white border border-purple-500/25'
              : 'text-white/55 hover:text-white hover:bg-white/8'
          }`}
          onClick={() => setDrawerOpen(false)}
        >
          <item.Icon className="w-4 h-4 flex-shrink-0" />
          <span>{item.label}</span>
        </Link>
      ))}
    </nav>
  )

  const PortfolioList = () => {
    if (stocks.length === 0) return null
    return (
      <div className="px-3 pb-3">
        <div className="h-px bg-white/10 mb-3" />
        <div className="text-xs font-semibold text-white/25 uppercase tracking-widest mb-2 px-3">
          Portfolio
        </div>
        <div className="space-y-0.5 max-h-48 overflow-y-auto">
          {stocks.slice(0, 10).map(stock => (
            <button
              key={stock.symbol}
              onClick={() => { onStockSelect?.(stock.symbol); setDrawerOpen(false) }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all ${
                currentStock === stock.symbol
                  ? 'bg-purple-600/20 text-white'
                  : 'text-white/55 hover:text-white hover:bg-white/8'
              }`}
            >
              <span className="font-mono font-semibold tracking-wide">{stock.symbol}</span>
              <span className={`text-xs ${
                (stock.avg_sentiment ?? 0) > 0.1  ? 'text-green-400' :
                (stock.avg_sentiment ?? 0) < -0.1 ? 'text-red-400'   : 'text-white/25'
              }`}>
                {(stock.avg_sentiment ?? 0) > 0.1  ? '▲' :
                 (stock.avg_sentiment ?? 0) < -0.1 ? '▼' : '—'}
              </span>
            </button>
          ))}
        </div>
      </div>
    )
  }

  const LogoutBtn = () => {
    if (!onLogout) return null
    return (
      <div className="px-3 pb-4 mt-auto">
        <div className="h-px bg-white/10 mb-3" />
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-red-400/70 hover:text-red-300 hover:bg-red-500/10 transition-all text-sm"
        >
          <ArrowRightOnRectangleIcon className="w-4 h-4 flex-shrink-0" />
          <span>Logout</span>
        </button>
      </div>
    )
  }

  const Logo = () => (
    <div className="flex items-center gap-3 px-4 py-5 flex-shrink-0">
      <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0 shadow-md">
        <ChartBarSquareIcon className="w-5 h-5 text-white" />
      </div>
      <div>
        <div className="font-bold text-white text-[15px] leading-tight">StockScope</div>
        <div className="text-[10px] text-white/35 font-medium tracking-wider uppercase">Pro</div>
      </div>
    </div>
  )

  return (
    <>
      {/* ── Desktop sidebar ───────────────────────── */}
      <aside className="hidden lg:flex flex-col w-56 bg-slate-900/60 border-r border-white/10 flex-shrink-0 sticky top-0 h-screen overflow-y-auto">
        <Logo />
        <div className="h-px bg-white/10 mx-4 flex-shrink-0" />
        <NavLinks />
        <PortfolioList />
        <LogoutBtn />
      </aside>

      {/* ── Mobile: bottom tab bar + slide drawer ── */}
      <div className="lg:hidden">
        {/* Fixed bottom tab bar */}
        <nav className="fixed bottom-0 inset-x-0 z-50 bg-slate-900/95 backdrop-blur-sm border-t border-white/10 flex items-stretch h-16">
          {NAV_ITEMS.map(item => (
            <Link
              key={item.id}
              href={item.href}
              className={`flex-1 flex flex-col items-center justify-center gap-1 transition-colors ${
                activePage === item.id
                  ? 'text-purple-400'
                  : 'text-white/45 hover:text-white active:text-white'
              }`}
            >
              <item.Icon className="h-5 w-5" />
              <span className="text-[10px] font-medium">{item.label}</span>
            </Link>
          ))}
          {/* Menu tab — opens drawer for portfolio + logout */}
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex-1 flex flex-col items-center justify-center gap-1 text-white/45 hover:text-white active:text-white transition-colors"
            aria-label="Open menu"
          >
            <Bars3Icon className="h-5 w-5" />
            <span className="text-[10px] font-medium">Menu</span>
          </button>
        </nav>

        {/* Backdrop */}
        {drawerOpen && (
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            onClick={() => setDrawerOpen(false)}
          />
        )}

        {/* Drawer (portfolio list + logout) */}
        <div className={`fixed inset-y-0 left-0 w-64 bg-slate-900 border-r border-white/10 z-50 flex flex-col overflow-y-auto transition-transform duration-250 ease-out ${
          drawerOpen ? 'translate-x-0' : '-translate-x-full'
        }`}>
          <div className="flex items-center justify-between pr-3 border-b border-white/10">
            <Logo />
            <button
              onClick={() => setDrawerOpen(false)}
              className="p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Close menu"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>
          <NavLinks />
          <PortfolioList />
          <LogoutBtn />
        </div>
      </div>
    </>
  )
}

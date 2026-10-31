'use client'

import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { useRouter } from 'next/navigation'
import AnimatedAction from './ui/AnimatedAction'
import Link from 'next/link'
import * as Dialog from '@animate-ui/react/primitives/radix-ui/dialog'
import {
  ArrowUpRight,
  FlaskConical,
  FolderOpen,
  LayoutDashboard,
  Landmark,
  LogOut,
  Menu,
  ScanLine,
  Scale,
  X,
} from 'lucide-react'
import { clearAuthSession, apiFetch, getAuthSession } from '@/lib/api'
import CompanyLogo from './CompanyLogo'
import type { StockMetadata } from '@/types'

interface SideNavProps {
  stocks?: StockMetadata[]
  onLogout?: () => void
  onStockSelect?: (symbol: string) => void
  currentStock?: string
  activePage?: 'dashboard' | 'compare' | 'screener' | 'trading' | 'disclosures' | 'lists' | 'access' | 'account'
  watchlistLoading?: boolean
  watchlistError?: boolean
  onWatchlistRetry?: () => void
  hideMobileToggle?: boolean
}
const items = [
  { id: 'dashboard', href: '/', label: 'Overview', Icon: LayoutDashboard },
  { id: 'lists', href: '/lists', label: 'Companies & lists', Icon: FolderOpen },
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

// Keep primary destinations comfortably tappable; the menu contains every page.
const mobileItems = items.filter((item) => ['dashboard', 'lists', 'screener', 'compare'].includes(item.id))

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
  const router = useRouter()
  const navigationTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => () => { if (navigationTimer.current) clearTimeout(navigationTimer.current) }, [])
  const navigate = (event: MouseEvent<HTMLAnchorElement>, href: string) => {
    if (!open || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
    event.preventDefault()
    if (navigationTimer.current) return
    setOpen(false)
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    // Let the sheet finish closing before a route change unmounts this shell.
    navigationTimer.current = setTimeout(() => {
      navigationTimer.current = null
      router.push(href)
    }, reduced ? 0 : 220)
  }
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 1024px)')
    const closeOnDesktop = () => {
      if (desktop.matches) setOpen(false)
    }
    desktop.addEventListener('change', closeOnDesktop)
    return () => desktop.removeEventListener('change', closeOnDesktop)
  }, [])
  const logo = (
    <Link href="/" className="scope-brand" onClick={event => navigate(event, '/')}>
      <span className="scope-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32" fill="none"><path d="M4 13V4h9M19 4h9v9M28 19v9h-9M13 28H4v-9" stroke="currentColor" strokeWidth="1.5" /><path d="M10 21V16M16 21V10M22 21V13" stroke="currentColor" strokeWidth="2" /></svg>
      </span>
      <span><span className="scope-wordmark">StockScope<span className="text-[#b6c8ab]">.</span></span><span className="scope-caption">Company research</span></span>
    </Link>
  )
  const links = (
    <nav aria-label="Main navigation" className="scope-navigation">
      <p className="scope-section-label">Research desk</p>
      {items.map(({ id, href, label, Icon }, index) => (
        <Link
          key={id}
          href={href}
          aria-current={!currentStock && activePage === id ? 'page' : undefined}
          onClick={event => navigate(event, href)}
          className="scope-nav-link"
        >
          <span className="scope-nav-number" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
          <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{label}</span>
          <ArrowUpRight className="scope-nav-arrow ml-auto h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      ))}
      <Link href="/account" onClick={event => navigate(event, '/account')} className="scope-nav-link" aria-current={activePage === 'account' ? 'page' : undefined}>Your account</Link>
      {getAuthSession()?.role === 'admin' && <Link href="/access" onClick={event => navigate(event, '/access')} className="scope-nav-link" aria-current={activePage === 'access' ? 'page' : undefined}>Access & resources</Link>}
    </nav>
  )
  const watchlist = (
    <div className="scope-watchlist">
      <div className="scope-section-label flex items-center justify-between">
        <span>Pinned companies</span>
        <span className="font-mono">{watchlistLoading || watchlistError ? '—' : String(stocks.length).padStart(2, '0')}</span>
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
        <div className="space-y-1 lg:max-h-72 lg:overflow-y-auto">
          {stocks.slice(0, 5).map((stock) => (
            <Link
              key={stock.symbol}
              href={`/stock/${encodeURIComponent(stock.symbol)}`}
              onClick={(e) => {
                if (onStockSelect) {
                  e.preventDefault()
                  onStockSelect(stock.symbol)
                }
                if (onStockSelect) setOpen(false)
                else navigate(e, `/stock/${encodeURIComponent(stock.symbol)}`)
              }}
              aria-current={currentStock === stock.symbol ? 'page' : undefined}
              className={`flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm hover:bg-white/5 ${currentStock === stock.symbol ? 'bg-white/5 text-white' : 'text-slate-400'}`}
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
            Pin companies in your personal lists to keep them close.
          </p>
        )
      )}
      {stocks.length > 5 && (
        <Link
          href="/lists"
          onClick={event => navigate(event, '/lists')}
          className="mt-3 block px-3 py-2 text-xs text-[#b6c8ab]"
        >
          View all {stocks.length} companies →
        </Link>
      )}
    </div>
  )
  const footer = (
    <div className="scope-nav-footer">
      <div className="flex items-center justify-between gap-2">
        <div><p className="text-xs text-slate-300">Private workspace</p><p className="mt-1 text-[10px] text-slate-500">Saved research & evidence</p></div>
        <AnimatedAction onClick={() => { if (getAuthSession()?.user) void apiFetch('/api/auth/sign-out', { method: 'POST' }).catch(() => {}).finally(onLogout); else onLogout() }} aria-label="Sign out" className="flex h-11 w-11 items-center justify-center rounded-md text-slate-400 hover:bg-white/5 hover:text-white"><LogOut className="h-4 w-4" /></AnimatedAction>
      </div>
    </div>
  )
  return (
    <Dialog.Root open={open} onOpenChange={next => {
      if (next && navigationTimer.current) {
        clearTimeout(navigationTimer.current)
        navigationTimer.current = null
      }
      setOpen(next)
    }}>
      <a
        href="#main-content"
        className="sr-only z-[100] rounded bg-violet-600 p-3 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to content
      </a>
      <aside className="shell-sidebar sticky top-0 hidden h-dvh w-64 shrink-0 flex-col overflow-y-auto border-r border-white/[0.07] lg:flex">
        {logo}
        {links}
        {watchlist}
        {footer}
      </aside>
      <nav
        aria-label="Mobile navigation"
        className="shell-mobile-nav relative z-40 grid grid-cols-5 border-t border-white/10 bg-[#101218] lg:hidden"
      >
        {mobileItems.map(({ id, href, label, Icon }) => (
          <Link
            key={id}
            href={href}
            prefetch={false}
            aria-label={label}
            aria-current={!currentStock && activePage === id ? 'page' : undefined}
            className={`flex min-h-16 min-w-0 flex-col items-center justify-center gap-1 px-1 text-[11px] ${!currentStock && activePage === id ? 'scope-mobile-active font-medium text-[#dbe6d4]' : 'text-slate-400'}`}
          >
            <Icon className="h-5 w-5" />
            {id === 'dashboard' ? 'Home' : id === 'lists' ? 'Lists' : id === 'screener' ? 'Discover' : label}
          </Link>
        ))}
        <Dialog.Trigger asChild>
        <AnimatedAction
          aria-label="Open workspace menu"
          aria-expanded={open}
          aria-haspopup="dialog"
          className={`flex min-h-16 min-w-0 flex-col items-center justify-center gap-1 px-1 text-[11px] ${activePage === 'disclosures' || open ? 'scope-mobile-active font-medium text-[#dbe6d4]' : 'text-slate-400'}`}
        >
          <Menu className="h-5 w-5" />
          {activePage === 'disclosures' ? 'Disclosures' : 'Menu'}
        </AnimatedAction>
        </Dialog.Trigger>
      </nav>
      <Dialog.Portal>
        <Dialog.Overlay transition={{ duration: 0.3 }} exitTransition={{ duration: 0.22 }} className="fixed inset-0 z-50 bg-black/60 lg:hidden" />
        <Dialog.Content data-side="left" transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }} exitTransition={{ duration: 0.2, ease: [0.4, 0, 1, 1] }} className="shell-sidebar shell-drawer fixed left-0 top-0 z-50 flex h-dvh w-[340px] max-w-[88vw] flex-col overflow-y-auto overscroll-contain border-r border-white/10 shadow-2xl outline-none lg:hidden">
          <Dialog.Title className="sr-only">Workspace menu</Dialog.Title>
          <Dialog.Description className="sr-only">Navigate research tools and saved companies.</Dialog.Description>
          <Dialog.Close asChild>
            <AnimatedAction aria-label="Close workspace menu" className="shell-drawer-close absolute right-2 flex h-11 w-11 items-center justify-center rounded-md text-slate-400 hover:bg-white/5"><X className="h-4 w-4" /></AnimatedAction>
          </Dialog.Close>
          {logo}
          {links}
          {watchlist}
          {footer}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

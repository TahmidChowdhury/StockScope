'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Building2,
  ScanLine,
  Scale,
} from 'lucide-react'
import AppShell from '@/components/AppShell'
import StockSearch from '@/components/StockSearch'
import Watchlist from '@/components/Watchlist'
import SpotlightCard from '@/components/ui/SpotlightCard'
import AnimatedAction from '@/components/ui/AnimatedAction'
import { useWatchlist } from '@/hooks/useWatchlist'
import { useAnalysisProgress } from '@/hooks/useAnalysisProgress'
import { apiFetch } from '@/lib/api'

export default function Home() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { data: stocks = [], isPending: watchlistPending } = useWatchlist()
  const [symbol, setSymbol] = useState('')
  const [starting, setStarting] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [notice, setNotice] = useState('')
  const { progress, message } = useAnalysisProgress({
    symbol,
    isAnalyzing: analyzing,
    onComplete: (result) => {
      setAnalyzing(false)
      void queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      const destination = `/stock/${encodeURIComponent(symbol)}`
      router.push(
        result.status === 'partial'
          ? `${destination}?collection=partial`
          : destination,
      )
    },
    onError: (error) => {
      setAnalyzing(false)
      setNotice(error)
    },
  })
  const openCompany = async (ticker: string) => {
    if (starting || analyzing) return
    setStarting(true)
    setNotice('')
    setSymbol(ticker)
    try {
      const existing = await apiFetch(
        `/api/stocks/${encodeURIComponent(ticker)}`,
      )
      if (existing.ok) {
        router.push(`/stock/${encodeURIComponent(ticker)}`)
        return
      }
      if (existing.status !== 404)
        throw new Error(
          'Saved research could not be checked. Please try again.',
        )
      const response = await apiFetch('/api/stocks/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: ticker,
          sources: ['news', 'sec_facts'],
        }),
      })
      if (!response.ok)
        throw new Error('Research could not be started. Please try again.')
      setAnalyzing(true)
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : 'Research could not be loaded.',
      )
    } finally {
      setStarting(false)
    }
  }
  return (
    <AppShell>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow mb-2">Your research, in focus</p>
          <h1 className="page-title">Workspace overview</h1>
          <p className="mt-2 text-sm text-slate-400">
            A clearer view of the companies you follow.
          </p>
        </div>
        <span className="text-xs text-slate-500">
          Shared watchlist · Saved research
        </span>
      </div>
      <section className="research-hero relative mb-6 rounded-2xl border border-white/10 p-4 sm:p-8">
        <div className="relative z-10 max-w-2xl">
          <span className="mb-4 hidden items-center gap-2 rounded-full border border-violet-400/20 bg-violet-400/[0.08] px-3 py-1 text-[11px] font-medium text-violet-200 sm:inline-flex">
            <span className="h-1 w-1 rounded-full bg-violet-300" />
            The company comes first
          </span>
          <h2 className="mb-3 text-base font-medium tracking-tight text-white sm:mb-0 sm:text-3xl">
            <span className="sm:hidden">Find a company</span>
            <span className="hidden sm:inline">
              Start with a question.
              <br />
              <span className="text-slate-400">Get closer to the evidence.</span>
            </span>
          </h2>
          <p className="mb-6 mt-3 hidden max-w-lg text-sm leading-6 text-slate-400 sm:block">
            Explore financials, read the news, and trace the numbers back to
            their sources.
          </p>
          <StockSearch
            onAnalyze={openCompany}
            isLoading={starting || analyzing}
          />
        </div>
      </section>
      {(analyzing || starting || notice) && (
        <div role="status" aria-live="polite" className="surface mb-6 p-4">
          <div className="flex items-center justify-between gap-4 text-sm">
            <span className={notice ? 'text-amber-200' : 'text-slate-300'}>
              {notice ||
                (starting
                  ? `Opening research for ${symbol}…`
                  : `${symbol} · ${message || 'Collecting research…'}`)}
            </span>
            {analyzing && (
              <span className="text-xs tabular-nums text-violet-300">
                {Math.round(progress)}%
              </span>
            )}
          </div>
          {analyzing && (
            <div
              role="progressbar"
              aria-label="Research collection"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(progress)}
              className="mt-3 h-1 overflow-hidden rounded-full bg-white/10"
            >
              <div
                className="h-full rounded-full bg-violet-400 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>
      )}
      <div className="mb-9 grid grid-cols-3 gap-2 sm:gap-3">
        {[
          {
            label: 'Companies followed',
            value: stocks.length,
            detail: 'In the shared watchlist',
            Icon: Building2,
          },
          {
            label: 'Saved evidence',
            value: stocks.some((stock) => stock.total_posts == null)
              ? '—'
              : stocks
                  .reduce((sum, stock) => sum + (stock.total_posts ?? 0), 0)
                  .toLocaleString(),
            detail: 'News and filing records',
            Icon: BookOpen,
          },
          {
            label: 'Sources',
            value: new Set(stocks.flatMap((stock) => stock.sources)).size,
            detail: 'Across saved research',
            Icon: ScanLine,
          },
        ].map(({ label, value, detail, Icon }) => (
          <div
            key={label}
            className="surface flex items-start gap-4 p-3 sm:p-5"
          >
            <span className="hidden rounded-lg border border-white/[0.06] bg-white/[0.03] p-2.5 text-slate-400 lg:block">
              <Icon className="h-4 w-4" />
            </span>
            <div>
              <p className="text-[10px] text-slate-400 sm:text-xs">{label}</p>
              <p className="mt-1.5 text-xl font-semibold tracking-tight tabular-nums text-white">
                {watchlistPending ? '—' : value}
              </p>
              <p className="mt-1 hidden text-[11px] text-slate-500 sm:block">
                {detail}
              </p>
            </div>
          </div>
        ))}
      </div>
      <Watchlist />
      <div className="mt-9 grid gap-4 md:grid-cols-2">
        {[
          {
            href: '/screener',
            title: 'Find a company worth studying',
            description:
              'Filter the curated universe by growth, margins, and balance sheet strength.',
            Icon: ScanLine,
            action: 'Open screener',
          },
          {
            href: '/compare',
            title: 'Put the numbers in perspective',
            description:
              'Compare company fundamentals side by side to see what stands out.',
            Icon: Scale,
            action: 'Compare companies',
          },
        ].map(({ href, title, description, Icon, action }) => (
          <SpotlightCard key={href} className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <Icon className="h-5 w-5 text-violet-300" />
              <ArrowUpRight className="h-4 w-4 text-slate-500 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
            </div>
            <h3 className="text-sm font-medium text-slate-100">{title}</h3>
            <p className="mt-2 max-w-md text-xs leading-6 text-slate-400">
              {description}
            </p>
            <AnimatedAction asChild className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg border border-violet-400/20 bg-violet-400/[0.08] px-3 text-xs font-medium text-violet-200 hover:bg-violet-400/[0.14]">
              <Link href={href}>
                {action}
                <ArrowRight aria-hidden="true" className="h-3 w-3" />
              </Link>
            </AnimatedAction>
          </SpotlightCard>
        ))}
      </div>
      <p className="mt-8 text-center text-[11px] leading-5 text-slate-500">
        Research has a timestamp. Check source dates and coverage before drawing
        conclusions.
      </p>
    </AppShell>
  )
}

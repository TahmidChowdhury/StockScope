'use client'

import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import {
  ArrowLeft,
  ArrowUpRight,
  ChartNoAxesCombined,
  FileText,
  Newspaper,
} from 'lucide-react'
import PriceChart from './PriceChart'
import NewsComponent from './NewsComponent'
import KeyMetrics from './KeyMetrics'
import StockDashboard from './StockDashboard'
import SecFactsPanel from './SecFactsPanel'
import SentimentLabPanel from './SentimentLabPanel'
import ValuationPanel from './ValuationPanel'
import CompanyLogo from './CompanyLogo'
import type { StockMetadata } from '@/types'
import { researchReturn } from '@/lib/research-workflow'

interface StockAnalysisHubProps {
  symbol: string
  onBack: () => void
  onStockSelect?: (symbol: string) => void
  stocks?: StockMetadata[]
}

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'news', label: 'News' },
  { id: 'tone', label: 'Tone lab' },
  { id: 'sources', label: 'SEC evidence' },
  { id: 'analysis', label: 'Research summary' },
] as const

export default function StockAnalysisHub({
  symbol,
  onBack,
  stocks = [],
}: StockAnalysisHubProps) {
  const search = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const active = tabs.some((tab) => tab.id === search.get('tab'))
    ? search.get('tab')
    : 'overview'
  const company = stocks.find((stock) => stock.symbol === symbol)
  const returnDestination = researchReturn(search.get('returnTo'))
  const selectTab = (tab: string) => {
    const params = new URLSearchParams(search.toString())
    if (tab === 'overview') params.delete('tab')
    else params.set('tab', tab)
    router.push(`${pathname}${params.size ? `?${params}` : ''}`, {
      scroll: false,
    })
  }
  return (
    <>
      <button
        onClick={onBack}
        className="mb-6 inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        {returnDestination?.label || 'Back to overview'}
      </button>
      <div className="mb-7 flex flex-wrap items-center justify-between gap-5">
        <div className="flex min-w-0 items-center gap-4">
          <CompanyLogo symbol={symbol} size="large" />
          <div className="min-w-0">
            <p className="eyebrow mb-1">Company research</p>
            <h1 className="page-title break-words">
              {company?.companyName || symbol}
            </h1>
            <p className="mt-1 text-xs font-medium text-slate-400">
              {symbol}
              <span className="mx-2 text-slate-600">/</span>Financials, context,
              and original sources
            </p>
          </div>
        </div>
        <Link
          href={`/fundamentals/${encodeURIComponent(symbol)}${returnDestination ? `?${new URLSearchParams({ returnTo: returnDestination.href })}` : ''}`}
          className="button-primary"
        >
          Explore financials
          <ArrowUpRight className="h-4 w-4" />
        </Link>
      </div>
      {search.get('collection') === 'partial' && (
        <p
          role="status"
          className="surface mb-5 border-amber-400/20 p-4 text-sm text-amber-200"
        >
          Research collection completed with partial results. Some sources were
          unavailable. Review the research summary for collection details.
        </p>
      )}
      <nav
        aria-label="Company research sections"
        className="mb-7 flex gap-6 overflow-x-auto border-b border-white/10"
      >
        {tabs.map((tab) => (
          <Link
            key={tab.id}
            href={`${pathname}?${new URLSearchParams({ ...Object.fromEntries(search), tab: tab.id })}`}
            aria-current={active === tab.id ? 'page' : undefined}
            onClick={(e) => {
              e.preventDefault()
              selectTab(tab.id)
            }}
            className={`whitespace-nowrap border-b-2 pb-3.5 text-sm transition-colors ${active === tab.id ? 'border-violet-400 font-medium text-violet-200' : 'border-transparent text-slate-500 hover:text-slate-200'}`}
          >
            {tab.label}
          </Link>
        ))}
      </nav>
      <div key={`${symbol}-${active}`} className="animate-fadeIn">
        {active === 'overview' && (
          <>
            <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
              <div className="min-w-0 space-y-5">
                <PriceChart symbol={symbol} className="company-panel" />
                <div className="grid gap-3 sm:grid-cols-2">
                  {[
                    {
                      tab: 'news',
                      Icon: Newspaper,
                      title: 'The story around the numbers',
                      text: 'Read dated articles and company releases.',
                    },
                    {
                      tab: 'sources',
                      Icon: FileText,
                      title: 'Go straight to the source',
                      text: 'Inspect SEC facts and original filings.',
                    },
                  ].map(({ tab, Icon, title, text }) => (
                    <button
                      key={tab}
                      onClick={() => selectTab(tab)}
                      className="surface group p-5 text-left transition-colors hover:border-violet-400/30"
                    >
                      <div className="mb-3 flex items-center justify-between">
                        <Icon className="h-4 w-4 text-violet-300" />
                        <ArrowUpRight className="h-4 w-4 text-slate-500" />
                      </div>
                      <h2 className="text-sm font-medium text-slate-200">
                        {title}
                      </h2>
                      <p className="mt-2 text-xs leading-5 text-slate-500">
                        {text}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
              <KeyMetrics symbol={symbol} />
            </div>
            <div className="mt-5">
              <ValuationPanel symbol={symbol} />
            </div>
            <div className="surface mt-5 flex items-start gap-3 px-5 py-4">
              <ChartNoAxesCombined className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
              <p className="text-xs leading-6 text-slate-400">
                Price history shows market context. Financial statements and
                original filings provide the business context. Provider
                observations can be delayed; check each panel’s source date.
              </p>
            </div>
          </>
        )}
        {active === 'news' && (
          <NewsComponent symbol={symbol} className="company-panel" />
        )}
        {active === 'tone' && <SentimentLabPanel symbol={symbol} />}
        {active === 'sources' && (
          <div className="surface p-4 sm:p-6">
            <SecFactsPanel symbol={symbol} />
          </div>
        )}
        {active === 'analysis' && (
          <StockDashboard symbol={symbol} onBack={onBack} embedded />
        )}
      </div>
    </>
  )
}

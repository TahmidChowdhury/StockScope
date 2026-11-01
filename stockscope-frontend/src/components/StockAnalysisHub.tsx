'use client'

import Link from 'next/link'
import dynamic from 'next/dynamic'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { skipToken, useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  ArrowUpRight,
} from 'lucide-react'
import PriceChart from './PriceChart'
import KeyMetrics from './KeyMetrics'
import DeferredPanel from './DeferredPanel'
import CompanyDisclosures from './CompanyDisclosures'
import { LoadingRows, SentimentLoading } from './ResearchLoading'
import CompanyLogo from './CompanyLogo'
import type { StockMetadata } from '@/types'
import { companyFundamentalsHref, researchReturn } from '@/lib/research-workflow'

function SectionLoading() {
  return <div className="surface p-6"><LoadingRows label="Loading research section…" /></div>
}

const NewsComponent = dynamic(() => import('./NewsComponent'), { loading: SectionLoading })
const StockDashboard = dynamic(() => import('./StockDashboard'), { loading: SectionLoading })
const SecFactsPanel = dynamic(() => import('./SecFactsPanel'), { loading: SectionLoading })
const SentimentLabPanel = dynamic(() => import('./SentimentLabPanel'), { loading: SentimentLoading })

interface StockAnalysisHubProps {
  symbol: string
  onBack: () => void
  onStockSelect?: (symbol: string) => void
  stocks?: StockMetadata[]
}

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'news', label: 'News' },
  { id: 'tone', label: 'Sentiment' },
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
  // Observe the metrics panel's cached response without issuing another request.
  const { data: companyInfo } = useQuery<{ displayName?: string }>({
    queryKey: ['company-info', symbol],
    queryFn: skipToken,
  })
  const companyName = company?.companyName && company.companyName !== symbol
    ? company.companyName
    : typeof companyInfo?.displayName === 'string' && companyInfo.displayName.trim()
      ? companyInfo.displayName
      : symbol
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
      {returnDestination && <button
        onClick={onBack}
        className="mb-6 inline-flex items-center gap-2 text-xs text-slate-400 hover:text-white"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        {returnDestination.label}
      </button>}
      <div className="mb-7 flex flex-wrap items-center justify-between gap-5">
        <div className="flex min-w-0 items-center gap-4">
          <CompanyLogo symbol={symbol} size="large" />
          <div className="min-w-0">
            <h1 className="page-title break-words">
              {companyName}
            </h1>
            {companyName !== symbol && <p className="mt-1 text-xs font-medium text-slate-400">
              {symbol}
            </p>}
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href={companyFundamentalsHref(symbol, returnDestination?.href || '')}
            className="button-secondary"
          >
            Financials &amp; valuation
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
      {search.get('collection') === 'partial' && (
        <p
          role="status"
          className="surface mb-5 border-amber-400/20 p-4 text-sm text-amber-200"
        >
          Some sources could not be refreshed. Open the research summary to see which sources responded.
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
            className={`whitespace-nowrap border-b-2 pb-3.5 text-sm transition-colors ${active === tab.id ? 'border-sage-300 font-medium text-[#dce6d7]' : 'border-transparent text-slate-500 hover:text-slate-200'}`}
          >
            {tab.label}
          </Link>
        ))}
      </nav>
      <div key={`${symbol}-${active}`} className="animate-fadeIn">
        {active === 'overview' && (
          <>
            <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
              <div className="min-w-0">
                <PriceChart symbol={symbol} className="company-panel" />
              </div>
              <KeyMetrics symbol={symbol} />
            </div>
            <div className="mt-5">
              <DeferredPanel label="company disclosures">
                {enabled => <CompanyDisclosures symbol={symbol} enabled={enabled} />}
              </DeferredPanel>
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

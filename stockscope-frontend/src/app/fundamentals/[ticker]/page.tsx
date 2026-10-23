'use client'

import { useFundamentals } from '@/hooks/useFundamentals'
import { useParams, useSearchParams } from 'next/navigation'
import { companyComparisonHref, companyResearchHref, researchReturn } from '@/lib/research-workflow'
import { Scale } from 'lucide-react'
import { amount } from '@/lib/financial-format'
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ArrowLeftIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  BanknotesIcon,
} from '@heroicons/react/24/outline'
import { FundamentalPoint, FundamentalsSeries } from '@/types'
import Link from 'next/link'
import SecFactsPanel from '@/components/SecFactsPanel'
import AppShell from '@/components/AppShell'
import ValuationPanel from '@/components/ValuationPanel'

interface ChartDataPoint {
  date: string
  revenue: number | null
  operating_income: number | null
  operating_margin: number | null
  fcf: number | null
  fcf_margin: number | null
  ebitda: number | null
}

export default function FundamentalsPage() {
  const params = useParams<{ ticker: string }>()
  const ticker = params.ticker?.toUpperCase() ?? ''
  const search = useSearchParams()
  const returnTo = researchReturn(search.get('returnTo'))?.href || ''
  return (
    <AppShell company={ticker}>
      <FundamentalsOverview ticker={ticker} returnTo={returnTo} />
      <div className="mt-8">
        <ValuationPanel symbol={ticker} />
      </div>
      <div className="mt-8">
        <SecFactsPanel key={ticker} symbol={ticker} />
      </div>
    </AppShell>
  )
}

function FundamentalsOverview({
  ticker,
  returnTo,
}: {
  ticker: string
  returnTo: string
}) {
  const { data, isLoading, error } = useFundamentals(ticker)

  const formatPercent = (value: number | null | undefined) => {
    if (value == null || !Number.isFinite(value)) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      maximumFractionDigits: 1,
    }).format(value)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
    })
  }

  const prepareChartData = (series: FundamentalsSeries): ChartDataPoint[] => {
    if (!series) return []

    // Use all available series dates, in chronological order.
    const availableSeries: (FundamentalPoint[] | undefined)[] =
      Object.values(series)
    const dates = [
      ...new Set(
        availableSeries.flatMap(
          (points) => points?.map((point) => point.date) ?? [],
        ),
      ),
    ].sort()

    return dates.map((date: string) => {
      const getValueForDate = (
        seriesData?: Array<{ date: string; value: number | null }>,
      ) => {
        const point = seriesData?.find((p) => p.date === date)
        return point?.value ?? null
      }

      const revenue = getValueForDate(series.revenue_q)
      const operatingIncome = getValueForDate(series.operating_income_q)
      const operatingMargin = getValueForDate(series.operating_margin_q)
      const fcf = getValueForDate(series.fcf_q)
      const fcfMargin = getValueForDate(series.fcf_margin_q)
      const ebitda = getValueForDate(series.ebitda_q)

      return {
        date: formatDate(date),
        revenue: revenue != null ? revenue / 1e6 : null, // Convert to millions
        operating_income:
          operatingIncome != null ? operatingIncome / 1e6 : null,
        operating_margin:
          operatingMargin != null ? operatingMargin * 100 : null, // Convert to percentage
        fcf: fcf != null ? fcf / 1e6 : null,
        fcf_margin: fcfMargin != null ? fcfMargin * 100 : null,
        ebitda: ebitda != null ? ebitda / 1e6 : null,
      }
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center px-4 py-12">
        <div className="text-center">
          <div className="h-16 w-16 animate-spin rounded-full border-4 border-white/30 border-t-white mx-auto mb-4" />
          <p className="text-white text-xl">Loading {ticker} fundamentals...</p>
          <p className="text-white/60 text-sm mt-2">Analyzing financial data</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center px-4 py-12">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Error Loading Fundamentals
          </h2>
          <p className="text-red-300 mb-6">{error.message}</p>
          <Link
            href={companyResearchHref(ticker, returnTo)}
            className="button-secondary"
          >
            ← Back to company
          </Link>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center px-4 py-12">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-white mb-2">
            No Data Available
          </h2>
          <p className="text-white/70 mb-6">
            No fundamentals data available for {ticker}
          </p>
          <Link
            href={companyResearchHref(ticker, returnTo)}
            className="button-secondary"
          >
            ← Back to company
          </Link>
        </div>
      </div>
    )
  }

  const { ttm, series } = data
  const chartData = prepareChartData(series)
  const growthLabels: Record<string, string> = {
    revenue_growth_yoy: 'Revenue growth',
    fcf_growth_yoy: 'Free cash flow growth',
    operating_income_growth_yoy: 'Operating income growth',
    ebitda_growth_yoy: 'EBITDA growth',
  }

  return (
    <div>
      <div>
        {/* Header */}
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link
              href={companyResearchHref(ticker, returnTo)}
              className="mb-4 inline-flex items-center gap-2 text-xs text-slate-400 transition-colors hover:text-violet-200"
            >
              <ArrowLeftIcon className="h-3.5 w-3.5" />
              Back to {ticker}
            </Link>
            <div>
              <p className="eyebrow mb-2">Financial research</p>
              <h1 className="page-title">{ticker} fundamentals</h1>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                Financial statements, reporting periods, and source evidence.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {ttm.insufficient_data && (
              <div className="rounded-lg border border-amber-400/20 bg-amber-400/[0.08] px-4 py-2">
                <span className="text-sm font-medium text-amber-200">
                  Limited financial data
                </span>
              </div>
            )}
            <Link href={companyComparisonHref(ticker)} className="button-secondary">
              <Scale className="h-4 w-4" />
              Compare company
            </Link>
          </div>
        </div>

        <div className="surface mb-6 space-y-2 p-4 text-sm leading-6 text-slate-400">
          <p>
            {data.metadata?.source ?? 'Yahoo Finance via yfinance'} · TTM totals
            require four consecutive reporting quarters. Amounts use the
            provider’s statement units; currency is not assumed to be USD.
          </p>
          {ttm.period_metadata?.revenue_ttm && (
            <p>
              Latest revenue period ended{' '}
              {ttm.period_metadata.revenue_ttm.period_end}.
            </p>
          )}
          <p>
            Missing components remain unavailable. Growth with a zero or
            negative prior-year base is not meaningful as a percentage.
          </p>
          {Object.entries(ttm.growth_metadata ?? {}).map(([field, basis]) => (
            <p key={field}>
              {growthLabels[field] ?? field}:{' '}
              {basis.status === 'non_positive_prior'
                ? 'Not meaningful (non-positive prior year)'
                : basis.status === 'insufficient_history'
                  ? 'Insufficient comparable history'
                  : basis.basis === 'fiscal_year'
                    ? 'Fiscal-year YoY (annual fallback)'
                    : 'TTM YoY'}
              {basis.current_period_end &&
                ` · ${basis.current_period_end} vs ${basis.prior_period_end}`}
            </p>
          ))}
        </div>

        {/* Summary Cards */}
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-4">
          <div className="surface min-w-0 p-5 sm:p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <CurrencyDollarIcon className="h-6 w-6 text-green-400" />
                <p className="text-white/70 text-sm font-medium">Revenue TTM</p>
              </div>
              {ttm.revenue_growth_yoy != null && (
                <div
                  className={`flex items-center text-xs px-2 py-1 rounded-full ${
                    ttm.revenue_growth_yoy > 0
                      ? 'bg-green-500/20 text-green-300'
                      : ttm.revenue_growth_yoy < 0
                        ? 'bg-red-500/20 text-red-300'
                        : 'bg-white/10 text-white/70'
                  }`}
                >
                  {ttm.revenue_growth_yoy ===
                  0 ? null : ttm.revenue_growth_yoy > 0 ? (
                    <ArrowTrendingUpIcon className="h-3 w-3 mr-1" />
                  ) : (
                    <ArrowTrendingDownIcon className="h-3 w-3 mr-1" />
                  )}
                  {formatPercent(ttm.revenue_growth_yoy)}{' '}
                  {ttm.growth_metadata?.revenue_growth_yoy?.basis ===
                  'fiscal_year'
                    ? 'FY YoY'
                    : 'TTM YoY'}
                </div>
              )}
            </div>
            <p className="text-3xl font-bold text-white">
              {amount(ttm.revenue_ttm)}
            </p>
          </div>

          <div className="surface min-w-0 p-5 sm:p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ArrowTrendingUpIcon className="h-6 w-6 text-blue-400" />
                <p className="text-white/70 text-sm font-medium">
                  Free Cash Flow TTM
                </p>
              </div>
              {ttm.fcf_growth_yoy != null && (
                <div
                  className={`flex items-center text-xs px-2 py-1 rounded-full ${
                    ttm.fcf_growth_yoy > 0
                      ? 'bg-green-500/20 text-green-300'
                      : ttm.fcf_growth_yoy < 0
                        ? 'bg-red-500/20 text-red-300'
                        : 'bg-white/10 text-white/70'
                  }`}
                >
                  {ttm.fcf_growth_yoy === 0 ? null : ttm.fcf_growth_yoy > 0 ? (
                    <ArrowTrendingUpIcon className="h-3 w-3 mr-1" />
                  ) : (
                    <ArrowTrendingDownIcon className="h-3 w-3 mr-1" />
                  )}
                  {formatPercent(ttm.fcf_growth_yoy)}{' '}
                  {ttm.growth_metadata?.fcf_growth_yoy?.basis === 'fiscal_year'
                    ? 'FY YoY'
                    : 'TTM YoY'}
                </div>
              )}
            </div>
            <p className="text-3xl font-bold text-white">
              {amount(ttm.fcf_ttm)}
            </p>
          </div>

          <div className="surface min-w-0 p-5 sm:p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ChartBarIcon className="h-6 w-6 text-purple-400" />
                <p className="text-white/70 text-sm font-medium">
                  Operating Margin TTM
                </p>
              </div>
              {ttm.margin_growth_yoy_pp != null && (
                <div
                  className={`flex items-center text-xs px-2 py-1 rounded-full ${
                    ttm.margin_growth_yoy_pp > 0
                      ? 'bg-green-500/20 text-green-300'
                      : ttm.margin_growth_yoy_pp < 0
                        ? 'bg-red-500/20 text-red-300'
                        : 'bg-white/10 text-white/70'
                  }`}
                >
                  {ttm.margin_growth_yoy_pp ===
                  0 ? null : ttm.margin_growth_yoy_pp > 0 ? (
                    <ArrowTrendingUpIcon className="h-3 w-3 mr-1" />
                  ) : (
                    <ArrowTrendingDownIcon className="h-3 w-3 mr-1" />
                  )}
                  {ttm.margin_growth_yoy_pp.toFixed(1)}pp YoY
                </div>
              )}
            </div>
            <p className="text-3xl font-bold text-white">
              {formatPercent(ttm.operating_margin_ttm)}
            </p>
          </div>

          <div className="surface min-w-0 p-5 sm:p-6">
            <div className="flex items-center gap-2 mb-3">
              <BanknotesIcon className="h-6 w-6 text-orange-400" />
              <p className="text-white/70 text-sm font-medium">
                Debt/Cash Ratio
              </p>
            </div>
            <p className="text-3xl font-bold text-white">
              {ttm.debt_to_cash != null ? ttm.debt_to_cash.toFixed(2) : 'N/A'}
            </p>
            <p className="text-white/60 text-sm mt-1">
              Reported debt ÷ available cash and short-term investments
            </p>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* FCF Margin Chart */}
          <div className="surface min-w-0 p-5 sm:p-6">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              Free cash flow margin · Quarterly
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(255,255,255,0.1)"
                  />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(0,0,0,0.9)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: '8px',
                      color: 'white',
                    }}
                    formatter={(value) => {
                      if (typeof value === 'number') {
                        return [`${value.toFixed(1)}%`, 'FCF Margin']
                      }
                      return ['N/A', 'FCF Margin']
                    }}
                  />
                  <Bar
                    dataKey="fcf_margin"
                    fill="#3B82F6"
                    name="FCF Margin %"
                    radius={[4, 4, 0, 0]}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Operating Margin Chart */}
          <div className="surface min-w-0 p-5 sm:p-6">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              Operating margin · Quarterly
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(255,255,255,0.1)"
                  />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(0,0,0,0.9)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: '8px',
                      color: 'white',
                    }}
                    formatter={(value) => {
                      if (typeof value === 'number') {
                        return [`${value.toFixed(1)}%`, 'Operating Margin']
                      }
                      return ['N/A', 'Operating Margin']
                    }}
                  />
                  <Bar
                    dataKey="operating_margin"
                    fill="#10B981"
                    name="Operating Margin %"
                    radius={[4, 4, 0, 0]}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Revenue Chart */}
          <div className="surface min-w-0 p-5 sm:p-6">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              Revenue · Quarterly
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(255,255,255,0.1)"
                  />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(0,0,0,0.9)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: '8px',
                      color: 'white',
                    }}
                    formatter={(value) =>
                      typeof value === 'number'
                        ? [`${value.toFixed(0)}M`, 'Revenue']
                        : ['N/A', 'Revenue']
                    }
                  />
                  <Bar
                    dataKey="revenue"
                    fill="#8B5CF6"
                    name="Revenue (millions of statement units)"
                    radius={[4, 4, 0, 0]}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* EBITDA Chart */}
          <div className="surface min-w-0 p-5 sm:p-6">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              EBITDA · Quarterly
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(255,255,255,0.1)"
                  />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(0,0,0,0.9)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: '8px',
                      color: 'white',
                    }}
                    formatter={(value) => {
                      if (typeof value === 'number') {
                        return [`${value.toFixed(0)}M`, 'EBITDA']
                      }
                      return ['N/A', 'EBITDA']
                    }}
                  />
                  <Bar
                    dataKey="ebitda"
                    fill="#F59E0B"
                    name="EBITDA (millions of statement units)"
                    radius={[4, 4, 0, 0]}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 surface min-w-0 p-5 sm:p-6">
          <h3 className="text-xl font-semibold text-white mb-4">
            Quick Actions
          </h3>
          <div className="flex flex-wrap gap-4">
            <Link
              href={
                returnTo.startsWith('/compare')
                  ? returnTo
                  : `/compare?tickers=${encodeURIComponent(ticker)}`
              }
              className="button-primary"
            >
              Compare with other companies
            </Link>
            <Link href="/screener" className="button-secondary">
              Open screener
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

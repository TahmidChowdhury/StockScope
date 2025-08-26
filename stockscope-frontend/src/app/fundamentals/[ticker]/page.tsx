'use client'

import { useFundamentals } from '@/hooks/useFundamentals'
import { 
  ComposedChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts'
import { 
  ArrowTrendingUpIcon, 
  ArrowTrendingDownIcon, 
  ArrowLeftIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  BanknotesIcon
} from '@heroicons/react/24/outline'
import { FundamentalsSeries } from '@/types'
import { use } from 'react'
import Link from 'next/link'

interface FundamentalsPageProps {
  params: Promise<{
    ticker: string
  }>
}

interface ChartDataPoint {
  date: string
  revenue: number | null
  operating_income: number | null
  operating_margin: number | null
  fcf: number | null
  fcf_margin: number | null
  ebitda: number | null
}

export default function FundamentalsPage({ params }: FundamentalsPageProps) {
  const { ticker } = use(params)
  const { data, isLoading, error } = useFundamentals(ticker)

  const formatPercent = (value: number | null) => {
    if (value === null) return 'N/A'
    return new Intl.NumberFormat('en-US', { 
      style: 'percent', 
      maximumFractionDigits: 1 
    }).format(value)
  }

  const formatCurrency = (value: number | null, compact = true) => {
    if (value === null) return 'N/A'
    if (compact && Math.abs(value) >= 1e9) {
      return `$${(value / 1e9).toFixed(1)}B`
    } else if (compact && Math.abs(value) >= 1e6) {
      return `$${(value / 1e6).toFixed(1)}M`
    }
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: 'USD',
      maximumFractionDigits: 0
    }).format(value)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short' 
    })
  }

  const prepareChartData = (series: FundamentalsSeries): ChartDataPoint[] => {
    if (!series) return []
    
    // Get the dates from revenue data (assuming all series have same dates)
    const dates = series.revenue_q?.map((point) => point.date) || []
    
    return dates.map((date: string) => {
      const getValueForDate = (seriesData: Array<{ date: string; value: number | null }>) => {
        const point = seriesData.find((p) => p.date === date)
        return point?.value || null
      }

      const revenue = getValueForDate(series.revenue_q)
      const operatingIncome = getValueForDate(series.operating_income_q)
      const operatingMargin = getValueForDate(series.operating_margin_q)
      const fcf = getValueForDate(series.fcf_q)
      const fcfMargin = getValueForDate(series.fcf_margin_q)
      const ebitda = getValueForDate(series.ebitda_q)

      return {
        date: formatDate(date),
        revenue: revenue ? revenue / 1e6 : null, // Convert to millions
        operating_income: operatingIncome ? operatingIncome / 1e6 : null,
        operating_margin: operatingMargin ? operatingMargin * 100 : null, // Convert to percentage
        fcf: fcf ? fcf / 1e6 : null,
        fcf_margin: fcfMargin ? fcfMargin * 100 : null,
        ebitda: ebitda ? ebitda / 1e6 : null
      }
    }).reverse() // Show oldest to newest
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
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
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-white mb-2">Error Loading Fundamentals</h2>
          <p className="text-red-300 mb-6">{error.message}</p>
          <Link
            href="/fundamentals"
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
          >
            ← Back to Search
          </Link>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-white mb-2">No Data Available</h2>
          <p className="text-white/70 mb-6">No fundamentals data available for {ticker}</p>
          <Link
            href="/fundamentals"
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
          >
            ← Back to Search
          </Link>
        </div>
      </div>
    )
  }

  const { ttm, series } = data
  const chartData = prepareChartData(series)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors backdrop-blur-sm border border-white/20"
            >
              <ArrowLeftIcon className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-4xl font-bold text-white">📈 {ticker} Fundamentals</h1>
              <p className="text-white/70">Comprehensive financial metrics analysis</p>
            </div>
          </div>
          {ttm.insufficient_data && (
            <div className="bg-yellow-500/20 backdrop-blur-sm px-4 py-2 rounded-lg border border-yellow-500/50">
              <span className="text-yellow-300 text-sm font-medium">⚠️ Limited Data Available</span>
            </div>
          )}
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <CurrencyDollarIcon className="h-6 w-6 text-green-400" />
                <p className="text-white/70 text-sm font-medium">Revenue TTM</p>
              </div>
              {ttm.revenue_growth_yoy && (
                <div className={`flex items-center text-xs px-2 py-1 rounded-full ${
                  ttm.revenue_growth_yoy > 0 ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
                }`}>
                  {ttm.revenue_growth_yoy > 0 ? (
                    <ArrowTrendingUpIcon className="h-3 w-3 mr-1" />
                  ) : (
                    <ArrowTrendingDownIcon className="h-3 w-3 mr-1" />
                  )}
                  {formatPercent(Math.abs(ttm.revenue_growth_yoy))} YoY
                </div>
              )}
            </div>
            <p className="text-3xl font-bold text-white">
              {formatCurrency(ttm.revenue_ttm)}
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ArrowTrendingUpIcon className="h-6 w-6 text-blue-400" />
                <p className="text-white/70 text-sm font-medium">Free Cash Flow TTM</p>
              </div>
              {ttm.fcf_growth_yoy && (
                <div className={`flex items-center text-xs px-2 py-1 rounded-full ${
                  ttm.fcf_growth_yoy > 0 ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
                }`}>
                  {ttm.fcf_growth_yoy > 0 ? (
                    <ArrowTrendingUpIcon className="h-3 w-3 mr-1" />
                  ) : (
                    <ArrowTrendingDownIcon className="h-3 w-3 mr-1" />
                  )}
                  {formatPercent(Math.abs(ttm.fcf_growth_yoy))} YoY
                </div>
              )}
            </div>
            <p className="text-3xl font-bold text-white">
              {formatCurrency(ttm.fcf_ttm)}
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ChartBarIcon className="h-6 w-6 text-purple-400" />
                <p className="text-white/70 text-sm font-medium">Operating Margin TTM</p>
              </div>
              {ttm.margin_growth_yoy_pp && (
                <div className={`flex items-center text-xs px-2 py-1 rounded-full ${
                  ttm.margin_growth_yoy_pp > 0 ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
                }`}>
                  {ttm.margin_growth_yoy_pp > 0 ? (
                    <ArrowTrendingUpIcon className="h-3 w-3 mr-1" />
                  ) : (
                    <ArrowTrendingDownIcon className="h-3 w-3 mr-1" />
                  )}
                  {Math.abs(ttm.margin_growth_yoy_pp).toFixed(1)}pp YoY
                </div>
              )}
            </div>
            <p className="text-3xl font-bold text-white">
              {formatPercent(ttm.operating_margin_ttm)}
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center gap-2 mb-3">
              <BanknotesIcon className="h-6 w-6 text-orange-400" />
              <p className="text-white/70 text-sm font-medium">Debt/Cash Ratio</p>
            </div>
            <p className="text-3xl font-bold text-white">
              {ttm.debt_to_cash ? ttm.debt_to_cash.toFixed(2) : 'N/A'}
            </p>
            <p className="text-white/60 text-sm mt-1">
              {ttm.debt_to_cash && ttm.debt_to_cash <= 1 ? 'Conservative' : 
               ttm.debt_to_cash && ttm.debt_to_cash <= 2 ? 'Moderate' : 'High Leverage'}
            </p>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* FCF Margin Chart */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              💸 FCF Margin % (Quarterly)
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.2)', 
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value) => {
                      if (typeof value === 'number') {
                        return [`${value.toFixed(1)}%`, 'FCF Margin']
                      }
                      return ['N/A', 'FCF Margin']
                    }} 
                  />
                  <Bar dataKey="fcf_margin" fill="#3B82F6" name="FCF Margin %" radius={[4, 4, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Operating Margin Chart */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              📊 Operating Margin % (Quarterly)
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.2)', 
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value) => {
                      if (typeof value === 'number') {
                        return [`${value.toFixed(1)}%`, 'Operating Margin']
                      }
                      return ['N/A', 'Operating Margin']
                    }} 
                  />
                  <Bar dataKey="operating_margin" fill="#10B981" name="Operating Margin %" radius={[4, 4, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Revenue Chart */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              💰 Revenue (Quarterly)
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.2)', 
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value) => (typeof value === 'number' ? [`$${value.toFixed(0)}M`, 'Revenue'] : ['N/A', 'Revenue'])} 
                  />
                  <Bar dataKey="revenue" fill="#8B5CF6" name="Revenue ($M)" radius={[4, 4, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* EBITDA Chart */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              📈 EBITDA (Quarterly)
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.2)', 
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value) => {
                      if (typeof value === 'number') {
                        return [`$${value.toFixed(0)}M`, 'EBITDA']
                      }
                      return ['N/A', 'EBITDA']
                    }} 
                  />
                  <Bar dataKey="ebitda" fill="#F59E0B" name="EBITDA ($M)" radius={[4, 4, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
          <h3 className="text-xl font-semibold text-white mb-4">Quick Actions</h3>
          <div className="flex flex-wrap gap-4">
            <Link
              href="/compare"
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors flex items-center gap-2 font-medium"
            >
              ⚖️ Compare with Others
            </Link>
            <Link
              href="/screener"
              className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg transition-colors flex items-center gap-2 font-medium"
            >
              🔍 Screen Similar Companies
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
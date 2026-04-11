'use client'

import { useState, useCallback } from 'react'
import { useCompare } from '@/hooks/useFundamentals'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const getPassword = () => typeof window !== 'undefined' ? localStorage.getItem('stockscope_password') || '' : ''
import { 
  ComposedChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts'
import { PlusIcon, XMarkIcon } from '@heroicons/react/24/outline'
import SideNav from '@/components/SideNav'
import Link from 'next/link'
import { FundamentalsTTM } from '@/types'

interface ChartDataItem {
  ticker: string
  fcf_margin_ttm: number
  operating_margin_ttm: number
  revenue_ttm: number
  fill: string
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316']

export default function ComparePage() {
  const [tickers, setTickers] = useState<string[]>([])
  const [inputValue, setInputValue] = useState('')
  const [validating, setValidating] = useState(false)
  const [tickerError, setTickerError] = useState<string | null>(null)
  const compare = useCompare()

  const addTicker = useCallback(async () => {
    const symbol = inputValue.trim().toUpperCase()
    if (!symbol) return
    if (tickers.includes(symbol)) {
      setTickerError(`${symbol} is already added`)
      return
    }
    setValidating(true)
    setTickerError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/stocks/validate/${symbol}?password=${encodeURIComponent(getPassword())}`
      )
      if (!res.ok) throw new Error('Validation request failed')
      const data = await res.json()
      if (!data.valid) {
        setTickerError(`"${symbol}" not found — check the ticker symbol`)
        return
      }
      setTickers(prev => [...prev, symbol])
      setInputValue('')
    } catch {
      setTickerError('Could not validate ticker — check your connection')
    } finally {
      setValidating(false)
    }
  }, [inputValue, tickers])

  const removeTicker = (tickerToRemove: string) => {
    setTickers(tickers.filter(t => t !== tickerToRemove))
  }

  const handleCompare = () => {
    const validTickers = tickers.filter(t => t.trim())
    if (validTickers.length > 1) {
      compare.mutate({ tickers: validTickers })
    }
  }

  const formatPercent = (value: number | null | undefined) => {
    if (value == null || isNaN(value)) return '—'
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

  const prepareChartData = (data: FundamentalsTTM[]): ChartDataItem[] => {
    return data.map((item, index) => ({
      ticker: item.ticker,
      fcf_margin_ttm: (item.fcf_margin_ttm || 0) * 100,
      operating_margin_ttm: (item.operating_margin_ttm || 0) * 100,
      revenue_ttm: (item.revenue_ttm || 0) / 1e9, // Convert to billions
      fill: COLORS[index % COLORS.length]
    }))
  }

  const validTickers = tickers.filter(t => t)
  const canCompare = validTickers.length >= 2

  return (
    <div className="flex h-screen overflow-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <SideNav activePage="compare" />
      <main className="flex-1 overflow-y-auto">
        <div className="lg:hidden h-4" />
        <div className="max-w-5xl mx-auto px-4 py-4 lg:py-8 pb-24 lg:pb-10">

          {/* Page header */}
          <div className="mb-6 lg:mb-8">
            <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight">Compare Companies</h1>
            <p className="text-sm text-white/50 mt-0.5">Side-by-side financial metrics</p>
          </div>

          {/* Input card */}
          <div className="rounded-2xl bg-white/[0.06] border border-white/10 p-4 lg:p-5 mb-5">

            {/* Search row */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => { setInputValue(e.target.value.toUpperCase()); setTickerError(null) }}
                  onKeyDown={(e) => e.key === 'Enter' && addTicker()}
                  placeholder="Ticker symbol — AAPL, MSFT…"
                  className="w-full px-4 py-2.5 rounded-xl text-sm transition-all focus:outline-none focus:ring-1
                    bg-slate-800 text-slate-100 placeholder-slate-500
                    border border-slate-600 focus:ring-purple-400/60 focus:border-purple-400/40
                    [color-scheme:dark]"
                />
              </div>
              <button
                onClick={addTicker}
                disabled={!inputValue.trim() || validating}
                className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-30 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors flex items-center gap-1.5 flex-shrink-0"
              >
                {validating
                  ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  : <PlusIcon className="h-4 w-4" />}
                {validating ? '' : 'Add'}
              </button>
            </div>

            {/* Inline error */}
            {tickerError && (
              <p className="text-red-400 text-xs mt-2">{tickerError}</p>
            )}

            {/* Ticker chips */}
            {validTickers.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {validTickers.map((ticker, index) => (
                  <span
                    key={ticker}
                    className="inline-flex items-center gap-1.5 pl-3 pr-2 py-1 rounded-full text-sm font-medium text-white border"
                    style={{
                      backgroundColor: COLORS[index % COLORS.length] + '22',
                      borderColor: COLORS[index % COLORS.length] + '55',
                    }}
                  >
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    {ticker}
                    <button
                      onClick={() => removeTicker(ticker)}
                      className="text-white/50 hover:text-white/90 transition-colors ml-0.5"
                    >
                      <XMarkIcon className="h-3.5 w-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Divider + CTA */}
            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={handleCompare}
                disabled={!canCompare || compare.isPending}
                className="flex-1 lg:flex-none lg:px-6 py-2.5 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2
                  disabled:bg-white/8 disabled:text-white/30 disabled:cursor-not-allowed
                  enabled:bg-gradient-to-r enabled:from-purple-600 enabled:to-indigo-600 enabled:hover:from-purple-500 enabled:hover:to-indigo-500 enabled:text-white enabled:shadow-lg enabled:shadow-purple-900/40"
              >
                {compare.isPending ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Comparing…
                  </>
                ) : (
                  'Run Comparison'
                )}
              </button>
              {!canCompare && (
                <p className="text-white/35 text-xs">Add at least 2 tickers</p>
              )}
            </div>
          </div>

          {/* Error state */}
          {compare.isError && (
            <div className="rounded-2xl bg-red-500/10 border border-red-500/30 p-4 mb-5">
              <p className="text-red-300 font-medium text-sm">Comparison failed</p>
              <p className="text-red-400/70 text-xs mt-0.5">{compare.error?.message}</p>
            </div>
          )}

          {/* Results */}
          {compare.data && (
            <div className="space-y-5 lg:space-y-6">

              {/* Summary chips */}
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-2xl bg-white/[0.06] border border-white/10 p-3 lg:p-4">
                  <p className="text-white/50 text-xs mb-1">Compared</p>
                  <p className="text-xl lg:text-2xl font-bold text-white">{compare.data.length}</p>
                </div>
                <div className="rounded-2xl bg-white/[0.06] border border-white/10 p-3 lg:p-4">
                  <p className="text-white/50 text-xs mb-1">Top Revenue</p>
                  <p className="text-base lg:text-xl font-bold text-emerald-400">
                    {compare.data.reduce((max, c) => (c.revenue_ttm || 0) > (max.revenue_ttm || 0) ? c : max).ticker}
                  </p>
                  <p className="text-white/40 text-xs truncate">
                    {formatCurrency(Math.max(...compare.data.map(c => c.revenue_ttm || 0)))}
                  </p>
                </div>
                <div className="rounded-2xl bg-white/[0.06] border border-white/10 p-3 lg:p-4">
                  <p className="text-white/50 text-xs mb-1">Best FCF</p>
                  <p className="text-base lg:text-xl font-bold text-blue-400">
                    {compare.data.reduce((max, c) => (c.fcf_margin_ttm || 0) > (max.fcf_margin_ttm || 0) ? c : max).ticker}
                  </p>
                  <p className="text-white/40 text-xs truncate">
                    {formatPercent(Math.max(...compare.data.map(c => c.fcf_margin_ttm || 0)))}
                  </p>
                </div>
              </div>

              {/* Metrics table */}
              <div className="rounded-2xl bg-white/[0.06] border border-white/10 overflow-hidden">
                <div className="px-4 lg:px-5 py-3 border-b border-white/10">
                  <h3 className="text-sm font-semibold text-white/80 uppercase tracking-wider">TTM Metrics</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/8">
                        <th className="px-4 lg:px-5 py-3 text-left text-xs font-medium text-white/40 uppercase tracking-wider">Company</th>
                        <th className="px-4 lg:px-5 py-3 text-right text-xs font-medium text-white/40 uppercase tracking-wider">Revenue</th>
                        <th className="px-4 lg:px-5 py-3 text-right text-xs font-medium text-white/40 uppercase tracking-wider">FCF Margin</th>
                        <th className="px-4 lg:px-5 py-3 text-right text-xs font-medium text-white/40 uppercase tracking-wider">Op. Margin</th>
                        <th className="px-4 lg:px-5 py-3 text-right text-xs font-medium text-white/40 uppercase tracking-wider">Rev. Growth</th>
                        <th className="px-4 lg:px-5 py-3 text-right text-xs font-medium text-white/40 uppercase tracking-wider">FCF Growth</th>
                        <th className="px-4 lg:px-5 py-3 text-right text-xs font-medium text-white/40 uppercase tracking-wider">D/C</th>
                        <th className="px-4 lg:px-5 py-3 text-right text-xs font-medium text-white/40 uppercase tracking-wider" />
                      </tr>
                    </thead>
                    <tbody>
                      {compare.data.map((company, index) => (
                        <tr key={company.ticker} className="border-b border-white/[0.06] hover:bg-white/[0.04] transition-colors">
                          <td className="px-4 lg:px-5 py-3">
                            <div className="flex items-center gap-2.5">
                              <span
                                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                style={{ backgroundColor: COLORS[index % COLORS.length] }}
                              />
                              <span className="font-semibold text-white">{company.ticker}</span>
                              {company.insufficient_data && (
                                <span className="text-[10px] text-yellow-400/80 bg-yellow-400/10 px-1.5 py-0.5 rounded-full">Limited</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 lg:px-5 py-3 text-right text-white font-medium">{formatCurrency(company.revenue_ttm)}</td>
                          <td className="px-4 lg:px-5 py-3 text-right text-white/80">{formatPercent(company.fcf_margin_ttm)}</td>
                          <td className="px-4 lg:px-5 py-3 text-right text-white/80">{formatPercent(company.operating_margin_ttm)}</td>
                          <td className={`px-4 lg:px-5 py-3 text-right font-medium ${company.revenue_growth_yoy && company.revenue_growth_yoy > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {company.revenue_growth_yoy && company.revenue_growth_yoy > 0 ? '+' : ''}{formatPercent(company.revenue_growth_yoy)}
                          </td>
                          <td className={`px-4 lg:px-5 py-3 text-right font-medium ${company.fcf_growth_yoy && company.fcf_growth_yoy > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {company.fcf_growth_yoy && company.fcf_growth_yoy > 0 ? '+' : ''}{formatPercent(company.fcf_growth_yoy)}
                          </td>
                          <td className="px-4 lg:px-5 py-3 text-right text-white/60">{company.debt_to_cash ? company.debt_to_cash.toFixed(2) : '—'}</td>
                          <td className="px-4 lg:px-5 py-3 text-right">
                            <Link href={`/fundamentals/${company.ticker}`} className="text-purple-400 hover:text-purple-300 font-medium transition-colors text-xs">
                              Details →
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-5">
                <div className="rounded-2xl bg-white/[0.06] border border-white/10 p-4 lg:p-5">
                  <h3 className="text-sm font-semibold text-white/80 mb-4">Margins (TTM)</h3>
                  <div className="h-64 lg:h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={prepareChartData(compare.data)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                        <XAxis dataKey="ticker" stroke="rgba(255,255,255,0.4)" tick={{ fontSize: 12 }} />
                        <YAxis stroke="rgba(255,255,255,0.4)" tick={{ fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'rgba(15,15,25,0.95)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '10px', color: 'white', fontSize: 13 }}
                          formatter={(value: number, name: string) => [`${value?.toFixed(1)}%`, name === 'fcf_margin_ttm' ? 'FCF Margin' : 'Op. Margin']}
                        />
                        <Legend wrapperStyle={{ fontSize: 12 }} />
                        <Bar dataKey="fcf_margin_ttm" fill="#6366f1" name="FCF Margin %" radius={[3, 3, 0, 0]} />
                        <Bar dataKey="operating_margin_ttm" fill="#10B981" name="Op. Margin %" radius={[3, 3, 0, 0]} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="rounded-2xl bg-white/[0.06] border border-white/10 p-4 lg:p-5">
                  <h3 className="text-sm font-semibold text-white/80 mb-4">Revenue TTM ($B)</h3>
                  <div className="h-64 lg:h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={prepareChartData(compare.data)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                        <XAxis dataKey="ticker" stroke="rgba(255,255,255,0.4)" tick={{ fontSize: 12 }} />
                        <YAxis stroke="rgba(255,255,255,0.4)" tick={{ fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'rgba(15,15,25,0.95)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '10px', color: 'white', fontSize: 13 }}
                          formatter={(value: number) => [`$${value?.toFixed(1)}B`, 'Revenue TTM']}
                        />
                        <Bar dataKey="revenue_ttm" fill="#a855f7" name="Revenue ($B)" radius={[4, 4, 0, 0]} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

            </div>
          )}
        </div>
      </main>
    </div>
  )
}
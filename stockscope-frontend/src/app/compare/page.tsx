'use client'

import { useState } from 'react'
import { useCompare } from '@/hooks/useFundamentals'
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
import { PlusIcon, XMarkIcon, ArrowLeftIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline'
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
  const [tickers, setTickers] = useState<string[]>([''])
  const [inputValue, setInputValue] = useState('')
  const compare = useCompare()

  const addTicker = () => {
    if (inputValue.trim() && !tickers.includes(inputValue.trim().toUpperCase())) {
      setTickers([...tickers.filter(t => t), inputValue.trim().toUpperCase()])
      setInputValue('')
    }
  }

  const removeTicker = (tickerToRemove: string) => {
    setTickers(tickers.filter(t => t !== tickerToRemove))
  }

  const handleCompare = () => {
    const validTickers = tickers.filter(t => t.trim())
    if (validTickers.length > 1) {
      compare.mutate({ tickers: validTickers })
    }
  }

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

  const prepareChartData = (data: FundamentalsTTM[]): ChartDataItem[] => {
    return data.map((item, index) => ({
      ticker: item.ticker,
      fcf_margin_ttm: (item.fcf_margin_ttm || 0) * 100,
      operating_margin_ttm: (item.operating_margin_ttm || 0) * 100,
      revenue_ttm: (item.revenue_ttm || 0) / 1e9, // Convert to billions
      fill: COLORS[index % COLORS.length]
    }))
  }

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
              <h1 className="text-4xl font-bold text-white">⚖️ Compare Companies</h1>
              <p className="text-white/70">Side-by-side analysis of financial metrics</p>
            </div>
          </div>
        </div>

        {/* Ticker Input Section */}
        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20 mb-8">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <PlusIcon className="h-5 w-5" />
            Select Companies to Compare
          </h2>
          
          <div className="flex gap-3 mb-6">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value.toUpperCase())}
              onKeyPress={(e) => e.key === 'Enter' && addTicker()}
              placeholder="Enter ticker symbol (e.g., AAPL, MSFT, GOOGL)"
              className="flex-1 px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
            />
            <button
              onClick={addTicker}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2 font-medium"
            >
              <PlusIcon className="h-4 w-4" />
              Add
            </button>
          </div>

          {/* Selected Tickers */}
          {tickers.filter(t => t).length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-white/70 mb-3">Selected Companies:</h3>
              <div className="flex flex-wrap gap-2">
                {tickers.filter(t => t).map((ticker, index) => (
                  <span
                    key={ticker}
                    className="px-4 py-2 bg-white/20 backdrop-blur-sm text-white rounded-full flex items-center gap-2 border border-white/30"
                    style={{ borderColor: COLORS[index % COLORS.length] + '80' }}
                  >
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    {ticker}
                    <button
                      onClick={() => removeTicker(ticker)}
                      className="text-white/70 hover:text-white transition-colors"
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={handleCompare}
            disabled={tickers.filter(t => t).length < 2 || compare.isPending}
            className="px-8 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {compare.isPending ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Comparing...
              </>
            ) : (
              '⚖️ Compare Companies'
            )}
          </button>

          {tickers.filter(t => t).length < 2 && (
            <p className="text-white/60 text-sm mt-2">Add at least 2 companies to compare</p>
          )}
        </div>

        {/* Loading State */}
        {compare.isPending && (
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-8 border border-white/20 text-center">
            <div className="h-12 w-12 animate-spin rounded-full border-2 border-white/30 border-t-white mx-auto mb-4" />
            <p className="text-white text-lg">Loading comparison data...</p>
          </div>
        )}

        {/* Error State */}
        {compare.isError && (
          <div className="bg-red-500/20 backdrop-blur-sm rounded-xl p-6 border border-red-500/50 mb-8">
            <h3 className="text-red-300 font-medium text-lg mb-2">⚠️ Comparison Failed</h3>
            <p className="text-red-200">{compare.error?.message}</p>
          </div>
        )}

        {/* Results */}
        {compare.data && (
          <div className="space-y-8">
            {/* Key Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <h3 className="text-white/70 text-sm mb-2">Companies Compared</h3>
                <p className="text-3xl font-bold text-white">{compare.data.length}</p>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <h3 className="text-white/70 text-sm mb-2">Highest Revenue</h3>
                <p className="text-2xl font-bold text-green-400">
                  {compare.data.reduce((max, company) => 
                    (company.revenue_ttm || 0) > (max.revenue_ttm || 0) ? company : max
                  ).ticker}
                </p>
                <p className="text-white/60 text-sm">
                  {formatCurrency(Math.max(...compare.data.map(c => c.revenue_ttm || 0)))}
                </p>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <h3 className="text-white/70 text-sm mb-2">Best FCF Margin</h3>
                <p className="text-2xl font-bold text-blue-400">
                  {compare.data.reduce((max, company) => 
                    (company.fcf_margin_ttm || 0) > (max.fcf_margin_ttm || 0) ? company : max
                  ).ticker}
                </p>
                <p className="text-white/60 text-sm">
                  {formatPercent(Math.max(...compare.data.map(c => c.fcf_margin_ttm || 0)))}
                </p>
              </div>
            </div>

            {/* Comparison Table */}
            <div className="bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 overflow-hidden">
              <div className="px-6 py-4 border-b border-white/20">
                <h3 className="text-xl font-semibold text-white">📊 TTM Metrics Comparison</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-white/5">
                    <tr>
                      <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Company</th>
                      <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Revenue TTM</th>
                      <th className="px-6 py-4 text-left text-sm font-medium text-white/70">FCF Margin</th>
                      <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Operating Margin</th>
                      <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Revenue Growth</th>
                      <th className="px-6 py-4 text-left text-sm font-medium text-white/70">FCF Growth</th>
                      <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Debt/Cash</th>
                      <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compare.data.map((company, index) => (
                      <tr key={company.ticker} className="border-b border-white/10 hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div 
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: COLORS[index % COLORS.length] }}
                            />
                            <div>
                              <div className="font-medium text-white">{company.ticker}</div>
                              {company.insufficient_data && (
                                <span className="text-xs text-yellow-400">⚠️ Limited Data</span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-white font-medium">
                          {formatCurrency(company.revenue_ttm)}
                        </td>
                        <td className="px-6 py-4 text-white">
                          {formatPercent(company.fcf_margin_ttm)}
                        </td>
                        <td className="px-6 py-4 text-white">
                          {formatPercent(company.operating_margin_ttm)}
                        </td>
                        <td className="px-6 py-4">
                          <div className={`flex items-center gap-1 ${
                            company.revenue_growth_yoy && company.revenue_growth_yoy > 0 
                              ? 'text-green-400' 
                              : 'text-red-400'
                          }`}>
                            {company.revenue_growth_yoy && company.revenue_growth_yoy > 0 ? (
                              <span className="h-4 w-4">↑</span>
                            ) : (
                              <ArrowTrendingDownIcon className="h-4 w-4" />
                            )}
                            {formatPercent(company.revenue_growth_yoy)}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className={`flex items-center gap-1 ${
                            company.fcf_growth_yoy && company.fcf_growth_yoy > 0 
                              ? 'text-green-400' 
                              : 'text-red-400'
                          }`}>
                            {company.fcf_growth_yoy && company.fcf_growth_yoy > 0 ? (
                              <ArrowTrendingDownIcon className="h-4 w-4" />
                            ) : (
                              <ArrowTrendingDownIcon className="h-4 w-4" />
                            )}
                            {formatPercent(company.fcf_growth_yoy)}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-white">
                          {company.debt_to_cash ? company.debt_to_cash.toFixed(2) : 'N/A'}
                        </td>
                        <td className="px-6 py-4">
                          <Link 
                            href={`/fundamentals/${company.ticker}`}
                            className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
                          >
                            View Details →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Margin Comparison Chart */}
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  📈 TTM Margins Comparison
                </h3>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={prepareChartData(compare.data)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="ticker" stroke="rgba(255,255,255,0.7)" />
                      <YAxis stroke="rgba(255,255,255,0.7)" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'rgba(0,0,0,0.9)', 
                          border: '1px solid rgba(255,255,255,0.2)', 
                          borderRadius: '8px',
                          color: 'white'
                        }}
                        formatter={(value: number, name: string) => [
                          `${value?.toFixed(1)}%`, 
                          name === 'fcf_margin_ttm' ? 'FCF Margin' : 'Operating Margin'
                        ]} 
                      />
                      <Legend />
                      <Bar dataKey="fcf_margin_ttm" fill="#3B82F6" name="FCF Margin %" radius={[2, 2, 0, 0]} />
                      <Bar dataKey="operating_margin_ttm" fill="#10B981" name="Operating Margin %" radius={[2, 2, 0, 0]} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Revenue Size Comparison */}
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  💰 Revenue TTM Comparison
                </h3>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={prepareChartData(compare.data)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="ticker" stroke="rgba(255,255,255,0.7)" />
                      <YAxis stroke="rgba(255,255,255,0.7)" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'rgba(0,0,0,0.9)', 
                          border: '1px solid rgba(255,255,255,0.2)', 
                          borderRadius: '8px',
                          color: 'white'
                        }}
                        formatter={(value: number) => [`$${value?.toFixed(1)}B`, 'Revenue TTM']} 
                      />
                      <Bar dataKey="revenue_ttm" fill="#8B5CF6" name="Revenue TTM ($B)" radius={[4, 4, 0, 0]} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
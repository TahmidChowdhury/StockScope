'use client'

import { useState } from 'react'
import { useScreener } from '@/hooks/useFundamentals'
import { FunnelIcon, ArrowLeftIcon, MagnifyingGlassIcon, ChartBarIcon } from '@heroicons/react/24/outline'
import Link from 'next/link'

interface FilterState {
  min_revenue_growth_yoy: number | undefined
  min_fcf_growth_yoy: number | undefined
  min_margin_growth_yoy_pp: number | undefined
  min_ebitda_growth_yoy: number | undefined
  max_debt_to_cash: number | undefined
  sort_by: string
  sort_dir: 'asc' | 'desc'
  limit: number
}

export default function ScreenerPage() {
  const [filters, setFilters] = useState<FilterState>({
    min_revenue_growth_yoy: undefined,
    min_fcf_growth_yoy: undefined,
    min_margin_growth_yoy_pp: undefined,
    min_ebitda_growth_yoy: undefined,
    max_debt_to_cash: undefined,
    sort_by: 'revenue_growth_yoy',
    sort_dir: 'desc',
    limit: 50
  })

  const [useTestUniverse, setUseTestUniverse] = useState(false)

  const screener = useScreener()

  const handleFilterChange = (key: keyof FilterState, value: string | number | undefined) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const handleScreen = () => {
    const request = {
      ...filters,
      // Convert empty strings to undefined
      min_revenue_growth_yoy: filters.min_revenue_growth_yoy || undefined,
      min_fcf_growth_yoy: filters.min_fcf_growth_yoy || undefined,
      min_margin_growth_yoy_pp: filters.min_margin_growth_yoy_pp || undefined,
      min_ebitda_growth_yoy: filters.min_ebitda_growth_yoy || undefined,
      max_debt_to_cash: filters.max_debt_to_cash || undefined,
      // Add test universe if enabled
      universe: useTestUniverse ? ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'ADBE', 'CRM'] : undefined
    }
    screener.mutate(request)
  }

  const clearFilters = () => {
    setFilters({
      min_revenue_growth_yoy: undefined,
      min_fcf_growth_yoy: undefined,
      min_margin_growth_yoy_pp: undefined,
      min_ebitda_growth_yoy: undefined,
      max_debt_to_cash: undefined,
      sort_by: 'revenue_growth_yoy',
      sort_dir: 'desc',
      limit: 50
    })
  }

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || isNaN(value)) return 'N/A'
    return new Intl.NumberFormat('en-US', { 
      style: 'percent', 
      maximumFractionDigits: 1 
    }).format(value)
  }

  const formatCurrency = (value: number | null | undefined, compact = true) => {
    if (value === null || value === undefined || isNaN(value)) return 'N/A'
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

  const formatNumber = (value: number | null | undefined, decimals = 2) => {
    if (value === null || value === undefined || isNaN(value)) return 'N/A'
    return value.toFixed(decimals)
  }

  const getChangeColor = (value: number | null | undefined) => {
    if (value === null || value === undefined || isNaN(value)) return 'text-white/60'
    return value > 0 ? 'text-green-400' : value < 0 ? 'text-red-400' : 'text-white/60'
  }

  const sortOptions = [
    { value: 'revenue_growth_yoy', label: 'Revenue Growth YoY' },
    { value: 'fcf_growth_yoy', label: 'FCF Growth YoY' },
    { value: 'ebitda_growth_yoy', label: 'EBITDA Growth YoY' },
    { value: 'fcf_margin_ttm', label: 'FCF Margin TTM' },
    { value: 'operating_margin_ttm', label: 'Operating Margin TTM' },
    { value: 'revenue_ttm', label: 'Revenue TTM' }
  ]

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
              <h1 className="text-4xl font-bold text-white">🔍 Stock Screener</h1>
              <p className="text-white/70">Filter stocks by financial criteria and performance</p>
            </div>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
            <MagnifyingGlassIcon className="h-8 w-8 text-white/70" />
          </div>
        </div>

        {/* Filter Panel */}
        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20 mb-8">
          <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
            <FunnelIcon className="h-5 w-5" />
            Screening Criteria
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {/* Revenue Growth Filter */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                💰 Min Revenue Growth YoY (%)
              </label>
              <input
                type="number"
                step="0.01"
                value={filters.min_revenue_growth_yoy ? (filters.min_revenue_growth_yoy * 100) : ''}
                onChange={(e) => handleFilterChange('min_revenue_growth_yoy', 
                  e.target.value ? parseFloat(e.target.value) / 100 : undefined)}
                placeholder="e.g., 10 for 10%"
                className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
              />
            </div>

            {/* FCF Growth Filter */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                💸 Min FCF Growth YoY (%)
              </label>
              <input
                type="number"
                step="0.01"
                value={filters.min_fcf_growth_yoy ? (filters.min_fcf_growth_yoy * 100) : ''}
                onChange={(e) => handleFilterChange('min_fcf_growth_yoy', 
                  e.target.value ? parseFloat(e.target.value) / 100 : undefined)}
                placeholder="e.g., 15 for 15%"
                className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
              />
            </div>

            {/* Margin Growth Filter */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                📈 Min Margin Growth YoY (pp)
              </label>
              <input
                type="number"
                step="0.1"
                value={filters.min_margin_growth_yoy_pp ? (filters.min_margin_growth_yoy_pp * 100) : ''}
                onChange={(e) => handleFilterChange('min_margin_growth_yoy_pp', 
                  e.target.value ? parseFloat(e.target.value) / 100 : undefined)}
                placeholder="e.g., 1.0 for 1pp"
                className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
              />
            </div>

            {/* EBITDA Growth Filter */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                📊 Min EBITDA Growth YoY (%)
              </label>
              <input
                type="number"
                step="0.01"
                value={filters.min_ebitda_growth_yoy ? (filters.min_ebitda_growth_yoy * 100) : ''}
                onChange={(e) => handleFilterChange('min_ebitda_growth_yoy', 
                  e.target.value ? parseFloat(e.target.value) / 100 : undefined)}
                placeholder="e.g., 12 for 12%"
                className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
              />
            </div>

            {/* Debt to Cash Filter */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                🏦 Max Debt/Cash Ratio
              </label>
              <input
                type="number"
                step="0.1"
                value={filters.max_debt_to_cash || ''}
                onChange={(e) => handleFilterChange('max_debt_to_cash', 
                  e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="e.g., 2.0"
                className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
              />
            </div>

            {/* Results Limit */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                🎯 Max Results
              </label>
              <select
                value={filters.limit}
                onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
                className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
              >
                <option value={25} className="bg-slate-800">25</option>
                <option value={50} className="bg-slate-800">50</option>
                <option value={100} className="bg-slate-800">100</option>
              </select>
            </div>
          </div>

          {/* Sort Options */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                📊 Sort By
              </label>
              <select
                value={filters.sort_by}
                onChange={(e) => handleFilterChange('sort_by', e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
              >
                {sortOptions.map(option => (
                  <option key={option.value} value={option.value} className="bg-slate-800">
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">
                ⚡ Sort Direction
              </label>
              <select
                value={filters.sort_dir}
                onChange={(e) => handleFilterChange('sort_dir', e.target.value as 'asc' | 'desc')}
                className="w-full px-4 py-3 bg-white/10 border border-white/30 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
              >
                <option value="desc" className="bg-slate-800">Highest First</option>
                <option value="asc" className="bg-slate-800">Lowest First</option>
              </select>
            </div>
          </div>

          {/* Test Universe Option */}
          <div className="flex items-center gap-2 mb-8">
            <input
              type="checkbox"
              checked={useTestUniverse}
              onChange={(e) => setUseTestUniverse(e.target.checked)}
              className="h-4 w-4 text-blue-600 bg-white/10 border-white/30 rounded focus:ring-blue-500"
            />
            <label className="text-sm font-medium text-white/70">
              Use Test Universe (AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META, NFLX, ADBE, CRM)
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              onClick={handleScreen}
              disabled={screener.isPending}
              className="px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {screener.isPending ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Screening...
                </>
              ) : (
                <>
                  <MagnifyingGlassIcon className="h-4 w-4" />
                  🔍 Run Screen
                </>
              )}
            </button>
            
            <button
              onClick={clearFilters}
              className="px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/30 text-white rounded-lg transition-colors font-medium backdrop-blur-sm"
            >
              Clear All
            </button>
          </div>
        </div>

        {/* Loading State */}
        {screener.isPending && (
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-8 border border-white/20 text-center">
            <div className="h-12 w-12 animate-spin rounded-full border-2 border-white/30 border-t-white mx-auto mb-4" />
            <p className="text-white text-lg">Screening companies with your criteria...</p>
            <p className="text-white/60 text-sm mt-2">This may take a moment</p>
          </div>
        )}

        {/* Error State */}
        {screener.isError && (
          <div className="bg-red-500/20 backdrop-blur-sm rounded-xl p-6 border border-red-500/50 mb-8">
            <h3 className="text-red-300 font-medium text-lg mb-2">⚠️ Screening Failed</h3>
            <p className="text-red-200">{screener.error?.message}</p>
          </div>
        )}

        {/* Results */}
        {screener.data && (
          <div className="space-y-6">
            {/* Results Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <div className="flex items-center gap-3">
                  <ChartBarIcon className="h-8 w-8 text-blue-400" />
                  <div>
                    <h3 className="text-2xl font-bold text-white">{screener.data.results.length}</h3>
                    <p className="text-white/70 text-sm">Companies Found</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <div className="flex items-center gap-3">
                  <MagnifyingGlassIcon className="h-8 w-8 text-green-400" />
                  <div>
                    <h3 className="text-2xl font-bold text-white">{screener.data.total_screened}</h3>
                    <p className="text-white/70 text-sm">Total Screened</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <div className="flex items-center gap-3">
                  <FunnelIcon className="h-8 w-8 text-purple-400" />
                  <div>
                    <h3 className="text-2xl font-bold text-white">
                      {screener.data.total_screened > 0 ? 
                        `${((screener.data.results.length / screener.data.total_screened) * 100).toFixed(1)}%` : '0%'}
                    </h3>
                    <p className="text-white/70 text-sm">Pass Rate</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Sort Information */}
            <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
              <p className="text-white/80 text-sm text-center">
                📊 Sorted by <span className="font-medium text-white">{sortOptions.find(opt => opt.value === filters.sort_by)?.label}</span> 
                {' '}({filters.sort_dir === 'desc' ? 'Highest to Lowest' : 'Lowest to Highest'})
              </p>
            </div>

            {/* Results Table */}
            {screener.data.results.length > 0 ? (
              <div className="bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 overflow-hidden">
                <div className="px-6 py-4 border-b border-white/20">
                  <h3 className="text-xl font-semibold text-white">🏆 Screening Results</h3>
                </div>
                
                {/* Desktop Table */}
                <div className="hidden lg:block overflow-x-auto">
                  <table className="min-w-full">
                    <thead className="bg-white/5">
                      <tr>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Ticker</th>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Revenue TTM</th>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Rev Growth</th>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">FCF Margin</th>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">FCF Growth</th>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Op Margin</th>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">EBITDA Growth</th>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Debt/Cash</th>
                        <th className="px-6 py-4 text-left text-sm font-medium text-white/70">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {screener.data.results.map((company) => (
                        <tr key={company.ticker} className="border-b border-white/10 hover:bg-white/5 transition-colors">
                          <td className="px-6 py-4">
                            <div className="font-medium text-white">{company.ticker}</div>
                          </td>
                          <td className="px-6 py-4 text-white font-medium">
                            {formatCurrency(company.revenue_ttm)}
                          </td>
                          <td className="px-6 py-4">
                            <div className={`font-medium ${getChangeColor(company.revenue_growth_yoy)}`}>
                              {formatPercent(company.revenue_growth_yoy)}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-white font-medium">
                            {formatPercent(company.fcf_margin_ttm)}
                          </td>
                          <td className="px-6 py-4">
                            <div className={`font-medium ${getChangeColor(company.fcf_growth_yoy)}`}>
                              {formatPercent(company.fcf_growth_yoy)}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-white font-medium">
                            {formatPercent(company.operating_margin_ttm)}
                          </td>
                          <td className="px-6 py-4">
                            <div className={`font-medium ${getChangeColor(company.ebitda_growth_yoy)}`}>
                              {formatPercent(company.ebitda_growth_yoy)}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-white font-medium">
                            {formatNumber(company.debt_to_cash)}
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
                
                {/* Mobile Card View */}
                <div className="lg:hidden space-y-4 p-4">
                  {screener.data.results.map((company, index) => (
                    <div key={company.ticker} className="bg-white/5 rounded-lg p-4 space-y-3">
                      <div className="flex justify-between items-center">
                        <h4 className="text-lg font-bold text-white">{company.ticker}</h4>
                        <Link 
                          href={`/fundamentals/${company.ticker}`}
                          className="text-blue-400 text-sm font-medium"
                        >
                          View →
                        </Link>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className="text-white/60">Revenue TTM:</span>
                          <span className="text-white font-medium ml-2">{formatCurrency(company.revenue_ttm)}</span>
                        </div>
                        <div>
                          <span className="text-white/60">FCF Margin:</span>
                          <span className="text-white font-medium ml-2">{formatPercent(company.fcf_margin_ttm)}</span>
                        </div>
                        <div>
                          <span className="text-white/60">Op Margin:</span>
                          <span className="text-white font-medium ml-2">{formatPercent(company.operating_margin_ttm)}</span>
                        </div>
                        <div>
                          <span className="text-white/60">Debt/Cash:</span>
                          <span className="text-white font-medium ml-2">{formatNumber(company.debt_to_cash)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-12 text-center border border-white/20">
                <FunnelIcon className="h-16 w-16 text-white/50 mx-auto mb-4" />
                <h3 className="text-xl font-medium text-white mb-2">No Companies Match Your Filters</h3>
                <p className="text-white/60 mb-6">Try adjusting your criteria or clearing some filters to see more results.</p>
                <button
                  onClick={clearFilters}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
                >
                  Reset Filters
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
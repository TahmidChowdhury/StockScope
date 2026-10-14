'use client'

import { apiFetch } from '@/lib/api'

import { useState, useEffect, useRef, useCallback } from 'react'
import { TrendingUp, DollarSign, BarChart3, Building2, ChevronDown, ChevronUp, RefreshCw, Info } from 'lucide-react'

interface KeyMetrics {
  currentPrice: number | null
  marketCap: number | null
  peRatio: number | null
  dividendYield: number | null
  dayRange: { low: number | null; high: number | null }
  fiftyTwoWeekRange: { low: number | null; high: number | null }
  volume: number | null
  averageVolume: number | null
  beta: number | null
  eps: number | null
  priceToBook: number | null
  priceToSales: number | null
  currency: string | null
  quoteAsOf: string | null
  retrievedAt: string | null
}

const observedNumber = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null

const formatTimestamp = (value: string | null) => {
  if (!value) return 'Unavailable'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? 'Unavailable' : parsed.toLocaleString()
}

interface KeyMetricsProps {
  symbol: string
  className?: string
}

export default function KeyMetricsComponent({ symbol, className = '' }: KeyMetricsProps) {
  const [metrics, setMetrics] = useState<KeyMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [expandedSection, setExpandedSection] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [showTooltip, setShowTooltip] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const fetchMetrics = useCallback(async (refreshing = false) => {
    if (!refreshing) setLoading(true)
    setError(null)

    try {
      const response = await apiFetch(`/api/stocks/${symbol}/info`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch key metrics')
      }
      
      const data = await response.json()
      
      setMetrics({
        currentPrice: observedNumber(data.currentPrice),
        marketCap: observedNumber(data.marketCap),
        peRatio: observedNumber(data.priceToEarningsRatio),
        dividendYield: observedNumber(data.dividendYield),
        dayRange: {
          low: observedNumber(data.dayLow),
          high: observedNumber(data.dayHigh)
        },
        fiftyTwoWeekRange: {
          low: observedNumber(data.fiftyTwoWeekLow),
          high: observedNumber(data.fiftyTwoWeekHigh)
        },
        volume: observedNumber(data.volume),
        averageVolume: observedNumber(data.averageVolume),
        beta: observedNumber(data.beta),
        eps: observedNumber(data.earningsPerShare),
        priceToBook: observedNumber(data.priceToBook),
        priceToSales: observedNumber(data.priceToSalesTrailing12Months),
        currency: typeof data.currency === 'string' && /^[A-Z]{3}$/.test(data.currency) ? data.currency : null,
        quoteAsOf: typeof data.quote_as_of === 'string' ? data.quote_as_of : null,
        retrievedAt: typeof data.retrieved_at === 'string' ? data.retrieved_at : null
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [symbol])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await fetchMetrics(true)
    } finally {
      setIsRefreshing(false)
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section)
  }

  useEffect(() => {
    if (symbol) {
      fetchMetrics()
    }
  }, [symbol, fetchMetrics])

  const formatPrice = (price: number | null, compact = false) => {
    if (price === null) return 'Unavailable'
    return new Intl.NumberFormat('en-US', {
      ...(metrics?.currency ? { style: 'currency', currency: metrics.currency } : { style: 'decimal' }),
      notation: compact ? 'compact' : 'standard',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price)
  }

  const formatLargeNumber = (num: number | null) => formatPrice(num, true)

  const formatVolume = (volume: number | null) => {
    if (volume === null) return 'Unavailable'
    if (volume >= 1e9) {
      return `${(volume / 1e9).toFixed(2)}B`
    } else if (volume >= 1e6) {
      return `${(volume / 1e6).toFixed(2)}M`
    } else if (volume >= 1e3) {
      return `${(volume / 1e3).toFixed(2)}K`
    }
    return volume.toString()
  }

  const formatPercent = (value: number | null) => {
    if (value === null) return 'Unavailable'
    return `${(value * 100).toFixed(2)}%`
  }

  const formatRatio = (value: number | null) => {
    if (value === null) return 'Unavailable'
    return value.toFixed(2)
  }

  const formatRange = (range: { low: number | null; high: number | null }) =>
    range.low === null || range.high === null
      ? 'Unavailable'
      : `${formatPrice(range.low)} – ${formatPrice(range.high)}`

  if (loading) {
    return (
      <div className={`bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 p-3 sm:p-6 ${className}`}>
        <div className="flex items-center space-x-2 mb-4">
          <BarChart3 className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Key Metrics</h3>
        </div>
        
        {/* Mobile Loading - Horizontal cards */}
        <div className="lg:hidden">
          <div className="flex space-x-3 overflow-x-auto pb-2 mb-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white/5 rounded-lg p-3 min-w-[120px] animate-pulse">
                <div className="h-3 bg-white/10 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-white/10 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Desktop Loading */}
        <div className="hidden lg:block space-y-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="animate-pulse flex justify-between">
              <div className="h-4 bg-white/10 rounded w-1/2"></div>
              <div className="h-4 bg-white/10 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 p-3 sm:p-6 ${className}`}>
        <div className="flex items-center space-x-2 mb-4">
          <BarChart3 className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Key Metrics</h3>
        </div>
        <div className="text-center text-red-400 py-6">
          <p className="text-sm sm:text-base">Error loading metrics: {error}</p>
          <button
            onClick={handleRefresh}
            className="mt-3 px-4 py-2 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 rounded-lg text-white text-sm transition-colors touch-manipulation"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!metrics) return null

  // Group metrics for mobile sections
  const metricSections = {
    price: {
      title: 'Price & Valuation',
      icon: DollarSign,
      metrics: [
        { label: 'Quote Price', value: formatPrice(metrics.currentPrice), tooltip: 'Latest price returned by the provider; see quote time below' },
        { label: 'Market Cap', value: formatLargeNumber(metrics.marketCap), tooltip: 'Total market value of company' },
        { label: 'P/E Ratio', value: formatRatio(metrics.peRatio), tooltip: 'Price-to-Earnings ratio' },
        { label: 'P/B Ratio', value: formatRatio(metrics.priceToBook), tooltip: 'Price-to-Book ratio' },
        { label: 'P/S Ratio', value: formatRatio(metrics.priceToSales), tooltip: 'Price-to-Sales ratio' }
      ]
    },
    trading: {
      title: 'Trading & Performance',
      icon: TrendingUp,
      metrics: [
        { label: 'Day Range', value: formatRange(metrics.dayRange), tooltip: 'Price range for the provider’s reported trading session' },
        { label: '52W Range', value: formatRange(metrics.fiftyTwoWeekRange), tooltip: '52-week price range' },
        { label: 'Volume', value: formatVolume(metrics.volume), tooltip: 'Trading volume for the provider’s reported session' },
        { label: 'Avg Volume', value: formatVolume(metrics.averageVolume), tooltip: 'Average daily volume' },
        { label: 'Beta', value: formatRatio(metrics.beta), tooltip: 'Stock volatility vs market' }
      ]
    },
    fundamentals: {
      title: 'Fundamentals',
      icon: Building2,
      metrics: [
        { label: 'EPS', value: formatPrice(metrics.eps), tooltip: 'Earnings per share' },
        { label: 'Dividend Yield', value: formatPercent(metrics.dividendYield), tooltip: 'Annual dividend yield' }
      ]
    }
  }

  // Quick stats for horizontal scroll on mobile
  const quickStats = [
    { label: 'Price', value: formatPrice(metrics.currentPrice), change: null },
    { label: 'Market Cap', value: formatLargeNumber(metrics.marketCap), change: null },
    { label: 'P/E', value: formatRatio(metrics.peRatio), change: null },
    { label: 'Volume', value: formatVolume(metrics.volume), change: null },
    { label: 'Beta', value: formatRatio(metrics.beta), change: null },
    { label: 'Dividend', value: formatPercent(metrics.dividendYield), change: null }
  ]

  return (
    <div className={`bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 p-3 sm:p-6 ${className}`}>
      {/* Header with refresh */}
      <div className="flex items-center justify-between mb-4 sm:mb-6">
        <div className="flex items-center space-x-2">
          <BarChart3 className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Key Metrics</h3>
          <span className="hidden sm:inline text-sm text-white/60">for {symbol}</span>
        </div>
        
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="p-2 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-white transition-all disabled:opacity-50 touch-manipulation"
          title="Reload metrics (provider responses may be cached for up to one hour)"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Mobile: Horizontal scroll quick stats */}
      <div className="lg:hidden mb-6">
        <div 
          ref={scrollRef}
          className="flex space-x-3 overflow-x-auto pb-3 snap-x snap-mandatory"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {quickStats.map((stat, index) => (
            <div key={index} className="bg-white/5 rounded-lg p-3 min-w-[100px] sm:min-w-[120px] text-center snap-start border border-white/10 hover:bg-white/10 transition-colors">
              <p className="text-xs text-white/60 mb-1 truncate">{stat.label}</p>
              <p className="text-sm sm:text-base font-semibold text-white truncate">{stat.value}</p>
            </div>
          ))}
        </div>
        
        {/* Scroll indicator */}
        <div className="flex justify-center space-x-1 mb-4">
          {Array.from({ length: Math.ceil(quickStats.length / 3) }).map((_, i) => (
            <div key={i} className="w-1.5 h-1.5 rounded-full bg-white/20"></div>
          ))}
        </div>

        {/* Expandable sections */}
        <div className="space-y-3">
          {Object.entries(metricSections).map(([key, section]) => {
            const IconComponent = section.icon
            const isExpanded = expandedSection === key
            
            return (
              <div key={key} className="bg-white/5 rounded-lg border border-white/10 overflow-hidden">
                <button
                  onClick={() => toggleSection(key)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-white/5 transition-colors touch-manipulation"
                >
                  <div className="flex items-center space-x-3">
                    <IconComponent className="h-4 w-4 text-purple-400" />
                    <span className="text-sm font-medium text-white">{section.title}</span>
                    <span className="text-xs text-white/60">({section.metrics.length})</span>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-white/60" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-white/60" />
                  )}
                </button>
                
                {isExpanded && (
                  <div className="px-4 pb-4 space-y-3 animate-slideDown">
                    {section.metrics.map((metric, index) => (
                      <div key={index} className="flex items-center justify-between py-2 border-b border-white/10 last:border-b-0">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-white/80">{metric.label}</span>
                          <button
                            onClick={() => setShowTooltip(showTooltip === `${key}-${index}` ? null : `${key}-${index}`)}
                            className="p-1 rounded-full hover:bg-white/10 transition-colors"
                          >
                            <Info className="h-3 w-3 text-white/40" />
                          </button>
                        </div>
                        <span className="text-sm font-semibold text-white">{metric.value}</span>
                        
                        {/* Tooltip */}
                        {showTooltip === `${key}-${index}` && (
                          <div className="absolute right-4 bg-slate-900/95 backdrop-blur-sm border border-white/20 rounded-lg p-2 max-w-48 z-10">
                            <p className="text-xs text-white">{metric.tooltip}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Desktop: Traditional layout */}
      <div className="hidden lg:block space-y-4">
        {Object.values(metricSections).flatMap(section => section.metrics).map((metric, index) => (
          <div key={index} className="flex items-center justify-between py-2 border-b border-white/20 last:border-b-0 hover:bg-white/5 transition-colors rounded px-2">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-white/80">{metric.label}</span>
            </div>
            <span className="text-sm font-semibold text-white">{metric.value}</span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-white/20">
        <div className="text-center">
          <p className="text-xs text-white/60">
            Quote as of: {formatTimestamp(metrics.quoteAsOf)}
          </p>
          <p className="text-xs text-white/60 mt-1">
            Retrieved: {formatTimestamp(metrics.retrievedAt)}
          </p>
          <p className="text-xs text-white/60 mt-1">
            Provider data may be delayed; responses are cached for up to one hour.
            {!metrics.currency && ' Currency unavailable.'}
          </p>
        </div>
      </div>
    </div>
  )
}
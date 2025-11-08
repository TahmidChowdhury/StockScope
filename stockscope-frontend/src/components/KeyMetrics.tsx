'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { TrendingUp, DollarSign, BarChart3, Building2, ChevronDown, ChevronUp, RefreshCw, Info } from 'lucide-react'

interface KeyMetrics {
  currentPrice: number
  marketCap: number
  peRatio: number
  dividendYield: number
  dayRange: {
    low: number
    high: number
  }
  fiftyTwoWeekRange: {
    low: number
    high: number
  }
  volume: number
  averageVolume: number
  beta: number
  eps: number
  priceToBook: number
  priceToSales: number
}

interface KeyMetricsProps {
  symbol: string
  className?: string
}

export default function KeyMetricsComponent({ symbol, className = '' }: KeyMetricsProps) {
  const [metrics, setMetrics] = useState<KeyMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const getPasswordParam = () => {
    const password = localStorage.getItem('stockscope_password')
    return password ? `?password=${encodeURIComponent(password)}` : ''
  }

  const [expandedSection, setExpandedSection] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [showTooltip, setShowTooltip] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const fetchMetrics = useCallback(async () => {
    if (!isRefreshing) setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/info${getPasswordParam()}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch key metrics')
      }
      
      const data = await response.json()
      
      setMetrics({
        currentPrice: data.currentPrice || 0,
        marketCap: data.marketCap || 0,
        peRatio: data.priceToEarningsRatio || 0,
        dividendYield: data.dividendYield || 0,
        dayRange: {
          low: data.dayLow || 0,
          high: data.dayHigh || 0
        },
        fiftyTwoWeekRange: {
          low: data.fiftyTwoWeekLow || 0,
          high: data.fiftyTwoWeekHigh || 0
        },
        volume: data.volume || 0,
        averageVolume: data.averageVolume || 0,
        beta: data.beta || 0,
        eps: data.earningsPerShare || 0,
        priceToBook: data.priceToBook || 0,
        priceToSales: data.priceToSalesTrailing12Months || 0
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      if (!isRefreshing) setLoading(false)
    }
  }, [symbol, isRefreshing, API_BASE_URL])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await fetchMetrics()
    setTimeout(() => setIsRefreshing(false), 500)
  }

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section)
  }

  useEffect(() => {
    if (symbol) {
      fetchMetrics()
    }
  }, [symbol, fetchMetrics])

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price)
  }

  const formatLargeNumber = (num: number) => {
    if (num >= 1e12) {
      return `$${(num / 1e12).toFixed(2)}T`
    } else if (num >= 1e9) {
      return `$${(num / 1e9).toFixed(2)}B`
    } else if (num >= 1e6) {
      return `$${(num / 1e6).toFixed(2)}M`
    } else if (num >= 1e3) {
      return `$${(num / 1e3).toFixed(2)}K`
    }
    return `$${num.toFixed(2)}`
  }

  const formatVolume = (volume: number) => {
    if (volume >= 1e9) {
      return `${(volume / 1e9).toFixed(2)}B`
    } else if (volume >= 1e6) {
      return `${(volume / 1e6).toFixed(2)}M`
    } else if (volume >= 1e3) {
      return `${(volume / 1e3).toFixed(2)}K`
    }
    return volume.toString()
  }

  const formatPercent = (value: number) => {
    if (value === 0) return 'N/A'
    return `${(value * 100).toFixed(2)}%`
  }

  const formatRatio = (value: number) => {
    if (value === 0) return 'N/A'
    return value.toFixed(2)
  }

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
        { label: 'Current Price', value: formatPrice(metrics.currentPrice), tooltip: 'Current stock price' },
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
        { label: 'Day Range', value: `${formatPrice(metrics.dayRange.low)} - ${formatPrice(metrics.dayRange.high)}`, tooltip: "Today's price range" },
        { label: '52W Range', value: `${formatPrice(metrics.fiftyTwoWeekRange.low)} - ${formatPrice(metrics.fiftyTwoWeekRange.high)}`, tooltip: '52-week price range' },
        { label: 'Volume', value: formatVolume(metrics.volume), tooltip: 'Trading volume today' },
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
          title="Refresh metrics"
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
            📊 Last updated: {new Date().toLocaleTimeString()}
          </p>
        </div>
      </div>
    </div>
  )
}
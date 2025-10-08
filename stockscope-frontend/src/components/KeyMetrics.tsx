'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, DollarSign, BarChart3, Target, Building2 } from 'lucide-react'

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

  useEffect(() => {
    const fetchMetrics = async () => {
      setLoading(true)
      setError(null)

      try {
        const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/info${getPasswordParam()}`)
        
        if (!response.ok) {
          throw new Error('Failed to fetch key metrics')
        }
        
        const data = await response.json()
        
        // Transform the data to match our interface
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
        setLoading(false)
      }
    }

    if (symbol) {
      fetchMetrics()
    }
  }, [symbol])

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
      <div className={`bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 p-6 ${className}`}>
        <div className="flex items-center space-x-2 mb-4">
          <BarChart3 className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Key Metrics</h3>
        </div>
        <div className="space-y-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="animate-pulse flex justify-between">
              <div className="h-4 bg-slate-600 rounded w-1/2"></div>
              <div className="h-4 bg-slate-600 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 p-6 ${className}`}>
        <div className="flex items-center space-x-2 mb-4">
          <BarChart3 className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Key Metrics</h3>
        </div>
        <div className="text-center text-red-400">
          <p>Error loading metrics: {error}</p>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return null
  }

  const metricsData = [
    {
      label: 'Market Cap',
      value: formatLargeNumber(metrics.marketCap),
      icon: Building2
    },
    {
      label: 'P/E Ratio',
      value: formatRatio(metrics.peRatio),
      icon: Target
    },
    {
      label: 'Dividend Yield',
      value: formatPercent(metrics.dividendYield),
      icon: DollarSign
    },
    {
      label: 'Day Range',
      value: `${formatPrice(metrics.dayRange.low)} - ${formatPrice(metrics.dayRange.high)}`,
      icon: TrendingUp
    },
    {
      label: '52W Range',
      value: `${formatPrice(metrics.fiftyTwoWeekRange.low)} - ${formatPrice(metrics.fiftyTwoWeekRange.high)}`,
      icon: TrendingUp
    },
    {
      label: 'Volume',
      value: formatVolume(metrics.volume),
      icon: BarChart3
    },
    {
      label: 'Avg Volume',
      value: formatVolume(metrics.averageVolume),
      icon: BarChart3
    },
    {
      label: 'Beta',
      value: formatRatio(metrics.beta),
      icon: Target
    },
    {
      label: 'EPS',
      value: formatPrice(metrics.eps),
      icon: DollarSign
    },
    {
      label: 'P/B Ratio',
      value: formatRatio(metrics.priceToBook),
      icon: Target
    },
    {
      label: 'P/S Ratio',
      value: formatRatio(metrics.priceToSales),
      icon: Target
    }
  ]

  return (
    <div className={`bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 p-6 ${className}`}>
      <div className="flex items-center space-x-2 mb-6">
        <BarChart3 className="h-5 w-5 text-purple-400" />
        <h3 className="text-lg font-semibold text-white">Key Metrics</h3>
      </div>

      <div className="space-y-4">
        {metricsData.map((metric, index) => {
          const IconComponent = metric.icon
          return (
            <div key={index} className="flex items-center justify-between py-2 border-b border-slate-600 last:border-b-0">
              <div className="flex items-center space-x-2">
                <IconComponent className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-300">{metric.label}</span>
              </div>
              <span className="text-sm font-semibold text-white">
                {metric.value}
              </span>
            </div>
          )
        })}
      </div>

      {/* Summary section */}
      <div className="mt-6 pt-4 border-t border-slate-600">
        <div className="text-center">
          <p className="text-xs text-gray-300">
            Current Price: <span className="font-semibold text-white">{formatPrice(metrics.currentPrice)}</span>
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Data updated in real-time
          </p>
        </div>
      </div>
    </div>
  )
}
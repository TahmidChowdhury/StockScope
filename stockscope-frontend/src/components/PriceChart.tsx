'use client'

import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface PriceData {
  date: string
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface PriceHistoryResponse {
  symbol: string
  period: string
  interval: string
  currentPrice: number
  priceChange: number
  priceChangePercent: number
  data: PriceData[]
}

interface PriceChartProps {
  symbol: string
  className?: string
}

const PERIOD_OPTIONS = [
  { value: '1d', label: '1D' },
  { value: '5d', label: '5D' },
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '2y', label: '2Y' },
  { value: '5y', label: '5Y' }
]

export default function PriceChart({ symbol, className = '' }: PriceChartProps) {
  const [priceData, setPriceData] = useState<PriceHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState('1y')

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const getPasswordParam = () => {
    const password = localStorage.getItem('stockscope_password')
    return password ? `?password=${encodeURIComponent(password)}` : ''
  }

  const fetchPriceData = async (period: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/stocks/${symbol}/price-history?period=${period}&interval=1d${getPasswordParam() ? '&' + getPasswordParam().slice(1) : ''}`
      )
      
      if (!response.ok) {
        throw new Error('Failed to fetch price data')
      }
      
      const data = await response.json()
      setPriceData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (symbol) {
      fetchPriceData(selectedPeriod)
    }
  }, [symbol, selectedPeriod])

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    })
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-slate-900/95 backdrop-blur-sm p-3 rounded-lg shadow-lg border border-white/20">
          <p className="font-semibold text-white">{formatDate(label)}</p>
          <p className="text-green-400">Close: {formatPrice(data.close)}</p>
          <p className="text-gray-300">Volume: {data.volume.toLocaleString()}</p>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <div className={`bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 p-4 sm:p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-white/10 rounded w-1/4 mb-4"></div>
          <div className="h-48 sm:h-64 bg-white/10 rounded"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 p-4 sm:p-6 ${className}`}>
        <div className="text-center text-red-400">
          <p>Error loading price chart: {error}</p>
        </div>
      </div>
    )
  }

  if (!priceData) {
    return null
  }

  const isPositive = priceData.priceChange >= 0
  const chartColor = isPositive ? '#10B981' : '#EF4444'

  return (
    <div className={`bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 p-3 sm:p-6 ${className}`}>
      {/* Header with current price - Mobile optimized */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4 sm:mb-6">
        <div className="min-w-0">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-1 truncate">
            {symbol} Stock Price
          </h3>
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <span className="text-xl sm:text-2xl font-bold text-white">
              {formatPrice(priceData.currentPrice)}
            </span>
            <div className={`flex items-center gap-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? (
                <TrendingUp className="h-3 w-3 sm:h-4 sm:w-4" />
              ) : (
                <TrendingDown className="h-3 w-3 sm:h-4 sm:w-4" />
              )}
              <span className="text-sm sm:text-base font-semibold">
                {formatPrice(Math.abs(priceData.priceChange))} ({Math.abs(priceData.priceChangePercent).toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Period selector - Better mobile layout */}
        <div className="flex-shrink-0">
          <div className="flex items-center bg-white/5 rounded-lg p-1 gap-1 overflow-x-auto">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setSelectedPeriod(option.value)}
                className={`px-2 sm:px-3 py-1.5 rounded text-xs font-medium transition-colors whitespace-nowrap min-w-[32px] ${
                  selectedPeriod === option.value
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-white/70 hover:text-white hover:bg-white/10'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart - Better mobile height */}
      <div className="h-48 sm:h-64 lg:h-80 mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={priceData.data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis 
              dataKey="date"
              tickFormatter={formatDate}
              stroke="rgba(255,255,255,0.7)"
              fontSize={window.innerWidth < 640 ? 10 : 12}
              tick={{ fill: 'rgba(255,255,255,0.7)' }}
            />
            <YAxis 
              domain={['dataMin', 'dataMax']}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
              stroke="rgba(255,255,255,0.7)"
              fontSize={window.innerWidth < 640 ? 10 : 12}
              tick={{ fill: 'rgba(255,255,255,0.7)' }}
              width={window.innerWidth < 640 ? 50 : 60}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="close"
              stroke={chartColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: window.innerWidth < 640 ? 3 : 4, fill: chartColor }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Key metrics - Better mobile grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 pt-4 border-t border-white/10">
        <div className="text-center bg-white/5 rounded-lg p-2 sm:p-3">
          <p className="text-xs text-white/60 mb-1">Period High</p>
          <p className="text-sm sm:text-base font-semibold text-white">
            {formatPrice(Math.max(...priceData.data.map(d => d.high)))}
          </p>
        </div>
        <div className="text-center bg-white/5 rounded-lg p-2 sm:p-3">
          <p className="text-xs text-white/60 mb-1">Period Low</p>
          <p className="text-sm sm:text-base font-semibold text-white">
            {formatPrice(Math.min(...priceData.data.map(d => d.low)))}
          </p>
        </div>
        <div className="text-center bg-white/5 rounded-lg p-2 sm:p-3">
          <p className="text-xs text-white/60 mb-1">Avg Volume</p>
          <p className="text-sm sm:text-base font-semibold text-white">
            {(priceData.data.reduce((sum, d) => sum + d.volume, 0) / priceData.data.length).toLocaleString(undefined, {maximumFractionDigits: 0})}
          </p>
        </div>
        <div className="text-center bg-white/5 rounded-lg p-2 sm:p-3">
          <p className="text-xs text-white/60 mb-1">Data Points</p>
          <p className="text-sm sm:text-base font-semibold text-white">{priceData.data.length}</p>
        </div>
      </div>
    </div>
  )
}
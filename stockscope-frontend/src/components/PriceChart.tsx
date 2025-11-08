'use client'

import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, Calendar } from 'lucide-react'
import { getPasswordParam } from '@/utils/auth'

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
        <div className="bg-white p-3 rounded-lg shadow-lg border">
          <p className="font-semibold">{formatDate(label)}</p>
          <p className="text-blue-600">Close: {formatPrice(data.close)}</p>
          <p className="text-gray-600">Volume: {data.volume.toLocaleString()}</p>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <div className={`bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-slate-600 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-slate-600 rounded"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 p-6 ${className}`}>
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
    <div className={`bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 p-6 ${className}`}>
      {/* Header with current price */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-white mb-1">
            {symbol} Stock Price
          </h3>
          <div className="flex items-center space-x-3">
            <span className="text-2xl font-bold text-white">
              {formatPrice(priceData.currentPrice)}
            </span>
            <div className={`flex items-center space-x-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? (
                <TrendingUp className="h-4 w-4" />
              ) : (
                <TrendingDown className="h-4 w-4" />
              )}
              <span className="font-semibold">
                {formatPrice(Math.abs(priceData.priceChange))} ({Math.abs(priceData.priceChangePercent).toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Period selector - Mobile optimized */}
        <div className="flex items-center space-x-0.5 sm:space-x-1 bg-slate-700/50 rounded-lg p-0.5 sm:p-1 overflow-x-auto">
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setSelectedPeriod(option.value)}
              className={`px-2 sm:px-3 py-1 rounded text-xs sm:text-sm font-medium transition-colors whitespace-nowrap flex-shrink-0 ${
                selectedPeriod === option.value
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={priceData.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="date"
              tickFormatter={formatDate}
              stroke="#9CA3AF"
              fontSize={12}
            />
            <YAxis 
              domain={['dataMin', 'dataMax']}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
              stroke="#9CA3AF"
              fontSize={12}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="close"
              stroke={chartColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: chartColor }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-200">
        <div className="text-center">
          <p className="text-sm text-gray-600">Period High</p>
          <p className="font-semibold">
            {formatPrice(Math.max(...priceData.data.map(d => d.high)))}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-600">Period Low</p>
          <p className="font-semibold">
            {formatPrice(Math.min(...priceData.data.map(d => d.low)))}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-600">Avg Volume</p>
          <p className="font-semibold">
            {(priceData.data.reduce((sum, d) => sum + d.volume, 0) / priceData.data.length).toLocaleString(undefined, {maximumFractionDigits: 0})}
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-600">Data Points</p>
          <p className="font-semibold">{priceData.data.length}</p>
        </div>
      </div>
    </div>
  )
}
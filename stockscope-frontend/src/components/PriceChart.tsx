'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { apiFetch, ApiError, readApiJson } from '@/lib/api'
import { priceHistorySummary, type PriceData, type PriceHistoryResponse } from '@/lib/price-history'
import { useWindowWidth } from '@/hooks/useWindowWidth'

interface PriceChartProps {
  symbol: string
  className?: string
}

const PERIOD_OPTIONS = [
  { value: '5d', label: '5D' },
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '2y', label: '2Y' },
  { value: '5y', label: '5Y' },
]

const formatPrice = (price: number | null | undefined) => {
  if (price == null || !Number.isFinite(price)) return 'Unavailable'
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(price)
}

const formatDate = (dateStr: string) => {
  // Daily bars are trading dates, not midnight instants in the viewer's timezone.
  const date = new Date(`${dateStr}T00:00:00Z`)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: PriceData }> }) {
  const data = active ? payload?.[0]?.payload : undefined
  if (!data) return null
  return (
    <div className="bg-slate-900/95 backdrop-blur-sm p-3 rounded-lg shadow-lg border border-white/20">
      <p className="font-semibold text-white">{formatDate(data.date)}</p>
      <p className="text-green-400">Close: {formatPrice(data.close)}</p>
      <p className="text-gray-300">Volume: {data.volume?.toLocaleString() ?? 'Unavailable'}</p>
    </div>
  )
}

export default function PriceChart({ symbol, className = '' }: PriceChartProps) {
  const [selectedPeriod, setSelectedPeriod] = useState('1y')
  const windowWidth = useWindowWidth()
  const query = useQuery({
    queryKey: ['price-history', symbol, selectedPeriod],
    queryFn: async ({ signal }): Promise<PriceHistoryResponse> => {
      const response = await apiFetch(
        `/api/stocks/${encodeURIComponent(symbol)}/price-history?period=${selectedPeriod}&interval=1d`,
        { signal },
      )
      return readApiJson<PriceHistoryResponse>(response, 'Price history could not be loaded.')
    },
    enabled: Boolean(symbol),
    staleTime: 60 * 60_000,
    retry: false,
    refetchOnWindowFocus: false,
    // Keep the chart's size and quote stable during range changes. Never carry
    // a previous company's prices into a new company's view.
    placeholderData: (previous, previousQuery) =>
      previousQuery?.queryKey[1] === symbol ? previous : undefined,
  })
  const limited = query.error instanceof ApiError && query.error.status === 429
  const priceData = query.data
  const bars = priceData?.data ?? []
  const summary = priceHistorySummary(bars)
  const change = priceData?.priceChange
  const changePercent = priceData?.priceChangePercent
  const chartColor = change == null || change === 0 ? '#94A3B8' : change > 0 ? '#10B981' : '#EF4444'
  const quoteDate = priceData?.quote_as_of ? new Date(priceData.quote_as_of) : null
  const quoteDateLabel = quoteDate && !Number.isNaN(quoteDate.getTime()) ? quoteDate.toLocaleString() : 'Unknown'
  const selectedLabel = PERIOD_OPTIONS.find((option) => option.value === selectedPeriod)?.label
  const displayedLabel = PERIOD_OPTIONS.find((option) => option.value === priceData?.period)?.label ?? priceData?.period
  const waiting = query.isPending || query.isPlaceholderData

  return (
    <div className={`bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 p-3 sm:p-6 ${className}`}>
      <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center sm:justify-between gap-4 mb-4 sm:mb-6">
        <div className="min-w-0">
          <h3 className="text-base sm:text-lg font-semibold text-white mb-1 truncate">{symbol} Stock Price</h3>
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <span className="text-xl sm:text-2xl font-bold text-white">
              {!priceData && query.isPending ? 'Loading quote…' : priceData?.currentPrice == null ? 'Quote unavailable' : formatPrice(priceData.currentPrice)}
            </span>
            {change != null && changePercent != null ? (
              <div className={`flex items-center gap-1 ${change === 0 ? 'text-white/60' : change > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {change > 0 ? <TrendingUp className="h-3 w-3 sm:h-4 sm:w-4" /> : change < 0 ? <TrendingDown className="h-3 w-3 sm:h-4 sm:w-4" /> : null}
                <span className="text-sm sm:text-base font-semibold">
                  {change > 0 ? '+' : ''}{formatPrice(change)} ({changePercent > 0 ? '+' : ''}{changePercent.toFixed(2)}%)
                </span>
              </div>
            ) : <span className="text-sm text-white/60">Daily change unavailable</span>}
          </div>
          <p className="mt-2 text-xs text-white/60">{priceData?.price_source || 'Price provider'} · Quote time: {quoteDateLabel}</p>
          <p className="mt-1 text-xs text-white/60">Latest chart close: {formatPrice(priceData?.lastHistoricalClose)} · {priceData?.lastHistoricalCloseDate ?? 'Date unknown'}</p>
        </div>
        <div className="min-w-0 max-w-full">
          <div role="group" aria-label="Price history period" className="flex items-center bg-white/5 rounded-lg p-1 gap-1 overflow-x-auto">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                disabled={limited} onClick={() => setSelectedPeriod(option.value)}
                aria-pressed={selectedPeriod === option.value}
                className={`min-h-11 flex-1 px-2 sm:px-3 rounded text-xs font-medium transition-colors whitespace-nowrap min-w-[36px] ${selectedPeriod === option.value ? 'bg-purple-600 text-white shadow-sm' : 'text-white/70 hover:text-white hover:bg-white/10'}`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div role="status" className="mb-2 min-h-5 text-xs text-slate-400">
        {query.fetchStatus === 'paused'
          ? query.isPlaceholderData
            ? `Waiting for a connection to load ${selectedLabel}. Showing ${displayedLabel}.`
            : `Waiting for a connection.${priceData ? ' Previously loaded prices are shown.' : ''}`
          : query.isPlaceholderData
            ? `Loading ${selectedLabel}… Showing ${displayedLabel} until it is ready.`
            : query.isFetching
              ? priceData ? 'Refreshing price history…' : 'Loading price history…'
              : null}
      </div>
      {priceData?.stale && <p role="status" className="mb-3 text-xs leading-5 text-amber-200">Showing saved prices. The provider could not be refreshed; observation dates are unchanged.</p>}
      {query.isError && (
        <div role="alert" className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-amber-200">
          <p>{query.error.message}{priceData ? ' Previously loaded prices are shown.' : ''}</p>
          <button type="button" onClick={() => void query.refetch()} disabled={query.isFetching || limited} className="button-secondary">Retry price history</button>
        </div>
      )}

      <div aria-busy={waiting} className="h-48 sm:h-64 lg:h-80 mb-4 touch-pan-y">
        {!priceData && query.isPending ? (
          <div className="h-full animate-pulse rounded-lg bg-white/5" />
        ) : bars.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={bars} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" tickFormatter={formatDate} stroke="rgba(255,255,255,0.7)" fontSize={windowWidth < 640 ? 10 : 12} tick={{ fill: 'rgba(255,255,255,0.7)' }} minTickGap={24} />
              <YAxis domain={['dataMin', 'dataMax']} tickFormatter={(value) => `$${value.toFixed(2)}`} stroke="rgba(255,255,255,0.7)" fontSize={windowWidth < 640 ? 10 : 12} tick={{ fill: 'rgba(255,255,255,0.7)' }} width={windowWidth < 640 ? 50 : 60} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="close" stroke={chartColor} strokeWidth={2} dot={false} activeDot={{ r: windowWidth < 640 ? 3 : 4, fill: chartColor }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-white/10 p-4 text-center text-sm text-slate-400">
            {query.isError ? limited ? 'Price requests are temporarily paused. Saved news and filings are still available.' : 'Price history is unavailable. Try again later.' : 'No price history is available for this period.'}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 pt-4 border-t border-white/10">
        {[
          ['Period High', formatPrice(summary.high)],
          ['Period Low', formatPrice(summary.low)],
          ['Avg Volume', summary.averageVolume == null ? 'Unavailable' : summary.averageVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })],
          ['Data Points', priceData ? bars.length.toLocaleString() : '—'],
        ].map(([label, value]) => (
          <div key={label} className="min-w-0 text-center bg-white/5 rounded-lg p-2 sm:p-3">
            <p className="text-xs text-white/60 mb-1">{label}</p>
            <p className="break-words text-sm sm:text-base font-semibold text-white">{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

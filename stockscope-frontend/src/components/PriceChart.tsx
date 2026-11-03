'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { apiFetch, ApiError, readApiJson } from '@/lib/api'
import { priceHistoryInterval, formatHistoryDate, priceHistorySummary, type PriceData, type PriceHistoryResponse } from '@/lib/price-history'
import { priceAmount as formatPrice, unitLabel } from '@/lib/financial-format'
import { usePriceCooldown, priceCooldownDeadline, rememberPriceCooldown } from '@/hooks/usePriceCooldown'
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

function CustomTooltip({ active, payload, currency, interval }: { interval?: string; currency?: string | null; active?: boolean; payload?: ReadonlyArray<{ payload?: PriceData }> }) {
  const data = active ? payload?.[0]?.payload : undefined
  if (!data) return null
  return (
    <div className="max-w-56 whitespace-normal break-words bg-[#202722] p-3 rounded-lg border border-white/10 text-xs leading-5">
      <p className="font-medium text-white">{formatHistoryDate(data.date, interval)}</p>
      <p className="text-sage-300">Close: {formatPrice(data.close, currency)}</p>
      <p className="text-gray-300">Volume: {data.volume?.toLocaleString() ?? 'Unavailable'}</p>
    </div>
  )
}

export default function PriceChart({ symbol, className = '' }: PriceChartProps) {
  const [selectedPeriod, setSelectedPeriod] = useState('1y')
  const interval = priceHistoryInterval(selectedPeriod)
  const queryKey = ['price-history', symbol, selectedPeriod, interval]
  const windowWidth = useWindowWidth()
  const client = useQueryClient()
  const { deadline, cooling } = usePriceCooldown()
  const query = useQuery({
    queryKey,
    queryFn: async ({ signal }): Promise<PriceHistoryResponse> => {
      const blockedUntil = priceCooldownDeadline(client)
      if (blockedUntil > Date.now()) throw new ApiError('Price requests are cooling down.', 429, blockedUntil)
      const response = await apiFetch(
        `/api/stocks/${encodeURIComponent(symbol)}/price-history?period=${selectedPeriod}&interval=${interval}`,
        { signal },
      )
      try {
        return await readApiJson<PriceHistoryResponse>(response, 'Price history could not be loaded.')
      } catch (error) {
        rememberPriceCooldown(client, error)
        throw error
      }
    },
    // Expiry unlocks manual retry; it does not automatically spend another request.
    enabled: Boolean(symbol) && !cooling && client.getQueryState(queryKey)?.status !== 'error',
    refetchOnReconnect: false,
    staleTime: interval === '1h' ? 15 * 60_000 : 60 * 60_000,
    refetchInterval: (query) => interval === '1h' && !cooling && query.state.status !== 'error' ? 15 * 60_000 : false,
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
  const chartColor = change == null || change === 0 ? '#94A3B8' : change > 0 ? '#b6c8ab' : '#f0a6ae'
  const quoteDate = priceData?.quote_as_of ? new Date(priceData.quote_as_of) : null
  const quoteDateLabel = quoteDate && !Number.isNaN(quoteDate.getTime()) ? quoteDate.toLocaleString() : 'Unknown'
  const selectedLabel = PERIOD_OPTIONS.find((option) => option.value === selectedPeriod)?.label
  const displayedLabel = PERIOD_OPTIONS.find((option) => option.value === priceData?.period)?.label ?? priceData?.period
  const waiting = query.isPending || query.isPlaceholderData

  return (
    <div className={`surface p-4 sm:p-6 ${className}`}>
      <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center sm:justify-between gap-4 mb-4 sm:mb-6">
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-slate-300 mb-2">{symbol} Stock Price</h3>
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <span className="text-2xl sm:text-3xl font-medium tabular-nums text-white">
              {!priceData && query.isPending ? 'Loading quote…' : priceData?.currentPrice == null ? 'Quote unavailable' : formatPrice(priceData.currentPrice, priceData.quote_currency)}
            </span>
            {change != null && changePercent != null ? (
              <div className={`flex items-center gap-1 ${change === 0 ? 'text-white/60' : change > 0 ? 'text-sage-300' : 'text-rose-300'}`}>
                {change > 0 ? <TrendingUp className="h-3 w-3 sm:h-4 sm:w-4" /> : change < 0 ? <TrendingDown className="h-3 w-3 sm:h-4 sm:w-4" /> : null}
                <span className="text-sm font-medium tabular-nums">
                  {change > 0 ? '+' : ''}{formatPrice(change, priceData?.quote_currency)} ({changePercent > 0 ? '+' : ''}{changePercent.toFixed(2)}%)
                </span>
              </div>
            ) : <span className="text-sm text-white/60">Daily change unavailable</span>}
          </div>
          <p className="mt-2 text-xs text-white/60">{priceData?.price_source || 'Price provider'} · Quote time: {quoteDateLabel}</p>
          <p className="mt-1 text-xs text-white/60">Latest chart close: {formatPrice(priceData?.lastHistoricalClose, priceData?.currency)} · {priceData?.lastHistoricalCloseDate ? formatHistoryDate(priceData.lastHistoricalCloseDate, priceData.interval) : 'Date unknown'}</p>
        </div>
        <div className="min-w-0 max-w-full">
          <div role="group" aria-label="Price history period" className="flex items-center bg-white/5 rounded-lg p-1 gap-1 overflow-x-auto">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                disabled={cooling && !client.getQueryData(['price-history', symbol, option.value, priceHistoryInterval(option.value)])} onClick={() => setSelectedPeriod(option.value)}
                aria-pressed={selectedPeriod === option.value}
                className={`min-h-11 sm:min-h-9 flex-1 px-2 sm:px-3 rounded text-xs font-medium transition-colors whitespace-nowrap min-w-[36px] ${selectedPeriod === option.value ? 'bg-white/10 text-sage-200' : 'text-white/70 hover:text-white hover:bg-white/10'}`}
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
      {cooling && <p role="status" className="mb-3 text-xs text-amber-200">Price requests are cooling down until {new Date(deadline).toLocaleTimeString()}. Cached ranges remain available.</p>}
      {query.isError && (
        <div role="alert" className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-amber-200">
          <p>{query.error.message}{priceData ? ' Previously loaded prices are shown.' : ''}</p>
          <button type="button" onClick={() => { if (!cooling) void query.refetch() }} disabled={query.isFetching || cooling} className="button-secondary">Retry price history</button>
        </div>
      )}

      <p className="mb-2 text-xs text-slate-400">Chart unit: {unitLabel(priceData?.currency)} · No currency conversion{priceData ? priceData.interval === '1h' ? ' · Hourly bars · Times in your timezone' : ' · Daily bars' : ''}</p>
      <div aria-busy={waiting} className="h-48 sm:h-64 lg:h-80 mb-4 touch-pan-y">
        {!priceData && query.isPending ? (
          <div className="h-full animate-pulse rounded-lg bg-white/5" />
        ) : bars.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={bars} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.07)" />
              <XAxis dataKey="date" tickFormatter={(value) => formatHistoryDate(value, priceData?.interval)} axisLine={false} tickLine={false} fontSize={11} tick={{ fill: '#9fa9a2', fontFamily: 'monospace' }} minTickGap={24} />
              <YAxis domain={['dataMin', 'dataMax']} tickFormatter={(value) => Number(value).toFixed(2)} axisLine={false} tickLine={false} fontSize={11} tick={{ fill: '#9fa9a2', fontFamily: 'monospace' }} width={windowWidth < 640 ? 50 : 60} />
              <Tooltip content={<CustomTooltip currency={priceData?.currency} interval={priceData?.interval} />} />
              <Line type="monotone" dataKey="close" stroke={chartColor} strokeWidth={2} dot={false} activeDot={{ r: windowWidth < 640 ? 3 : 4, fill: chartColor }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-white/10 p-4 text-center text-sm text-slate-400">
            {query.isError ? limited && cooling ? 'Price requests are temporarily paused. Saved news and filings are still available.' : 'Price history is unavailable. Try again later.' : 'No price history is available for this period.'}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 pt-4 border-t border-white/10">
        {[
          ['Period high', formatPrice(summary.high, priceData?.currency)],
          ['Period low', formatPrice(summary.low, priceData?.currency)],
          [priceData?.interval === '1h' ? 'Avg hourly volume' : 'Avg daily volume', summary.averageVolume == null ? 'Unavailable' : summary.averageVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })],
          ['Data points', priceData ? bars.length.toLocaleString() : '—'],
        ].map(([label, value]) => (
          <div key={label} className="min-w-0 py-2">
            <p className="text-xs text-white/60 mb-1">{label}</p>
            <p className="break-words text-sm font-medium tabular-nums text-slate-200">{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

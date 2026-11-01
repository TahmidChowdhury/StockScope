export interface PriceData {
  date: string
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number | null
}

export interface PriceHistoryResponse {
  retrieved_at?: string | null
  stale?: boolean
  currency?: string | null
  quote_currency?: string | null
  symbol: string
  period: string
  interval: string
  currentPrice: number | null
  priceChange: number | null
  priceChangePercent: number | null
  quote_as_of: string | null
  price_source: string
  lastHistoricalClose: number | null
  lastHistoricalCloseDate: string | null
  data: PriceData[]
}

export function priceHistorySummary(data: PriceData[]) {
  let high: number | null = null
  let low: number | null = null
  let volumeTotal = 0
  let volumeCount = 0
  for (const bar of data) {
    if (typeof bar.high === 'number' && Number.isFinite(bar.high)) {
      high = high === null ? bar.high : Math.max(high, bar.high)
    }
    if (typeof bar.low === 'number' && Number.isFinite(bar.low)) {
      low = low === null ? bar.low : Math.min(low, bar.low)
    }
    if (typeof bar.volume === 'number' && Number.isFinite(bar.volume) && bar.volume >= 0) {
      volumeTotal += bar.volume
      volumeCount++
    }
  }
  return { high, low, averageVolume: volumeCount ? volumeTotal / volumeCount : null }
}

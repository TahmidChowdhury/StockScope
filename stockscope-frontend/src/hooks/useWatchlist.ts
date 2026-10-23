'use client'

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { StockMetadata } from '@/types'

export function useWatchlist() {
  return useQuery({
    queryKey: ['watchlist'],
    queryFn: async ({ signal }): Promise<StockMetadata[]> => {
      const response = await apiFetch('/api/stocks', { signal })
      if (!response.ok) throw new Error('The watchlist could not be loaded.')
      const data = await response.json()
      if (!Array.isArray(data.stocks))
        throw new Error('The watchlist response was incomplete.')
      return data.stocks.map((stock: StockMetadata | string) => {
        const row = typeof stock === 'string' ? { symbol: stock } : stock
        const value = row as Partial<StockMetadata> & { symbol: string }
        return {
          ...value,
          total_posts:
            typeof value.total_posts === 'number' &&
            Number.isFinite(value.total_posts)
              ? value.total_posts
              : null,
          sources: Array.isArray(value.sources) ? value.sources : [],
          avg_sentiment: value.avg_sentiment ?? null,
          last_updated: value.last_updated ?? null,
        }
      })
    },
    refetchInterval: 30000,
  })
}

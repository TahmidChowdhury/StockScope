'use client'

import { useParams, useRouter, useSearchParams } from 'next/navigation'
import AppShell from '@/components/AppShell'
import StockAnalysisHub from '@/components/StockAnalysisHub'
import { useWatchlist } from '@/hooks/useWatchlist'
import { researchReturn } from '@/lib/research-workflow'

export default function StockViewPage() {
  const { ticker } = useParams<{ ticker: string }>()
  const router = useRouter()
  const search = useSearchParams()
  const symbol = ticker.toUpperCase()
  const { data: stocks = [] } = useWatchlist()
  return (
    <AppShell company={symbol}>
      <StockAnalysisHub
        key={symbol}
        symbol={symbol}
        stocks={stocks}
        onBack={() => router.push(researchReturn(search.get('returnTo'))?.href || '/')}
      />
    </AppShell>
  )
}

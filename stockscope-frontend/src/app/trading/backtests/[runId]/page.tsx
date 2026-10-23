import { notFound } from 'next/navigation'
import TradingPage from '../../page'
import { validSavedTradingId } from '@/lib/trading-route'

export default async function SavedBacktestPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params
  if (!validSavedTradingId('backtest', runId)) notFound()
  return <TradingPage />
}

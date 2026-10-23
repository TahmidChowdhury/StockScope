import { notFound } from 'next/navigation'
import TradingPage from '../../page'
import { validSavedTradingId } from '@/lib/trading-route'

export default async function SavedPortfolioPage({ params }: { params: Promise<{ portfolioId: string }> }) {
  const { portfolioId } = await params
  if (!validSavedTradingId('portfolio', portfolioId)) notFound()
  return <TradingPage />
}

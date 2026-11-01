import { redirect } from 'next/navigation'
import { parseSymbols } from '@/lib/financial-format'

/** Keep bookmarked comparisons useful by opening those symbols in the Screener. */
export default async function LegacyComparePage({
  searchParams,
}: {
  searchParams: Promise<{ tickers?: string | string[] }>
}) {
  const { tickers } = await searchParams
  const symbols = parseSymbols(Array.isArray(tickers) ? tickers.join(',') : tickers ?? '').slice(0, 20)
  if (!symbols.length) redirect('/screener')

  const params = new URLSearchParams({ universe: 'custom', symbols: symbols.join(',') })
  redirect(`/screener?${params}`)
}

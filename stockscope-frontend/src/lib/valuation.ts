export interface EvidenceMetric {
  key: string
  label: string
  value: number | null
  format: 'percent' | 'multiple'
  status: string
  reason: string | null
  period_end: string | null
  prior_period_end?: string | null
  basis: string | null
}

export interface ValuationEvidence {
  symbol: string
  company: string
  source: string
  fetched_at: string
  quote: {
    price: number | null
    currency: string | null
    raw_currency: string | null
    price_at: string | null
    status: string
    market_cap: number | null
    enterprise_value: number | null
    shares_outstanding: number | null
    fetched_at: string
    source: string
  }
  financials: {
    currency: string | null
    currency_basis: string
    currency_compatible: boolean
    fetched_at: string | null
    source: string
    fcf_ttm: number | null
    revenue_ttm: number | null
    ebitda_ttm: number | null
  }
  quality: EvidenceMetric[]
  valuation: EvidenceMetric[]
  warnings: string[]
  methodology: { fcf: string; ratios: string; coverage: string }
}

/** An equity cash-flow multiple is an assumption, never an inferred fair value. */
export function equityCashFlowScenario(
  annualFcfeMillions: string,
  sharesMillions: string,
  cashFlowChangePercent: string,
  equityMultiple: string,
  referencePrice: number | null,
): { price: number; difference: number | null } | null {
  const inputs = [
    annualFcfeMillions,
    sharesMillions,
    cashFlowChangePercent,
    equityMultiple,
  ]
  if (inputs.some((value) => !value.trim())) return null
  const [fcfe, shares, change, multiple] = inputs.map(Number)
  if (![fcfe, shares, change, multiple].every(Number.isFinite)) return null
  if (fcfe <= 0 || shares <= 0 || change <= -100 || multiple <= 0) return null
  // Both cash flow and share count use millions, so units cancel per share.
  const price = (fcfe * (1 + change / 100) * multiple) / shares
  if (!Number.isFinite(price) || price <= 0) return null
  const difference =
    typeof referencePrice === 'number' &&
    Number.isFinite(referencePrice) &&
    referencePrice > 0
      ? price / referencePrice - 1
      : null
  return {
    price,
    difference:
      difference !== null && Number.isFinite(difference) ? difference : null,
  }
}

export function valuationDate(value: string | null) {
  if (!value) return 'Unknown'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? 'Unknown'
    : date.toLocaleString('en-US', {
        timeZone: 'America/New_York',
        dateStyle: 'medium',
        timeStyle: 'short',
      }) + ' ET'
}

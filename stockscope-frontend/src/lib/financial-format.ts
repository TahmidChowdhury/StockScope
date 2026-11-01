export const observed = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)
export const amount = (value?: number | null) =>
  observed(value)
    ? new Intl.NumberFormat('en-US', {
        notation: 'compact',
        maximumFractionDigits: 2,
      }).format(value)
    : '—'
export const percent = (value?: number | null) =>
  observed(value)
    ? new Intl.NumberFormat('en-US', {
        style: 'percent',
        maximumFractionDigits: 1,
      }).format(value)
    : '—'
export const ratio = (value?: number | null) =>
  observed(value) ? value.toFixed(2) : '—'
export function parseSymbols(value: string): string[] {
  return [
    ...new Set(
      value
        .toUpperCase()
        .split(/[\s,]+/)
        .map((s) => s.trim().replace(/\./g, '-'))
        .filter((s) => /^[A-Z][A-Z0-9.-]{0,9}$/.test(s)),
    ),
  ]
}

// Preserve case: GBp is pence, not GBP. No conversion is performed.
export const unitLabel = (unit?: string | null) =>
  typeof unit === 'string' && unit.trim() ? unit.trim() : 'Currency unknown'
export const priceAmount = (value?: number | null, unit?: string | null) =>
  observed(value)
    ? `${new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)} ${unitLabel(unit)}`
    : 'Unavailable'
export const revenueAmount = (value?: number | null, unit?: string | null) =>
  `${amount(value)} ${unitLabel(unit)}`
export function comparisonCurrencyNotice(companies: { reporting_currency?: string | null }[]) {
  const units = new Set(companies.map(company => unitLabel(company.reporting_currency)))
  return `${units.size > 1 ? 'Mixed or unknown reporting currencies. Amounts are not directly comparable.' : units.has('Currency unknown') ? 'Reporting currency unknown. Amounts may not be comparable.' : 'Amounts use the same reporting currency.'} No exchange-rate conversion is applied.`
}

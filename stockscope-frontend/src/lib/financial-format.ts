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

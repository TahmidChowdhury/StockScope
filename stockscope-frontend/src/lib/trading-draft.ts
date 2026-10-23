import type { Costs } from './trading'

export interface PaperSetupDraft { name: string; capital: number; benchmark: string; costs: Costs }
export interface BacktestDraft {
  capital: number; benchmark: string; costs: Costs; strategy: string; backtestLabel: string; symbols: string
  start: string; end: string; fast: number; slow: number; member: string; tradeFraction: number; maxWeight: number; delay: number
  symbolsContext?: string
}
export interface PaperOrderDraft { orderSymbol: string; orderSide: string; budget: number; thesis: string; clientOrderId: string }
export interface CongressDraft { csv: string }

const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length <= max
const number = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= 1000000000
const costs = (value: unknown): value is Costs => object(value) && number(value.slippage_bps) && number(value.spread_bps) && number(value.commission)
const funding = (value: Record<string, unknown>) => number(value.capital) && text(value.benchmark, 10) && costs(value.costs)

// Drafts may contain incomplete input; the existing API validates final execution rules.
export function isPaperSetupDraft(value: unknown): value is PaperSetupDraft {
  return object(value) && text(value.name, 80) && funding(value)
}
export function isBacktestDraft(value: unknown): value is BacktestDraft {
  return object(value) && funding(value) && text(value.backtestLabel, 80) && text(value.symbols, 500)
    && ['buy_hold', 'sma', 'congress'].includes(value.strategy as string)
    && text(value.start, 10) && text(value.end, 10) && text(value.member, 150)
    && [value.fast, value.slow, value.tradeFraction, value.maxWeight, value.delay].every(number)
    && (value.symbolsContext === undefined || text(value.symbolsContext, 1000))
}

/** Apply a research handoff once; reloads of that URL retain later draft edits. */
export function applyBacktestSymbols(draft: BacktestDraft, symbols: string[], handoff: string | null): BacktestDraft {
  const context = JSON.stringify([symbols, handoff && handoff.length <= 100 ? handoff : ''])
  if (draft.symbolsContext === context) return draft
  return { ...draft, symbols: symbols.join(', '), symbolsContext: context,
    strategy: draft.strategy === 'sma' && symbols.length > 1 ? 'buy_hold' : draft.strategy }
}
export function isPaperOrderDraft(value: unknown): value is PaperOrderDraft {
  return object(value) && text(value.orderSymbol, 10) && ['buy', 'sell'].includes(value.orderSide as string)
    && number(value.budget) && text(value.thesis, 2000) && typeof value.clientOrderId === 'string'
    && /^[a-zA-Z0-9-]{8,80}$/.test(value.clientOrderId)
}
export function isCongressDraft(value: unknown): value is CongressDraft {
  return object(value) && text(value.csv, 2000000)
}

'use client'

import { useEffect, useId, useRef, useState } from 'react'
import { Combobox } from '@headlessui/react'
import { ArrowRight, LoaderCircle, Search } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import type { StockSearchProps, StockSuggestion } from '@/types'

export default function StockSearch({
  onAnalyze,
  isLoading = false,
  compact = false,
}: StockSearchProps) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([])
  const [searching, setSearching] = useState(false)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const errorId = useId()
  const validationLock = useRef(false)
  const busy = isLoading || validating
  useEffect(() => {
    const controller = new AbortController()
    if (!query.trim()) {
      setSuggestions([])
      setSearching(false)
      return
    }
    setSearching(true)
    const timer = setTimeout(async () => {
      try {
        const response = await apiFetch(
          `/api/stocks/suggestions?q=${encodeURIComponent(query)}`,
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error('Search unavailable')
        const data = await response.json()
        if (!controller.signal.aborted)
          setSuggestions(Array.isArray(data) ? data : [])
      } catch {
        if (!controller.signal.aborted) setSuggestions([])
      } finally {
        if (!controller.signal.aborted) setSearching(false)
      }
    }, 180)
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [query])
  const open = async (raw: string) => {
    const symbol = raw.trim().toUpperCase().replace(/\./g, '-')
    if (!symbol || busy || validationLock.current) return
    validationLock.current = true
    setValidating(true)
    setError('')
    try {
      if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(symbol))
        throw new Error('Enter a valid ticker, such as AAPL.')
      setQuery('')
      setSuggestions([])
      inputRef.current?.blur()
      onAnalyze(symbol)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Search is unavailable. Please try again.',
      )
    } finally {
      setValidating(false)
      validationLock.current = false
    }
  }
  return (
    <div className="w-full max-w-xl">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          void open(query)
        }}
      >
        <Combobox
          value=""
          onChange={(value) => {
            if (value) void open(value)
          }}
          disabled={busy}
        >
          <div className="relative">
            <div className="relative">
              <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <Combobox.Input
                ref={inputRef}
                aria-label="Search for a company or ticker"
                aria-describedby={error ? errorId : undefined}
                aria-invalid={!!error}
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                enterKeyHint="search"
                placeholder={
                  compact ? 'Search companies…' : 'Search a company or ticker…'
                }
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value)
                  setError('')
                }}
                className={`min-h-14 w-full rounded-xl border border-white/10 bg-[#101218] pl-11 pr-16 text-base text-slate-100 placeholder:text-slate-500 focus:border-violet-400/60 focus:outline-none focus:ring-2 focus:ring-violet-400/10 sm:min-h-0 sm:pr-28 sm:text-sm ${compact ? 'py-3' : 'py-4'}`}
              />
              <button
                type="submit"
                aria-label="Explore company"
                disabled={!query.trim() || busy}
                className="absolute bottom-1.5 right-1.5 top-1.5 inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-lg bg-violet-500 px-3 py-2 text-xs font-medium text-white hover:bg-violet-600 disabled:opacity-40 sm:bottom-2 sm:right-2 sm:top-2 sm:min-h-0"
              >
                {busy ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <span className="hidden sm:inline">Explore</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </>
                )}
              </button>
            </div>
            {(suggestions.length > 0 || searching) && (
              <Combobox.Options modal={false} className="absolute z-30 mt-2 max-h-[min(18rem,40dvh)] w-full overflow-y-auto overscroll-contain rounded-xl border border-white/10 bg-[#1c1f29] p-1.5 shadow-2xl">
                {searching ? (
                  <li className="px-4 py-5 text-xs text-slate-400">
                    Finding companies…
                  </li>
                ) : (
                  suggestions.slice(0, 7).map((stock) => (
                    <Combobox.Option
                      key={stock.symbol}
                      value={stock.symbol}
                      className={({ active }) =>
                        `flex cursor-pointer items-center gap-3 rounded-lg px-3 py-3 text-sm ${active ? 'bg-violet-400/10 text-violet-200' : 'text-slate-300'}`
                      }
                    >
                      <span className="w-16 shrink-0 font-semibold">
                        {stock.symbol}
                      </span>
                      <span className="truncate text-xs text-slate-400">
                        {stock.name}
                      </span>
                      <ArrowRight className="ml-auto h-3 w-3 shrink-0" />
                    </Combobox.Option>
                  ))
                )}
              </Combobox.Options>
            )}
          </div>
        </Combobox>
      </form>
      {error && (
        <p
          id={errorId}
          role="alert"
          className="mt-2 text-xs text-rose-300"
        >
          {error}
        </p>
      )}
      {!compact && (
        <div className="mt-3 grid grid-cols-4 gap-2 sm:mt-4 sm:flex sm:flex-wrap sm:items-center">
          <span className="mr-1 hidden text-[11px] text-slate-500 sm:inline">
            Start exploring
          </span>
          {['AAPL', 'MSFT', 'NVDA', 'GOOGL'].map((symbol) => (
            <button
              key={symbol}
              onClick={() => void open(symbol)}
              disabled={busy}
              className="min-h-11 rounded-md border border-white/[0.07] bg-white/[0.02] px-2 py-2 text-xs font-medium text-slate-400 transition-colors hover:border-violet-400/30 hover:text-violet-200 disabled:opacity-40 sm:min-h-0 sm:px-2.5 sm:py-1.5 sm:text-[10px]"
            >
              {symbol}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

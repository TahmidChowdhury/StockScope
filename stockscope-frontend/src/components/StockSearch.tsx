'use client'

import { useEffect, useId, useRef, useState } from 'react'
import { Combobox } from '@headlessui/react'
import { ArrowRight, LoaderCircle, Search } from 'lucide-react'
import { resolveSearch } from '@/lib/search-resolution'
import { apiFetch } from '@/lib/api'
import type { StockSearchProps, StockSuggestion } from '@/types'

export default function StockSearch({
  onAnalyze,
  isLoading = false,
  compact = false,
}: StockSearchProps) {
  const [query, setQuery] = useState('')
  const [directTicker, setDirectTicker] = useState(false)
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([])
  const [searching, setSearching] = useState(false)
  const [searchNotice, setSearchNotice] = useState('')
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const keyboardSelection = useRef(false)
  const errorId = useId()
  const [resolving, setResolving] = useState(false)
  const submitController = useRef<AbortController | null>(null)
  const busy = isLoading || resolving
  useEffect(() => {
    submitController.current?.abort()
    setResolving(false)
    const controller = new AbortController()
    setSearchNotice('')
    setSuggestions([])
    if (!query.trim() || directTicker) {
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
        if (!Array.isArray(data)) throw new Error('Search unavailable')
        if (!controller.signal.aborted) {
          setSuggestions(data)
          if (!data.length) setSearchNotice('No matching companies. Try another name or open a ticker directly.')
        }
      } catch {
        if (!controller.signal.aborted) setSearchNotice('Company suggestions are unavailable. You can still open a ticker directly.')
      } finally {
        if (!controller.signal.aborted) setSearching(false)
      }
    }, 180)
    return () => {
      clearTimeout(timer)
      controller.abort()
      submitController.current?.abort()
    }
  }, [query, directTicker])
  const open = (raw: string) => {
    const symbol = raw.trim().toUpperCase().replace(/^(BRK|BF)\.([AB])$/, '$1-$2')
    if (!symbol || busy) return
    if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(symbol)) {
      setError('Enter a valid ticker, such as AAPL.')
      inputRef.current?.focus()
      return
    }
    setError('')
    onAnalyze(symbol)
  }
  const submit = async () => {
    if (busy || !query.trim()) return
    if (directTicker) { open(query); return }
    const controller = new AbortController()
    submitController.current = controller
    setResolving(true)
    setError('')
    try {
      let matches: StockSuggestion[] = []
      let available = false
      try {
        const response = await apiFetch(`/api/stocks/suggestions?q=${encodeURIComponent(query.trim())}&limit=50`, { signal: controller.signal })
        if (!response.ok) throw new Error('Search unavailable')
        const data = await response.json()
        if (!Array.isArray(data)) throw new Error('Search unavailable')
        matches = data
        available = true
      } catch { /* Direct uppercase ticker entry remains available offline. */ }
      if (controller.signal.aborted) return
      setSuggestions(matches)
      onAnalyze(resolveSearch(query, matches, available))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Choose a company suggestion.')
      inputRef.current?.focus()
    } finally {
      if (!controller.signal.aborted) setResolving(false)
    }
  }
  return (
    <div className="w-full max-w-xl">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
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
                onKeyDownCapture={event => {
                  // Tab moves focus to the submit button without opening a suggestion.
                  if (event.key === 'Tab') event.stopPropagation()
                  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') keyboardSelection.current = true
                  // Headless UI can highlight the first result automatically.
                  // Only explicit arrow-key navigation counts as a selection.
                  if (event.key === 'Enter' && !event.nativeEvent.isComposing && (!keyboardSelection.current || !event.currentTarget.getAttribute('aria-activedescendant'))) {
                    event.preventDefault()
                    event.stopPropagation()
                    void submit()
                  }
                }}
                enterKeyHint="search"
                placeholder={
                  compact ? 'Company name or ticker…' : 'Search a company or ticker…'
                }
                displayValue={() => query}
                value={query}
                onChange={(e) => {
                  keyboardSelection.current = false
                  setQuery(e.target.value)
                  setError('')
                }}
                className={`min-h-14 w-full rounded-xl border border-white/10 bg-[#111513] pl-11 pr-16 text-base text-slate-100 placeholder:text-slate-500 focus:border-sage-400/60 focus:outline-none focus:ring-2 focus:ring-sage-400/10 sm:min-h-0 sm:pr-28 sm:text-sm ${compact ? 'py-3' : 'py-4'}`}
              />
              <button
                type="submit"
                aria-label={busy ? 'Opening company research' : 'Explore'}
                disabled={!query.trim() || busy}
                className="absolute right-1.5 top-1/2 inline-flex h-11 min-w-11 -translate-y-1/2 items-center justify-center gap-2 rounded-lg bg-sage-300 px-3 py-2 text-xs font-medium text-[#111613] hover:bg-sage-200 disabled:opacity-40 sm:right-2 lg:h-7"
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
              <Combobox.Options modal={false} className="absolute z-30 mt-2 max-h-[min(18rem,40dvh)] w-full overflow-y-auto overscroll-contain rounded-xl border border-white/10 bg-[#202722] p-1.5 shadow-2xl">
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
                        `flex cursor-pointer items-center gap-3 rounded-lg px-3 py-3 text-sm ${active ? 'bg-sage-400/10 text-sage-200' : 'text-slate-300'}`
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
        <label className="mt-2 flex min-h-11 items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={directTicker} disabled={busy} onChange={event => { setDirectTicker(event.target.checked); setError('') }} />
          Enter ticker directly
        </label>
      </form>
      <p role="status" className="mt-2 text-xs text-slate-400">{!error && searchNotice}</p>
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
              className="min-h-11 rounded-md border border-white/[0.07] bg-white/[0.02] px-2 py-2 text-xs font-medium text-slate-400 transition-colors hover:border-sage-400/30 hover:text-sage-200 disabled:opacity-40 sm:min-h-0 sm:px-2.5 sm:py-1.5 sm:text-[10px]"
            >
              {symbol}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

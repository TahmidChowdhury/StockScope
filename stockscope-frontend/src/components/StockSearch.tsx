'use client'

import { useState, useEffect, useRef } from 'react'
import { MagnifyingGlassIcon, ChartBarIcon } from '@heroicons/react/24/outline'
import { Combobox } from '@headlessui/react'
import type { StockSuggestion, StockSearchProps } from '@/types'

export default function StockSearch({ onAnalyze, isLoading = false }: StockSearchProps) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([])
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  // Get API URL from environment variables with fallback
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Get password for API calls
  const getPasswordParam = () => {
    const password = localStorage.getItem('stockscope_password')
    return password ? `?password=${encodeURIComponent(password)}` : ''
  }

  // Debounced search - prevents too many API calls while typing
  useEffect(() => {
    // Fetch suggestions from your FastAPI backend
    const fetchSuggestions = async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setSuggestions([])
        return
      }

      setIsLoadingSuggestions(true)
      try {
        const response = await fetch(`${API_BASE_URL}/api/stocks/suggestions${getPasswordParam()}&q=${encodeURIComponent(searchQuery)}`)
        const data = await response.json()
        setSuggestions(data)
      } catch (error) {
        console.error('Failed to fetch suggestions:', error)
        setSuggestions([])
      } finally {
        setIsLoadingSuggestions(false)
      }
    }

    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      fetchSuggestions(query)
    }, 150) // 150ms delay - feels instant but reduces API calls

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [query, API_BASE_URL])

  const handleAnalyze = (symbol: string) => {
    setQuery('')
    setSuggestions([])
    onAnalyze(symbol)
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="relative">
        <Combobox value="" onChange={(value) => value && handleAnalyze(value)}>
          <div className="relative">
            {/* Search Input */}
            <div className="relative">
              <Combobox.Input
                className="w-full rounded-xl border-0 bg-white/10 backdrop-blur-sm py-4 pl-12 pr-32 text-white placeholder:text-white/60 ring-1 ring-white/20 focus:ring-2 focus:ring-blue-500 text-lg shadow-lg transition-all duration-200"
                placeholder="Type stock symbol (e.g., AAPL, META, TSLA)..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && query.trim()) {
                    event.preventDefault()
                    handleAnalyze(query.trim().toUpperCase())
                  }
                }}
              />
              
              {/* Search Icon */}
              <MagnifyingGlassIcon className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-white/60" />
              
              {/* Analyze Button */}
              <button
                onClick={() => query.trim() && handleAnalyze(query.trim().toUpperCase())}
                disabled={!query.trim() || isLoading}
                className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-2 text-sm font-medium text-white shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                ) : (
                  <ChartBarIcon className="h-4 w-4" />
                )}
                Analyze
              </button>
            </div>

            {/* Suggestions Dropdown */}
            {(suggestions.length > 0 || isLoadingSuggestions) && (
              <Combobox.Options className="absolute z-50 mt-2 max-h-96 w-full overflow-auto rounded-xl bg-white/95 backdrop-blur-sm shadow-xl ring-1 ring-black/10">
                {isLoadingSuggestions ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600/30 border-t-blue-600" />
                    <span className="ml-3 text-gray-600">Searching...</span>
                  </div>
                ) : (
                  suggestions.map((stock) => (
                    <Combobox.Option
                      key={stock.symbol}
                      value={stock.symbol}
                      className={({ active }) =>
                        `relative cursor-pointer select-none px-6 py-4 transition-colors ${
                          active ? 'bg-blue-50 text-blue-900' : 'text-gray-900'
                        }`
                      }
                    >
                      {({ active }) => (
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-100 to-purple-100">
                              <span className="text-sm font-bold text-blue-700">
                                {stock.symbol.slice(0, 2)}
                              </span>
                            </div>
                            <div className="ml-4">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-gray-900">
                                  {stock.symbol}
                                </span>
                                {stock.sector && (
                                  <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                                    {stock.sector}
                                  </span>
                                )}
                              </div>
                              <div className="text-sm text-gray-500">
                                {stock.name}
                              </div>
                            </div>
                          </div>
                          {active && (
                            <ChartBarIcon className="h-5 w-5 text-blue-600" />
                          )}
                        </div>
                      )}
                    </Combobox.Option>
                  ))
                )}
              </Combobox.Options>
            )}
          </div>
        </Combobox>

        {/* Quick Examples */}
        <div className="mt-6">
          <p className="text-sm text-white/60 mb-3">Popular stocks:</p>
          <div className="flex flex-wrap gap-2">
            {['AAPL', 'TSLA', 'NVDA', 'META', 'MSFT', 'GOOGL'].map((symbol) => (
              <button
                key={symbol}
                onClick={() => handleAnalyze(symbol)}
                disabled={isLoading}
                className="rounded-full bg-white/10 px-4 py-2 text-sm text-white backdrop-blur-sm transition-all duration-200 hover:bg-white/20 disabled:opacity-50"
              >
                {symbol}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
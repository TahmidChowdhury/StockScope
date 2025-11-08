'use client'

import { useState, useEffect, useRef } from 'react'
import { MagnifyingGlassIcon, ChartBarIcon } from '@heroicons/react/24/outline'
import { Combobox } from '@headlessui/react'
import type { StockSuggestion, StockSearchProps } from '@/types'

export default function StockSearch({ onAnalyze, isLoading = false, compact = false }: StockSearchProps) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([])
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  // New state for validation feedback
  const [validationError, setValidationError] = useState<string | null>(null)
  const [isShaking, setIsShaking] = useState(false)

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

  const handleAnalyze = async (symbol: string) => {
    // Clear any previous errors
    setValidationError(null)
    setIsShaking(false)
    
    // First validate the symbol
    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks/validate/${symbol}${getPasswordParam()}`)
      const validation = await response.json()
      
      if (!validation.valid) {
        // Trigger shake animation
        setIsShaking(true)
        setValidationError(validation.message)
        
        // Reset shake after animation
        setTimeout(() => setIsShaking(false), 600)
        return
      }
      
      // If valid, proceed with analysis
      setQuery('')
      setSuggestions([])
      setValidationError(null)
      onAnalyze(symbol)
      
    } catch (error) {
      console.error('Error validating symbol:', error)
      setIsShaking(true)
      setValidationError('Failed to validate stock symbol. Please try again.')
      setTimeout(() => setIsShaking(false), 600)
    }
  }

  if (compact) {
    return (
      <div className="w-full">
        <div className="relative">
          <Combobox value="" onChange={(value) => value && handleAnalyze(value)}>
            <div className="relative">
              <div className={`relative ${isShaking ? 'animate-shake' : ''}`}>
                <Combobox.Input
                  className="w-full rounded-lg border-0 bg-white/10 backdrop-blur-sm py-2.5 pl-8 pr-16 text-white placeholder:text-white/60 ring-1 ring-white/20 focus:ring-2 focus:ring-blue-500 text-sm shadow-lg transition-all duration-200"
                  placeholder="Search stocks..."
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && query.trim()) {
                      event.preventDefault()
                      handleAnalyze(query.trim().toUpperCase())
                    }
                  }}
                />
                
                <MagnifyingGlassIcon className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-white/60" />
                
                <button
                  onClick={() => query.trim() && handleAnalyze(query.trim().toUpperCase())}
                  disabled={!query.trim() || isLoading}
                  className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center rounded-md bg-gradient-to-r from-blue-600 to-purple-600 px-2 py-1 text-xs font-medium text-white shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <div className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  ) : (
                    <ChartBarIcon className="h-3 w-3" />
                  )}
                </button>
              </div>

              {validationError && (
                <p className="mt-1 text-xs text-red-400">{validationError}</p>
              )}

              {/* Compact Suggestions Dropdown */}
              {(suggestions.length > 0 || isLoadingSuggestions) && (
                <Combobox.Options className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg bg-white/95 backdrop-blur-sm shadow-xl ring-1 ring-black/10">
                  {isLoadingSuggestions ? (
                    <div className="flex items-center justify-center py-4">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600/30 border-t-blue-600" />
                      <span className="ml-2 text-gray-600 text-xs">Searching...</span>
                    </div>
                  ) : (
                    suggestions.slice(0, 5).map((stock) => (
                      <Combobox.Option
                        key={stock.symbol}
                        value={stock.symbol}
                        className={({ active }) =>
                          `relative cursor-pointer select-none px-3 py-2 transition-colors ${
                            active ? 'bg-blue-50 text-blue-900' : 'text-gray-900'
                          }`
                        }
                      >
                        <div className="flex items-center">
                          <div className="flex h-6 w-6 items-center justify-center rounded bg-gradient-to-br from-blue-100 to-purple-100">
                            <span className="text-xs font-bold text-blue-700">
                              {stock.symbol.slice(0, 2)}
                            </span>
                          </div>
                          <div className="ml-2 flex-1 min-w-0">
                            <div className="text-sm font-semibold text-gray-900">{stock.symbol}</div>
                            <div className="text-xs text-gray-500 truncate">{stock.name}</div>
                          </div>
                        </div>
                      </Combobox.Option>
                    ))
                  )}
                </Combobox.Options>
              )}
            </div>
          </Combobox>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-2 sm:px-0">
      <div className="relative">
        <Combobox value="" onChange={(value) => value && handleAnalyze(value)}>
          <div className="relative">
            {/* Search Input - Mobile optimized */}
            <div className={`relative ${isShaking ? 'animate-shake' : ''}`}>
              <Combobox.Input
                className="w-full rounded-xl border-0 bg-white/10 backdrop-blur-sm py-3 sm:py-4 pl-10 sm:pl-12 pr-24 sm:pr-32 text-white placeholder:text-white/60 ring-1 ring-white/20 focus:ring-2 focus:ring-blue-500 text-base sm:text-lg shadow-lg transition-all duration-200"
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
              
              {/* Search Icon - Responsive sizing */}
              <MagnifyingGlassIcon className="absolute left-3 sm:left-4 top-1/2 h-4 w-4 sm:h-5 sm:w-5 -translate-y-1/2 text-white/60" />
              
              {/* Analyze Button - Mobile optimized */}
              <button
                onClick={() => query.trim() && handleAnalyze(query.trim().toUpperCase())}
                disabled={!query.trim() || isLoading}
                className="absolute right-1 sm:right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 sm:gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-2 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-white shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="h-3 w-3 sm:h-4 sm:w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                ) : (
                  <ChartBarIcon className="h-3 w-3 sm:h-4 sm:w-4" />
                )}
                <span className="hidden sm:inline">Analyze</span>
              </button>
            </div>

            {/* Validation Error */}
            {validationError && (
              <p className="mt-2 text-sm text-red-400 px-2">{validationError}</p>
            )}

            {/* Suggestions Dropdown - Mobile optimized */}
            {(suggestions.length > 0 || isLoadingSuggestions) && (
              <Combobox.Options className="absolute z-50 mt-2 max-h-80 sm:max-h-96 w-full overflow-auto rounded-xl bg-white/95 backdrop-blur-sm shadow-xl ring-1 ring-black/10">
                {isLoadingSuggestions ? (
                  <div className="flex items-center justify-center py-6 sm:py-8">
                    <div className="h-5 w-5 sm:h-6 sm:w-6 animate-spin rounded-full border-2 border-blue-600/30 border-t-blue-600" />
                    <span className="ml-3 text-gray-600 text-sm sm:text-base">Searching...</span>
                  </div>
                ) : (
                  suggestions.map((stock) => (
                    <Combobox.Option
                      key={stock.symbol}
                      value={stock.symbol}
                      className={({ active }) =>
                        `relative cursor-pointer select-none px-4 sm:px-6 py-3 sm:py-4 transition-colors ${
                          active ? 'bg-blue-50 text-blue-900' : 'text-gray-900'
                        }`
                      }
                    >
                      {({ active }) => (
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-100 to-purple-100">
                              <span className="text-xs sm:text-sm font-bold text-blue-700">
                                {stock.symbol.slice(0, 2)}
                              </span>
                            </div>
                            <div className="ml-3 sm:ml-4">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-gray-900 text-sm sm:text-base">
                                  {stock.symbol}
                                </span>
                                {stock.sector && (
                                  <span className="rounded-full bg-gray-100 px-2 py-0.5 sm:py-1 text-xs text-gray-600">
                                    {stock.sector}
                                  </span>
                                )}
                              </div>
                              <div className="text-xs sm:text-sm text-gray-500 truncate max-w-[200px] sm:max-w-none">
                                {stock.name}
                              </div>
                            </div>
                          </div>
                          {active && (
                            <ChartBarIcon className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600 flex-shrink-0" />
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

        {/* Quick Examples - Mobile optimized */}
        <div className="mt-4 sm:mt-6">
          <p className="text-xs sm:text-sm text-white/60 mb-2 sm:mb-3 px-2 sm:px-0">Popular stocks:</p>
          <div className="flex flex-wrap gap-2 justify-center sm:justify-start px-2 sm:px-0">
            {['AAPL', 'TSLA', 'NVDA', 'META', 'MSFT', 'GOOGL'].map((symbol) => (
              <button
                key={symbol}
                onClick={() => handleAnalyze(symbol)}
                disabled={isLoading}
                className="rounded-full bg-white/10 px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm text-white backdrop-blur-sm transition-all duration-200 hover:bg-white/20 disabled:opacity-50 active:scale-95"
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
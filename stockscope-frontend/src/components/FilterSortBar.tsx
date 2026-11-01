'use client'

import { useState, useRef, useEffect, useId } from 'react'
import { Filter, ArrowUpDown, CheckCircle, X } from 'lucide-react'

interface FilterOption {
  id: string
  label: string
  enabled: boolean
}

interface SortOption {
  id: string
  label: string
  direction: 'asc' | 'desc'
}

interface FilterSortBarProps {
  filters: FilterOption[]
  onFilterChange: (filterId: string, enabled: boolean) => void
  sortOptions: SortOption[]
  currentSort: string
  onSortChange: (sortId: string) => void
  className?: string
  resultCount?: number
}

export default function FilterSortBar({
  filters,
  onFilterChange,
  sortOptions,
  currentSort,
  onSortChange,
  className = '',
  resultCount
}: FilterSortBarProps) {
  const [showFilters, setShowFilters] = useState(false)
  const [showSort, setShowSort] = useState(false)
  const filterRef = useRef<HTMLDivElement>(null)
  const sortRef = useRef<HTMLDivElement>(null)
  const filterId = useId()
  const sortId = useId()

  // Close dropdowns when clicking outside — eliminates the dark backdrop flash
  useEffect(() => {
    const handler = (e: PointerEvent) => {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setShowFilters(false)
      }
      if (sortRef.current && !sortRef.current.contains(e.target as Node)) {
        setShowSort(false)
      }
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowFilters(false)
        setShowSort(false)
      }
    }
    document.addEventListener('pointerdown', handler)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handler)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const enabledCount = filters.filter(filter => filter.enabled).length
  const filtered = enabledCount < filters.length

  return (
    <div className={`border-b border-white/[0.07] pb-2 ${className}`}>
      <div className="relative flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        {/* Top/Left side - Result count */}
        <div className="text-xs sm:text-sm text-white/60">
          {resultCount !== undefined && (
            <span>{resultCount} {resultCount === 1 ? 'result' : 'results'}</span>
          )}
        </div>

        {/* Bottom/Right side - Filter and Sort controls */}
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          {/* Filter Dropdown */}
          <div className="sm:relative" ref={filterRef}>
            <button
              type="button"
              aria-expanded={showFilters}
              aria-controls={filterId}
              onClick={() => { setShowFilters(!showFilters); setShowSort(false) }}
              className={`
                inline-flex min-h-11 items-center gap-1.5 whitespace-nowrap rounded-md px-2 text-xs transition-colors
                ${filtered
                  ? 'bg-sage-400/10 text-sage-200'
                  : 'text-slate-300 hover:bg-white/5'
                }
              `}
            >
              <Filter className="h-3 w-3 sm:h-4 sm:w-4" />
              <span>
                Sources{filtered && ` (${enabledCount}/${filters.length})`}
              </span>
            </button>

            {showFilters && (
              <div id={filterId} className="absolute right-0 top-full mt-1 w-56 max-w-full sm:max-w-none bg-[#202722] border border-white/10 rounded-xl shadow-xl z-50 max-h-[min(20rem,50dvh)] overflow-y-auto overscroll-contain">
                  <div className="p-3 sm:p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-sm font-medium text-white">Filter by Source</div>
                    </div>
                    
                    <div className="space-y-2">
                      {filters.map((filter) => (
                        <label
                          key={filter.id}
                          className="flex min-h-11 items-center gap-3 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition-colors"
                        >
                          <div className="relative">
                            <input
                              type="checkbox"
                              checked={filter.enabled}
                              onChange={(e) => onFilterChange(filter.id, e.target.checked)}
                              className="peer sr-only"
                            />
                            <div className={`
                              w-5 h-5 rounded border-2 flex items-center justify-center transition-all peer-focus-visible:ring-2 peer-focus-visible:ring-sage-300
                              ${filter.enabled 
                                ? 'bg-sage-600 border-sage-600'
                                : 'border-gray-400 hover:border-gray-300'
                              }
                            `}>
                              {filter.enabled && <CheckCircle className="h-3 w-3 text-white" />}
                            </div>
                          </div>
                          <span className="min-w-0 break-words text-sm text-gray-200 flex items-center gap-2 flex-1">
                            {filter.label}
                          </span>
                        </label>
                      ))}
                    </div>

                    {/* Clear all filters */}
                    {filtered && (
                      <button
                        onClick={() => filters.forEach(f => onFilterChange(f.id, true))}
                        type="button"
                        className="min-h-11 w-full mt-3 px-3 py-2 text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                      >
                        Show all sources
                      </button>
                    )}
                  </div>
                </div>
            )}
          </div>

          {/* Sort Dropdown */}
          <div className="sm:relative" ref={sortRef}>
            <button
              type="button"
              aria-expanded={showSort}
              aria-controls={sortId}
              onClick={() => { setShowSort(!showSort); setShowFilters(false) }}
              className="inline-flex min-h-11 items-center gap-1.5 whitespace-nowrap rounded-md px-2 text-xs text-slate-300 transition-colors hover:bg-white/5"
            >
              <ArrowUpDown className="h-3 w-3 sm:h-4 sm:w-4" />
              <span>Sort</span>
            </button>

            {showSort && (
              <div id={sortId} className="absolute right-0 top-full mt-1 w-48 max-w-full sm:max-w-none bg-[#202722] border border-white/10 rounded-xl shadow-xl z-50">
                <div className="p-2">
                  <div className="flex items-center justify-between mb-2 sm:hidden px-2">
                    <span className="text-sm font-medium text-white">Sort by</span>
                    <button
                      type="button"
                      aria-label="Close sort options"
                      onClick={() => setShowSort(false)}
                      className="flex h-11 w-11 items-center justify-center text-white/60 hover:text-white"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    
                    {sortOptions.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        aria-pressed={currentSort === option.id}
                        onClick={() => {
                          onSortChange(option.id)
                          setShowSort(false)
                        }}
                        className={`
                          min-h-11 w-full text-left px-3 py-2 rounded-lg text-sm transition-colors
                          ${currentSort === option.id 
                            ? 'bg-sage-600/20 text-sage-300'
                            : 'text-gray-300 hover:bg-white/5 hover:text-white'
                          }
                        `}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

            )}
          </div>
        </div>
      </div>

    </div>
  )
}

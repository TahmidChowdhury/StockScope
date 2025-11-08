'use client'

import { useState } from 'react'
import { Filter, ArrowUpDown, CheckCircle } from 'lucide-react'

interface FilterOption {
  id: string
  label: string
  icon?: string
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

  const activeFiltersCount = filters.filter(f => f.enabled).length

  return (
    <div className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4 ${className}`}>
      <div className="flex items-center justify-between flex-wrap gap-3">
        {/* Left side - Result count */}
        <div className="text-sm text-gray-300">
          {resultCount !== undefined && (
            <span>{resultCount} {resultCount === 1 ? 'result' : 'results'}</span>
          )}
        </div>

        {/* Right side - Filter and Sort controls */}
        <div className="flex items-center gap-3">
          {/* Filter Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`
                flex items-center gap-2 px-3 py-2 rounded-lg border transition-all
                ${activeFiltersCount > 0 
                  ? 'bg-purple-600/20 border-purple-500/40 text-purple-300' 
                  : 'bg-white/5 border-white/20 text-gray-300 hover:bg-white/10'
                }
              `}
            >
              <Filter className="h-4 w-4" />
              <span className="text-sm">
                Filter {activeFiltersCount > 0 && `(${activeFiltersCount})`}
              </span>
            </button>

            {showFilters && (
              <div className="absolute right-0 top-full mt-2 w-56 bg-slate-800/95 backdrop-blur-sm border border-white/20 rounded-xl shadow-xl z-50">
                <div className="p-3">
                  <div className="text-sm font-medium text-white mb-3">Filter by Source</div>
                  <div className="space-y-2">
                    {filters.map((filter) => (
                      <label
                        key={filter.id}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition-colors"
                      >
                        <div className="relative">
                          <input
                            type="checkbox"
                            checked={filter.enabled}
                            onChange={(e) => onFilterChange(filter.id, e.target.checked)}
                            className="sr-only"
                          />
                          <div className={`
                            w-5 h-5 rounded border-2 flex items-center justify-center transition-all
                            ${filter.enabled 
                              ? 'bg-purple-600 border-purple-600' 
                              : 'border-gray-400 hover:border-gray-300'
                            }
                          `}>
                            {filter.enabled && <CheckCircle className="h-3 w-3 text-white" />}
                          </div>
                        </div>
                        <span className="text-sm text-gray-200 flex items-center gap-2">
                          {filter.icon && <span>{filter.icon}</span>}
                          {filter.label}
                        </span>
                      </label>
                    ))}
                  </div>

                  {/* Clear all filters */}
                  {activeFiltersCount > 0 && (
                    <button
                      onClick={() => filters.forEach(f => onFilterChange(f.id, false))}
                      className="w-full mt-3 px-3 py-2 text-sm text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                    >
                      Clear All
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Sort Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowSort(!showSort)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border bg-white/5 border-white/20 text-gray-300 hover:bg-white/10 transition-all"
            >
              <ArrowUpDown className="h-4 w-4" />
              <span className="text-sm">Sort</span>
            </button>

            {showSort && (
              <div className="absolute right-0 top-full mt-2 w-48 bg-slate-800/95 backdrop-blur-sm border border-white/20 rounded-xl shadow-xl z-50">
                <div className="p-2">
                  {sortOptions.map((option) => (
                    <button
                      key={option.id}
                      onClick={() => {
                        onSortChange(option.id)
                        setShowSort(false)
                      }}
                      className={`
                        w-full text-left px-3 py-2 rounded-lg text-sm transition-colors
                        ${currentSort === option.id 
                          ? 'bg-purple-600/20 text-purple-300' 
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

      {/* Active filters display */}
      {activeFiltersCount > 0 && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <div className="flex flex-wrap gap-2">
            {filters.filter(f => f.enabled).map((filter) => (
              <span
                key={filter.id}
                className="inline-flex items-center gap-1 px-2 py-1 bg-purple-600/20 text-purple-300 rounded-lg text-xs"
              >
                {filter.icon && <span>{filter.icon}</span>}
                {filter.label}
                <button
                  onClick={() => onFilterChange(filter.id, false)}
                  className="ml-1 hover:text-purple-200 transition-colors"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
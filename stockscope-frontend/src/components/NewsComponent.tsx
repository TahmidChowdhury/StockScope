'use client'

import { useState, useEffect, useMemo } from 'react'
import { ExternalLink, Calendar, Newspaper } from 'lucide-react'
import NewsCard from './NewsCard'
import FilterSortBar from './FilterSortBar'

interface NewsArticle {
  title: string
  url: string
  publishedAt: string
  source: {
    name: string
  }
  description?: string
  sentiment?: {
    score: number
    label: string
  }
}

interface NewsComponentProps {
  symbol: string
  className?: string
}

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

export default function NewsComponent({ symbol, className = '' }: NewsComponentProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // New state for filtering and sorting
  const [filters, setFilters] = useState<FilterOption[]>([
    { id: 'yahoo', label: 'Yahoo Finance', icon: '📰', enabled: true },
    { id: 'motley', label: 'Motley Fool', icon: '🎯', enabled: true },
    { id: 'reuters', label: 'Reuters', icon: '📊', enabled: true },
    { id: 'bloomberg', label: 'Bloomberg', icon: '💼', enabled: true },
    { id: 'other', label: 'Other Sources', icon: '🗞️', enabled: true }
  ])
  
  const [currentSort, setCurrentSort] = useState('date-desc')
  
  const sortOptions: SortOption[] = [
    { id: 'date-desc', label: 'Latest First', direction: 'desc' },
    { id: 'date-asc', label: 'Oldest First', direction: 'asc' },
    { id: 'sentiment-desc', label: 'Most Positive', direction: 'desc' },
    { id: 'sentiment-asc', label: 'Most Negative', direction: 'asc' }
  ]

  // Filtered and sorted articles
  const filteredAndSortedArticles = useMemo(() => {
    // Filter articles by enabled sources
    const enabledSources = filters.filter(f => f.enabled).map(f => f.id)
    let filtered = articles.filter(article => {
      const sourceName = article.source.name.toLowerCase()
      
      // Check which source category this article belongs to
      if (sourceName.includes('yahoo') && enabledSources.includes('yahoo')) return true
      if (sourceName.includes('motley') && enabledSources.includes('motley')) return true
      if (sourceName.includes('reuters') && enabledSources.includes('reuters')) return true
      if (sourceName.includes('bloomberg') && enabledSources.includes('bloomberg')) return true
      if (!sourceName.includes('yahoo') && !sourceName.includes('motley') && 
          !sourceName.includes('reuters') && !sourceName.includes('bloomberg') && 
          enabledSources.includes('other')) return true
      
      return false
    })

    // Sort articles
    filtered.sort((a, b) => {
      switch (currentSort) {
        case 'date-desc':
          return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
        case 'date-asc':
          return new Date(a.publishedAt).getTime() - new Date(b.publishedAt).getTime()
        case 'sentiment-desc':
          return (b.sentiment?.score || 0) - (a.sentiment?.score || 0)
        case 'sentiment-asc':
          return (a.sentiment?.score || 0) - (b.sentiment?.score || 0)
        default:
          return 0
      }
    })

    return filtered
  }, [articles, filters, currentSort])

  const handleFilterChange = (filterId: string, enabled: boolean) => {
    setFilters(prev => prev.map(f => 
      f.id === filterId ? { ...f, enabled } : f
    ))
  }

  const handleSortChange = (sortId: string) => {
    setCurrentSort(sortId)
  }

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const getPasswordParam = () => {
    const password = localStorage.getItem('stockscope_password')
    return password ? `?password=${encodeURIComponent(password)}` : ''
  }

  useEffect(() => {
    const fetchNews = async () => {
      setLoading(true)
      setError(null)

      try {
        // Use the dedicated news endpoint
        const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/news${getPasswordParam()}`)
        
        if (!response.ok) {
          throw new Error('Failed to fetch news data')
        }
        
        const data = await response.json()
        
        // Transform the articles to match our interface
        const transformedArticles = data.articles?.map((item: any) => ({
          title: item.title || 'No title available',
          url: item.url || '#',
          publishedAt: item.publishedAt || new Date().toISOString(),
          source: {
            name: item.source || 'Unknown Source'
          },
          description: item.description || '',
          sentiment: item.sentiment ? {
            score: item.sentiment.compound || 0,
            label: item.sentiment.label || 'Neutral'
          } : undefined
        })) || []
        
        setArticles(transformedArticles.slice(0, 20)) // Limit to 20 articles
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    if (symbol) {
      fetchNews()
    }
  }, [symbol])

  if (loading) {
    return (
      <div className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 ${className}`}>
        <div className="flex items-center gap-3 mb-6">
          <Newspaper className="h-6 w-6 text-purple-400" />
          <h2 className="text-xl font-semibold text-white">Latest News</h2>
        </div>
        
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4 animate-pulse">
              <div className="h-4 bg-white/10 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-white/10 rounded w-1/2 mb-2"></div>
              <div className="h-3 bg-white/10 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 ${className}`}>
        <div className="flex items-center gap-3 mb-4">
          <Newspaper className="h-6 w-6 text-purple-400" />
          <h2 className="text-xl font-semibold text-white">Latest News</h2>
        </div>
        <div className="text-center py-8">
          <p className="text-red-400 mb-2">Failed to load news</p>
          <p className="text-gray-400 text-sm">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Newspaper className="h-6 w-6 text-purple-400" />
        <h2 className="text-xl font-semibold text-white">Latest News</h2>
        <span className="text-sm text-gray-400">for {symbol}</span>
      </div>

      {/* Filter and Sort Bar */}
      <FilterSortBar
        filters={filters}
        onFilterChange={handleFilterChange}
        sortOptions={sortOptions}
        currentSort={currentSort}
        onSortChange={handleSortChange}
        resultCount={filteredAndSortedArticles.length}
        className="mb-6"
      />

      {/* Articles Grid */}
      {filteredAndSortedArticles.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-400">No news articles found with current filters</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          {filteredAndSortedArticles.map((article, index) => (
            <NewsCard
              key={`${article.url}-${index}`}
              article={article}
              showSentiment={true}
              variant="default"
            />
          ))}
        </div>
      )}
    </div>
  )
}
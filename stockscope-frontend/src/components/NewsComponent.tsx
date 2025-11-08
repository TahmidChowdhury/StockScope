'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { Newspaper, RefreshCw, ExternalLink, Bookmark, BookmarkCheck } from 'lucide-react'
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

  // New mobile-specific state
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [savedArticles, setSavedArticles] = useState<Set<string>>(new Set())
  const [expandedArticles, setExpandedArticles] = useState<Set<string>>(new Set())
  const [showFullscreen, setShowFullscreen] = useState(false)
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null)
  const refreshStartY = useRef(0)
  const refreshDistance = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)

  // Load saved articles from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(`stockscope_saved_articles_${symbol}`)
    if (saved) {
      setSavedArticles(new Set(JSON.parse(saved)))
    }
  }, [symbol])

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

  // Pull-to-refresh handlers for mobile
  const handleTouchStart = (e: React.TouchEvent) => {
    if (containerRef.current && containerRef.current.scrollTop === 0) {
      refreshStartY.current = e.touches[0].clientY
    }
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    if (containerRef.current && containerRef.current.scrollTop === 0 && refreshStartY.current > 0) {
      refreshDistance.current = e.touches[0].clientY - refreshStartY.current
      if (refreshDistance.current > 0 && refreshDistance.current < 100) {
        e.preventDefault()
        // Add visual feedback here if needed
      }
    }
  }

  const handleTouchEnd = () => {
    if (refreshDistance.current > 60 && !isRefreshing) {
      handleRefresh()
    }
    refreshStartY.current = 0
    refreshDistance.current = 0
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    // Trigger news refetch
    await fetchNews()
    setTimeout(() => setIsRefreshing(false), 500) // Minimum refresh time for UX
  }

  // Save/unsave article functionality
  const toggleSaveArticle = (articleUrl: string) => {
    const newSaved = new Set(savedArticles)
    if (newSaved.has(articleUrl)) {
      newSaved.delete(articleUrl)
    } else {
      newSaved.add(articleUrl)
    }
    setSavedArticles(newSaved)
    localStorage.setItem(`stockscope_saved_articles_${symbol}`, JSON.stringify([...newSaved]))
  }

  // Expand/collapse article preview
  const toggleExpandArticle = (articleUrl: string) => {
    const newExpanded = new Set(expandedArticles)
    if (newExpanded.has(articleUrl)) {
      newExpanded.delete(articleUrl)
    } else {
      newExpanded.add(articleUrl)
    }
    setExpandedArticles(newExpanded)
  }

  // Open article in fullscreen modal for mobile
  const openFullscreen = (article: NewsArticle) => {
    setSelectedArticle(article)
    setShowFullscreen(true)
  }

  const fetchNews = async () => {
    if (!isRefreshing) setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/news${getPasswordParam()}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch news data')
      }
      
      const data = await response.json()
      
      // Transform the articles to match our interface
      const transformedArticles = data.articles?.map((item: { 
        title?: string; 
        url?: string; 
        publishedAt?: string; 
        source?: string; 
        description?: string; 
        sentiment?: { compound?: number; label?: string }
      }) => {
        // Handle missing or invalid URLs better
        let articleUrl = item.url || ''
        
        // If no URL provided, create appropriate fallback based on source
        if (!articleUrl || articleUrl === '#' || articleUrl === 'null') {
          const sourceName = (item.source || '').toLowerCase()
          if (sourceName.includes('stocktwits')) {
            // For StockTwits, link to the symbol page since individual message URLs aren't available
            articleUrl = `https://stocktwits.com/symbol/${symbol}`
          } else if (sourceName.includes('yahoo')) {
            articleUrl = `https://finance.yahoo.com/quote/${symbol}/news`
          } else if (sourceName.includes('motley')) {
            articleUrl = `https://www.fool.com/investing/${symbol.toLowerCase()}-stock/`
          } else {
            // For other sources without URLs, don't provide a link
            articleUrl = ''
          }
        }
        
        return {
          title: item.title || 'No title available',
          url: articleUrl,
          publishedAt: item.publishedAt || new Date().toISOString(),
          source: {
            name: item.source || 'Unknown Source'
          },
          description: item.description || '',
          sentiment: item.sentiment ? {
            score: item.sentiment.compound || 0,
            label: item.sentiment.label || 'Neutral'
          } : undefined
        }
      }) || []
      
      setArticles(transformedArticles.slice(0, 20)) // Limit to 20 articles
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      if (!isRefreshing) setLoading(false)
    }
  }

  useEffect(() => {
    if (symbol) {
      fetchNews()
    }
  }, [symbol, API_BASE_URL])

  if (loading) {
    return (
      <div className={`bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl p-4 sm:p-6 ${className}`}>
        <div className="flex items-center gap-2 sm:gap-3 mb-4 sm:mb-6">
          <Newspaper className="h-5 w-5 sm:h-6 sm:w-6 text-purple-400" />
          <h2 className="text-lg sm:text-xl font-semibold text-white">Latest News</h2>
        </div>
        
        <div className="space-y-3 sm:space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-white/5 rounded-lg p-3 sm:p-4 animate-pulse">
              <div className="h-3 sm:h-4 bg-white/10 rounded w-3/4 mb-2"></div>
              <div className="h-2 sm:h-3 bg-white/10 rounded w-1/2 mb-2"></div>
              <div className="h-2 sm:h-3 bg-white/10 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl p-4 sm:p-6 ${className}`}>
        <div className="flex items-center gap-2 sm:gap-3 mb-4">
          <Newspaper className="h-5 w-5 sm:h-6 sm:w-6 text-purple-400" />
          <h2 className="text-lg sm:text-xl font-semibold text-white">Latest News</h2>
        </div>
        <div className="text-center py-6 sm:py-8">
          <p className="text-red-400 mb-2 text-sm sm:text-base">Failed to load news</p>
          <p className="text-gray-400 text-xs sm:text-sm">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div 
        ref={containerRef}
        className={`bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl p-3 sm:p-6 ${className} overflow-y-auto max-h-[80vh] lg:max-h-none`}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Header with refresh button - Mobile optimized */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-3 mb-4 sm:mb-6">
          <div className="flex items-center gap-2 sm:gap-3">
            <Newspaper className="h-5 w-5 sm:h-6 sm:w-6 text-purple-400" />
            <h2 className="text-lg sm:text-xl font-semibold text-white">Latest News</h2>
            <span className="text-xs sm:text-sm text-white/60">for {symbol}</span>
          </div>
          
          <button
            onClick={handleRefresh}
            disabled={isRefreshing || loading}
            className="flex items-center gap-2 px-3 py-2 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 rounded-lg text-white text-sm transition-all disabled:opacity-50 touch-manipulation self-start sm:self-auto"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>

        {/* Pull-to-refresh indicator for mobile */}
        <div className="lg:hidden text-center text-white/40 text-xs mb-4">
          Pull down to refresh
        </div>

        {/* Filter and Sort Bar - Mobile responsive */}
        <FilterSortBar
          filters={filters}
          onFilterChange={handleFilterChange}
          sortOptions={sortOptions}
          currentSort={currentSort}
          onSortChange={handleSortChange}
          resultCount={filteredAndSortedArticles.length}
          className="mb-4 sm:mb-6"
        />

        {/* Articles Grid - Enhanced mobile layout */}
        {filteredAndSortedArticles.length === 0 ? (
          <div className="text-center py-6 sm:py-8">
            <Newspaper className="h-12 w-12 text-white/20 mx-auto mb-4" />
            <p className="text-white/60 text-sm sm:text-base">No news articles found with current filters</p>
          </div>
        ) : (
          <div className="space-y-3 sm:space-y-4 lg:grid lg:gap-4 lg:grid-cols-2 lg:space-y-0">
            {filteredAndSortedArticles.map((article, index) => (
              <EnhancedNewsCard
                key={`${article.url}-${index}`}
                article={article}
                isSaved={savedArticles.has(article.url)}
                isExpanded={expandedArticles.has(article.url)}
                onToggleSave={() => toggleSaveArticle(article.url)}
                onToggleExpand={() => toggleExpandArticle(article.url)}
                onOpenFullscreen={() => openFullscreen(article)}
              />
            ))}
          </div>
        )}

        {/* Show saved articles count */}
        {savedArticles.size > 0 && (
          <div className="mt-6 pt-4 border-t border-white/10">
            <p className="text-sm text-white/60 text-center">
              📚 {savedArticles.size} article{savedArticles.size !== 1 ? 's' : ''} saved for later
            </p>
          </div>
        )}
      </div>

      {/* Fullscreen Article Modal for Mobile */}
      {showFullscreen && selectedArticle && (
        <div className="lg:hidden fixed inset-0 bg-black/95 backdrop-blur-sm z-50 flex flex-col">
          <div className="flex items-center justify-between p-4 border-b border-white/10">
            <h3 className="text-lg font-semibold text-white truncate pr-4">Article Preview</h3>
            <button
              onClick={() => setShowFullscreen(false)}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white touch-manipulation"
            >
              ✕
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            <div className="max-w-2xl mx-auto">
              <h2 className="text-xl font-bold text-white mb-3">{selectedArticle.title}</h2>
              
              <div className="flex items-center gap-3 mb-4 text-sm text-white/70">
                <span>{selectedArticle.source.name}</span>
                <span>•</span>
                <span>{new Date(selectedArticle.publishedAt).toLocaleDateString()}</span>
              </div>
              
              {selectedArticle.description && (
                <p className="text-white/90 mb-6 leading-relaxed">{selectedArticle.description}</p>
              )}
              
              <div className="flex flex-col gap-3">
                <button
                  onClick={() => window.open(selectedArticle.url, '_blank')}
                  className="flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white py-3 px-6 rounded-lg transition-colors touch-manipulation"
                >
                  <ExternalLink className="h-4 w-4" />
                  Read Full Article
                </button>
                
                <button
                  onClick={() => {
                    toggleSaveArticle(selectedArticle.url)
                    setShowFullscreen(false)
                  }}
                  className="flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 text-white py-3 px-6 rounded-lg transition-colors touch-manipulation"
                >
                  {savedArticles.has(selectedArticle.url) ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
                  {savedArticles.has(selectedArticle.url) ? 'Saved' : 'Save for Later'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

// Enhanced News Card Component with mobile features
function EnhancedNewsCard({
  article,
  isSaved,
  isExpanded,
  onToggleSave,
  onToggleExpand,
  onOpenFullscreen
}: {
  article: NewsArticle
  isSaved: boolean
  isExpanded: boolean
  onToggleSave: () => void
  onToggleExpand: () => void
  onOpenFullscreen: () => void
}) {
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${diffInHours}h ago`
    
    const diffInDays = Math.floor(diffInHours / 24)
    if (diffInDays < 7) return `${diffInDays}d ago`
    
    return date.toLocaleDateString()
  }

  const getSentimentColor = (score?: number) => {
    if (!score) return 'text-gray-400'
    if (score > 0.1) return 'text-green-400'
    if (score < -0.1) return 'text-red-400'
    return 'text-yellow-400'
  }

  const getSentimentIcon = (score?: number) => {
    if (!score) return '➡️'
    if (score > 0.1) return '📈'
    if (score < -0.1) return '📉'
    return '➡️'
  }

  return (
    <div className="bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition-all duration-200 overflow-hidden">
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <h3 
              className="font-semibold text-white mb-2 line-clamp-2 leading-tight cursor-pointer hover:text-purple-300 transition-colors"
              onClick={() => window.innerWidth < 1024 ? onOpenFullscreen() : window.open(article.url, '_blank')}
            >
              {article.title}
            </h3>
            
            <div className="flex items-center gap-2 text-sm text-white/60 mb-3">
              <span className="truncate">{article.source.name}</span>
              <span>•</span>
              <span>{formatRelativeTime(article.publishedAt)}</span>
              
              {article.sentiment && (
                <>
                  <span>•</span>
                  <span className={`flex items-center gap-1 ${getSentimentColor(article.sentiment.score)}`}>
                    {getSentimentIcon(article.sentiment.score)}
                    <span className="hidden sm:inline">{article.sentiment.label}</span>
                  </span>
                </>
              )}
            </div>

            {/* Description - expandable on mobile */}
            {article.description && (
              <p className={`text-white/80 text-sm leading-relaxed ${
                isExpanded ? '' : 'line-clamp-2'
              }`}>
                {article.description}
              </p>
            )}
          </div>

          {/* Save button */}
          <button
            onClick={onToggleSave}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors touch-manipulation"
            title={isSaved ? 'Unsave article' : 'Save for later'}
          >
            {isSaved ? (
              <BookmarkCheck className="h-4 w-4 text-purple-400" />
            ) : (
              <Bookmark className="h-4 w-4 text-white/60" />
            )}
          </button>
        </div>

        {/* Mobile action buttons */}
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-white/10">
          {article.description && (
            <button
              onClick={onToggleExpand}
              className="text-xs text-purple-400 hover:text-purple-300 transition-colors touch-manipulation"
            >
              {isExpanded ? 'Show less' : 'Show more'}
            </button>
          )}
          
          <div className="flex-1"></div>
          
          {/* Desktop - direct link, Mobile - fullscreen */}
          <button
            onClick={() => window.innerWidth < 1024 ? onOpenFullscreen() : window.open(article.url, '_blank')}
            className="flex items-center gap-1 text-xs text-white/60 hover:text-white transition-colors touch-manipulation"
          >
            <ExternalLink className="h-3 w-3" />
            <span className="hidden sm:inline">Read More</span>
            <span className="sm:hidden">Read</span>
          </button>
        </div>
      </div>
    </div>
  )
}
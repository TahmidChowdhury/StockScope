'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { Newspaper, RefreshCw, ExternalLink } from 'lucide-react'
import FilterSortBar from './FilterSortBar'

interface NewsArticle {
  title: string
  url: string
  publishedAt: string
  username?: string
  message_id?: number | string
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

const getArticleId = (article: Pick<NewsArticle, 'url' | 'publishedAt' | 'title' | 'source'>) => {
  return article.url || `${article.source.name}:${article.publishedAt}:${article.title}`
}

function getSourceIcon(source: string): string {
  const s = source.toLowerCase()
  if (s.includes('yahoo')) return '📰'
  if (s.includes('stocktwits')) return '💬'
  if (s.includes('seeking alpha') || s.includes('seekingalpha')) return '🔭'
  if (s.includes('finviz')) return '📊'
  if (s.includes('reuters')) return '📡'
  if (s.includes('bloomberg')) return '💼'
  if (s.includes('cnbc')) return '📺'
  if (s.includes('marketwatch')) return '📈'
  if (s.includes('benzinga')) return '⚡'
  if (s.includes('motley')) return '🎯'
  if (s.includes('google')) return '🔍'
  if (s.includes('cnn')) return '🏛️'
  if (s.includes('thestreet')) return '🏦'
  return '🗞️'
}

export default function NewsComponent({ symbol, className = '' }: NewsComponentProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Dynamic source filtering — built from whatever sources are actually in the data
  const [disabledSources, setDisabledSources] = useState<Set<string>>(new Set())

  // Derive available sources from loaded articles
  const availableSources = useMemo((): FilterOption[] => {
    const seen = new Map<string, string>() // sourceName → icon
    articles.forEach(a => {
      const name = a.source.name
      if (name && !seen.has(name)) {
        seen.set(name, getSourceIcon(name))
      }
    })
    return Array.from(seen.entries()).map(([name, icon]) => ({
      id: name,
      label: name,
      icon,
      enabled: !disabledSources.has(name)
    }))
  }, [articles, disabledSources])
  
  const [currentSort, setCurrentSort] = useState('date-desc')
  
  const sortOptions: SortOption[] = [
    { id: 'date-desc', label: 'Latest First', direction: 'desc' },
    { id: 'date-asc', label: 'Oldest First', direction: 'asc' },
    { id: 'sentiment-desc', label: 'Most Positive', direction: 'desc' },
    { id: 'sentiment-asc', label: 'Most Negative', direction: 'asc' }
  ]

  // Mobile-specific state
  const [isRefreshing, setIsRefreshing] = useState(false)
  const refreshStartY = useRef(0)
  const refreshDistance = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)

  // Filtered and sorted articles using dynamic source set
  const filteredAndSortedArticles = useMemo(() => {
    const filtered = articles.filter(article => !disabledSources.has(article.source.name))

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
  }, [articles, disabledSources, currentSort])

  const handleFilterChange = (filterId: string, enabled: boolean) => {
    setDisabledSources(prev => {
      const next = new Set(prev)
      if (enabled) {
        next.delete(filterId)
      } else {
        next.add(filterId)
      }
      return next
    })
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
    await fetchNews()
    setTimeout(() => setIsRefreshing(false), 500)
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

      const isGenericStocktwitsUrl = (url: string) => {
        const normalizedUrl = url.trim().replace(/\/+$/, '').toLowerCase()
        return [
          'https://stocktwits.com',
          'http://stocktwits.com',
          'https://www.stocktwits.com',
          'http://www.stocktwits.com',
          'https://stocktwits.com/mobile',
          'http://stocktwits.com/mobile',
          'https://www.stocktwits.com/mobile',
          'http://www.stocktwits.com/mobile'
        ].includes(normalizedUrl)
      }
      
      // Transform the articles to match our interface
      const transformedArticles = data.articles?.map((item: { 
        title?: string; 
        url?: string; 
        publishedAt?: string; 
        source?: string; 
        username?: string;
        message_id?: number | string;
        description?: string; 
        sentiment?: { compound?: number; label?: string }
      }) => {
        // Handle missing or invalid URLs better
        let articleUrl = item.url || ''
        const sourceName = (item.source || '').toLowerCase()

        if (sourceName.includes('stocktwits') && item.username && item.message_id) {
          articleUrl = `https://stocktwits.com/${item.username}/message/${item.message_id}`
        }
        
        // If no URL provided, create appropriate fallback based on source
        if (
          !articleUrl ||
          articleUrl === '#' ||
          articleUrl === 'null' ||
          (sourceName.includes('stocktwits') && isGenericStocktwitsUrl(articleUrl))
        ) {
          articleUrl = ''
        }
        
        return {
          title: item.title || 'No title available',
          url: articleUrl,
          publishedAt: item.publishedAt || new Date().toISOString(),
          username: item.username,
          message_id: item.message_id,
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
  }, [symbol]) // eslint-disable-line react-hooks/exhaustive-deps

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
          filters={availableSources}
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
                key={`${getArticleId(article)}-${index}`}
                article={article}
              />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

// News Card Component
function EnhancedNewsCard({ article }: { article: NewsArticle }) {
  const hasLink = Boolean(article.url)

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

  // Deduplicate: skip description if it's the same text as the title
  const showDescription =
    article.description && article.description.trim() !== article.title.trim()

  const CardWrapper = hasLink
    ? ({ children }: { children: React.ReactNode }) => (
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 hover:border-purple-500/30 transition-all duration-200 overflow-hidden"
        >
          {children}
        </a>
      )
    : ({ children }: { children: React.ReactNode }) => (
        <div className="bg-white/5 rounded-lg border border-white/10 overflow-hidden opacity-80">
          {children}
        </div>
      )

  return (
    <CardWrapper>
      <div className="p-4">
        {/* Title */}
        <h3 className={`font-semibold mb-2 line-clamp-2 leading-tight ${
          hasLink ? 'text-white group-hover:text-purple-300' : 'text-white/70'
        }`}>
          {article.title}
        </h3>

        {/* Meta row */}
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

        {/* Description (only if different from title) */}
        {showDescription && (
          <p className="text-white/80 text-sm leading-relaxed line-clamp-3 mb-3">
            {article.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex justify-end pt-2 border-t border-white/10">
          {hasLink ? (
            <span className="inline-flex items-center gap-1 text-xs text-purple-400">
              <ExternalLink className="h-3 w-3" />
              Read article
            </span>
          ) : (
            <span className="text-xs text-white/30">No link available</span>
          )}
        </div>
      </div>
    </CardWrapper>
  )
}

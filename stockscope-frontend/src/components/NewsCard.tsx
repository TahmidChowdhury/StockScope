'use client'

import { ExternalLink, Calendar, TrendingUp, TrendingDown } from 'lucide-react'
import SentimentBadge, { SentimentProgress } from './SentimentBadge'

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

interface NewsCardProps {
  article: NewsArticle
  className?: string
  showSentiment?: boolean
  variant?: 'default' | 'compact' | 'detailed'
}

export default function NewsCard({ 
  article, 
  className = '', 
  showSentiment = true,
  variant = 'default'
}: NewsCardProps) {
  
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${diffInHours}h ago`
    if (diffInHours < 48) return 'Yesterday'
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    })
  }

  const getSourceIcon = (sourceName: string) => {
    const source = sourceName.toLowerCase()
    if (source.includes('yahoo')) return '📰'
    if (source.includes('motley')) return '🎯'
    if (source.includes('reuters')) return '📊'
    if (source.includes('bloomberg')) return '💼'
    return '🗞️'
  }

  // Compact variant for mobile or sidebars
  if (variant === 'compact') {
    return (
      <div className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-all duration-200 ${className}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-white line-clamp-2 mb-2">
              {article.title}
            </h3>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span>{getSourceIcon(article.source.name)} {article.source.name}</span>
              <span>•</span>
              <span>{formatDate(article.publishedAt)}</span>
            </div>
          </div>
          {showSentiment && article.sentiment && (
            <SentimentBadge 
              score={article.sentiment.score} 
              size="sm" 
              showIcon={false}
            />
          )}
        </div>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute inset-0 z-10"
          aria-label={`Read article: ${article.title}`}
        />
      </div>
    )
  }

  // Detailed variant with full description and sentiment progress
  if (variant === 'detailed') {
    return (
      <article className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 hover:bg-white/8 hover:border-white/20 transition-all duration-200 group ${className}`}>
        {/* Header with source and time */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span>{getSourceIcon(article.source.name)} {article.source.name}</span>
            <span>•</span>
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>{formatDate(article.publishedAt)}</span>
            </div>
          </div>
          {showSentiment && article.sentiment && (
            <SentimentBadge 
              score={article.sentiment.score} 
              showScore 
              className="flex-shrink-0"
            />
          )}
        </div>

        {/* Title */}
        <h3 className="text-xl font-semibold text-white mb-3 group-hover:text-purple-200 transition-colors">
          {article.title}
        </h3>

        {/* Description */}
        {article.description && (
          <p className="text-sm text-gray-300 mb-4 line-clamp-3">
            {article.description}
          </p>
        )}

        {/* Sentiment Progress Bar */}
        {showSentiment && article.sentiment && (
          <div className="mb-4">
            <SentimentProgress score={article.sentiment.score} />
          </div>
        )}

        {/* Read More Button */}
        <div className="flex justify-end">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-purple-300 hover:text-purple-200 text-sm font-medium transition-colors"
          >
            Read Full Article
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </article>
    )
  }

  // Default variant - balanced view
  return (
    <article className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-5 hover:bg-white/8 hover:border-white/20 transition-all duration-200 group relative ${className}`}>
      {/* Header with sentiment and source */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <span>{getSourceIcon(article.source.name)} {article.source.name}</span>
          <span>•</span>
          <span>{formatDate(article.publishedAt)}</span>
        </div>
        {showSentiment && article.sentiment && (
          <SentimentBadge 
            score={article.sentiment.score} 
            size="sm"
            className="flex-shrink-0"
          />
        )}
      </div>

      {/* Title */}
      <h3 className="text-lg font-semibold text-white mb-3 line-clamp-2 group-hover:text-purple-200 transition-colors">
        {article.title}
      </h3>

      {/* Description */}
      {article.description && (
        <p className="text-sm text-gray-300 mb-4 line-clamp-2">
          {article.description}
        </p>
      )}

      {/* Read More Link */}
      <div className="flex justify-between items-center">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-purple-300 hover:text-purple-200 text-sm font-medium transition-colors z-20 relative"
        >
          Read More
          <ExternalLink className="h-3 w-3" />
        </a>
        
        {/* Sentiment Progress (if available) */}
        {showSentiment && article.sentiment && (
          <div className="w-20">
            <SentimentProgress score={article.sentiment.score} />
          </div>
        )}
      </div>

      {/* Full card clickable area */}
    </article>
  )
}
'use client'

import { MessageSquare, Heart, Share, TrendingUp, ExternalLink } from 'lucide-react'
import SentimentBadge from './SentimentBadge'

interface SocialMessage {
  id: string
  content: string
  author: string
  timestamp: string
  source: 'reddit' | 'stocktwits' | 'twitter'
  url?: string
  engagement?: {
    likes?: number
    shares?: number
    comments?: number
  }
  sentiment?: {
    score: number
    label: string
  }
}

interface SocialCardProps {
  message: SocialMessage
  className?: string
  showSentiment?: boolean
  variant?: 'default' | 'compact'
}

export default function SocialCard({ 
  message, 
  className = '', 
  showSentiment = true,
  variant = 'default'
}: SocialCardProps) {
  
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))
    
    if (diffInMinutes < 1) return 'Just now'
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'reddit': return '🔴'
      case 'stocktwits': return '💬'
      case 'twitter': return '🐦'
      default: return '💭'
    }
  }

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'reddit': return 'text-orange-400 border-orange-500/30'
      case 'stocktwits': return 'text-blue-400 border-blue-500/30'
      case 'twitter': return 'text-cyan-400 border-cyan-500/30'
      default: return 'text-gray-400 border-gray-500/30'
    }
  }

  // Compact variant for dense layouts
  if (variant === 'compact') {
    return (
      <div className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4 hover:bg-white/8 transition-all duration-200 ${className}`}>
        <div className="flex items-start gap-3">
          {/* Author avatar placeholder */}
          <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {message.author.charAt(0).toUpperCase()}
          </div>
          
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-white truncate">@{message.author}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${getSourceColor(message.source)}`}>
                {getSourceIcon(message.source)} {message.source}
              </span>
              <span className="text-xs text-gray-500">{formatTime(message.timestamp)}</span>
            </div>
            
            {/* Content */}
            <p className="text-sm text-gray-300 line-clamp-2 mb-2">
              {message.content}
            </p>
            
            {/* Footer */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs text-gray-400">
                {message.engagement?.likes && (
                  <span className="flex items-center gap-1">
                    <Heart className="h-3 w-3" />
                    {message.engagement.likes}
                  </span>
                )}
                {message.engagement?.comments && (
                  <span className="flex items-center gap-1">
                    <MessageSquare className="h-3 w-3" />
                    {message.engagement.comments}
                  </span>
                )}
              </div>
              
              {showSentiment && message.sentiment && (
                <SentimentBadge 
                  score={message.sentiment.score} 
                  size="sm" 
                  showIcon={false}
                />
              )}
            </div>
          </div>
        </div>
        
        {message.url && (
          <a
            href={message.url}
            target="_blank"
            rel="noopener noreferrer"
            className="absolute inset-0 z-10"
            aria-label={`View post by ${message.author}`}
          />
        )}
      </div>
    )
  }

  // Default variant with full features
  return (
    <article className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 hover:bg-white/8 hover:border-white/20 transition-all duration-200 group relative ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {/* Author avatar */}
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-white font-bold">
            {message.author.charAt(0).toUpperCase()}
          </div>
          
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-white">@{message.author}</span>
              <span className={`text-xs px-2 py-1 rounded-full border ${getSourceColor(message.source)}`}>
                {getSourceIcon(message.source)} {message.source}
              </span>
            </div>
            <span className="text-sm text-gray-400">{formatTime(message.timestamp)}</span>
          </div>
        </div>
        
        {showSentiment && message.sentiment && (
          <SentimentBadge 
            score={message.sentiment.score} 
            showScore 
            className="flex-shrink-0"
          />
        )}
      </div>

      {/* Content */}
      <div className="mb-4">
        <p className="text-gray-200 leading-relaxed">
          {message.content}
        </p>
      </div>

      {/* Engagement and Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-white/10">
        <div className="flex items-center gap-6 text-sm text-gray-400">
          {message.engagement?.likes && (
            <button className="flex items-center gap-2 hover:text-red-400 transition-colors">
              <Heart className="h-4 w-4" />
              <span>{message.engagement.likes}</span>
            </button>
          )}
          
          {message.engagement?.comments && (
            <button className="flex items-center gap-2 hover:text-blue-400 transition-colors">
              <MessageSquare className="h-4 w-4" />
              <span>{message.engagement.comments}</span>
            </button>
          )}
          
          {message.engagement?.shares && (
            <button className="flex items-center gap-2 hover:text-green-400 transition-colors">
              <Share className="h-4 w-4" />
              <span>{message.engagement.shares}</span>
            </button>
          )}
        </div>
        
        {message.url && (
          <a
            href={message.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-purple-300 hover:text-purple-200 text-sm font-medium transition-colors z-20 relative"
          >
            View Post
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>
    </article>
  )
}
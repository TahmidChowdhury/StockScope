'use client'

import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface SentimentBadgeProps {
  score: number
  label?: string
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
  showScore?: boolean
  className?: string
}

export default function SentimentBadge({ 
  score, 
  label, 
  size = 'md', 
  showIcon = true, 
  showScore = false,
  className = '' 
}: SentimentBadgeProps) {
  
  // Determine sentiment category and colors
  const getSentimentData = (score: number) => {
    if (score >= 0.1) {
      return {
        category: 'positive',
        label: label || 'Positive',
        bgColor: 'bg-green-500/20',
        textColor: 'text-green-400',
        borderColor: 'border-green-500/40',
        icon: TrendingUp
      }
    } else if (score <= -0.1) {
      return {
        category: 'negative',
        label: label || 'Negative',
        bgColor: 'bg-red-500/20',
        textColor: 'text-red-400',
        borderColor: 'border-red-500/40',
        icon: TrendingDown
      }
    } else {
      return {
        category: 'neutral',
        label: label || 'Neutral',
        bgColor: 'bg-gray-500/20',
        textColor: 'text-gray-400',
        borderColor: 'border-gray-500/40',
        icon: Minus
      }
    }
  }

  const sentiment = getSentimentData(score)
  const Icon = sentiment.icon

  // Size variations
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base'
  }

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5'
  }

  return (
    <div className={`
      inline-flex items-center gap-1.5 rounded-full border
      ${sentiment.bgColor} ${sentiment.textColor} ${sentiment.borderColor}
      ${sizeClasses[size]} font-medium transition-all duration-200
      hover:bg-opacity-30 ${className}
    `}>
      {showIcon && <Icon className={iconSizes[size]} />}
      <span>{sentiment.label}</span>
      {showScore && (
        <span className="opacity-75">
          ({score > 0 ? '+' : ''}{score.toFixed(2)})
        </span>
      )}
    </div>
  )
}

// Progress bar variant for detailed sentiment display
interface SentimentProgressProps {
  score: number
  className?: string
}

export function SentimentProgress({ score, className = '' }: SentimentProgressProps) {
  // Convert score from -1 to 1 range to 0-100 percentage
  const percentage = ((score + 1) / 2) * 100
  
  const getGradientColor = (score: number) => {
    if (score >= 0.1) return 'from-red-500 via-yellow-500 to-green-500'
    if (score <= -0.1) return 'from-red-500 via-yellow-500 to-green-500'
    return 'from-red-500 via-yellow-500 to-green-500'
  }

  return (
    <div className={`w-full ${className}`}>
      <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
        <span>Sentiment</span>
        <span>{score > 0 ? '+' : ''}{score.toFixed(2)}</span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div 
          className={`h-full bg-gradient-to-r ${getGradientColor(score)} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
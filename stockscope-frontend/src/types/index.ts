// Core data types for StockScope Pro

export interface StockMetadata {
  symbol: string
  total_posts: number
  avg_sentiment: number
  last_updated: string
  sources: string[]
}

export interface StockSuggestion {
  symbol: string
  name: string
  sector?: string
}

export interface SentimentData {
  date: string
  sentiment: number
  source: string
  title?: string
  content?: string
}

export interface StockAnalysis {
  symbol: string
  total_posts: number
  avg_sentiment: number
  positive_posts: number
  negative_posts: number
  neutral_posts: number
  last_updated: string
  sources: string[]
  recent_posts: SentimentData[]
  sentiment_over_time: SentimentData[]
}

export interface InvestmentAdvice {
  symbol: string
  recommendation: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH'
  target_price?: number
  reasoning: string[]
  factors: {
    positive: string[]
    negative: string[]
    neutral: string[]
  }
}

export interface QuantitativeAnalysis {
  symbol: string
  metrics: {
    sharpe_ratio?: number
    volatility?: number
    beta?: number
    alpha?: number
  }
  signals: {
    rsi?: number
    macd?: number
    bollinger_bands?: string
  }
  recommendation: string
  confidence: number
}

export interface APIResponse<T> {
  data: T
  status: 'success' | 'error'
  message?: string
}

export interface StockSearchProps {
  onAnalyze: (symbol: string) => void
  isLoading?: boolean
}

export interface StockDashboardProps {
  symbol: string
  onBack: () => void
}

export interface PortfolioViewProps {
  onViewDashboard: (symbol: string) => void
}

export type ViewType = 'search' | 'dashboard'

export interface AnalysisStatus {
  symbol: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  message?: string
}
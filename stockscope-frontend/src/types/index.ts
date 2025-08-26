// Core data types for StockScope Pro

// Simplified authentication types
export interface LoginRequest {
  password: string
}

export interface SimpleAuthResponse {
  success: boolean
  message: string
}

export interface AuthState {
  isAuthenticated: boolean
}

export interface StockMetadata {
  symbol: string
  companyName?: string
  currentPrice?: number
  priceChange?: number
  priceChangePercent?: number
  total_posts: number
  avg_sentiment: number
  last_updated: string
  sources: string[] // This endpoint returns simple strings
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

// Backend returns SourceAnalysis objects for the analysis endpoint
export interface SourceAnalysis {
  source: string
  count: number
  avg_sentiment: number
  latest_update: string
}

export interface SentimentMetrics {
  avg_sentiment: number
  sentiment_distribution: {
    positive: number
    neutral: number
    negative: number
  }
  confidence_score: number
  trend: string
}

export interface StockAnalysis {
  ticker: string // Backend uses 'ticker' not 'symbol'
  total_posts: number
  sentiment_metrics: SentimentMetrics
  sources: SourceAnalysis[] // This endpoint returns SourceAnalysis objects
  last_updated: string
  data_quality_score: number
  // Legacy fields for backward compatibility
  symbol?: string
  avg_sentiment?: number
  positive_posts?: number
  negative_posts?: number
  neutral_posts?: number
  recent_posts?: SentimentData[]
  sentiment_over_time?: SentimentData[]
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

export interface StockData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface AnalysisResult {
  ticker: string;
  total_posts: number;
  sentiment_metrics: {
    avg_sentiment: number;
    sentiment_distribution: {
      positive: number;
      neutral: number;
      negative: number;
    };
    confidence_score: number;
    trend: string;
  };
  sources: Array<{
    source: string;
    count: number;
    avg_sentiment: number;
    latest_update: string;
  }>;
  last_updated: string;
  data_quality_score: number;
}

// Fundamentals Analytics Types
export interface FundamentalPoint {
  date: string;
  value: number | null;
}

export interface FundamentalsSeries {
  revenue_q: FundamentalPoint[];
  operating_income_q: FundamentalPoint[];
  operating_margin_q: FundamentalPoint[];
  fcf_q: FundamentalPoint[];
  fcf_margin_q: FundamentalPoint[];
  ebitda_q: FundamentalPoint[];
}

export interface FundamentalsTTM {
  ticker: string;
  revenue_ttm: number | null;
  operating_income_ttm: number | null;
  operating_margin_ttm: number | null;
  fcf_ttm: number | null;
  fcf_margin_ttm: number | null;
  ebitda_ttm: number | null;
  revenue_growth_yoy: number | null;
  fcf_growth_yoy: number | null;
  ebitda_growth_yoy: number | null;
  margin_growth_yoy_pp: number | null;
  debt_to_cash: number | null;
  insufficient_data: boolean;
}

export interface FundamentalsResponse {
  ttm: FundamentalsTTM;
  series: FundamentalsSeries;
}

export interface CompareRequest {
  tickers: string[];
}

export interface ScreenerRequest {
  universe?: string[];
  min_revenue_growth_yoy?: number;
  min_fcf_growth_yoy?: number;
  min_margin_growth_yoy_pp?: number;
  min_ebitda_growth_yoy?: number;
  max_debt_to_cash?: number;
  limit?: number;
  sort_by?: string;
  sort_dir?: string;
}

export interface ScreenerResponse {
  results: FundamentalsTTM[];
  total_screened: number;
  filters_applied: Record<string, string | number | boolean | null | undefined>;
}
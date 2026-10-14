// Core data types for StockScope Pro

// Simplified authentication types
export interface LoginRequest {
  password: string
}

export interface SimpleAuthResponse {
  success: boolean
  message: string
  role: 'admin' | 'demo' | 'guest'
  access_token: string
  token_type: 'bearer'
  expires_in_seconds: number
}

export interface AuthState {
  isAuthenticated: boolean
}

export interface StockMetadata {
  symbol: string
  companyName?: string
  price_as_of?: string | null
  currentPrice?: number | null
  priceChange?: number | null
  priceChangePercent?: number | null
  total_posts: number
  avg_sentiment: number | null
  last_updated: string | null
  freshness?: DataFreshness
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
export type DataFreshness = 'recent' | 'stale' | 'unknown'

export interface SourceAnalysis {
  source: string
  count: number
  avg_sentiment: number | null
  latest_update: string | null
  freshness: DataFreshness
  unknown_timestamps: number
}

export interface FilingEvent {
  form_type: string
  filing_date: string | null
  url: string
  description: string
}

// Enhanced interfaces for new components
export interface NewsArticle {
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

export interface SocialMessage {
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

export interface FilterOption {
  id: string
  label: string
  icon?: string
  enabled: boolean
}

export interface SortOption {
  id: string
  label: string
  direction: 'asc' | 'desc'
}

export interface SentimentMetrics {
  avg_sentiment: number | null
  sentiment_distribution: { positive: number; neutral: number; negative: number }
  trend: 'positive' | 'negative' | 'neutral' | 'unavailable'
  sample_size: number
  method: string
}

export interface StockAnalysis {
  ticker: string
  total_posts: number
  sentiment_metrics: SentimentMetrics
  sources: SourceAnalysis[]
  last_updated: string | null
  source_as_of: string | null
  freshness: DataFreshness
  generated_at: string
  filings: FilingEvent[]
}

export interface InvestmentAdvice {
  ticker: string
  status: 'research_only'
  summary: string
  observations: string[]
  limitations: string[]
  sources: SourceAnalysis[]
  as_of: string | null
  generated_at: string
  filings: FilingEvent[]
}

export interface QuantitativeAnalysis {
  symbol: string
  status: 'unavailable'
  reason: string
  metrics: Record<string, never>
  signals: Record<string, never>
  strategies?: Record<string, never>
}

export interface APIResponse<T> {
  data: T
  status: 'success' | 'error'
  message?: string
}

export interface StockSearchProps {
  onAnalyze: (symbol: string) => void
  isLoading?: boolean
  compact?: boolean
}

export interface StockDashboardProps {
  symbol: string
  onBack: () => void
  embedded?: boolean
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

export type AnalysisResult = StockAnalysis

// Fundamentals Analytics Types
export interface FundamentalPoint {
  date: string;
  value: number | null;
}

export interface FundamentalsSeries {
  revenue_q?: FundamentalPoint[];
  operating_income_q?: FundamentalPoint[];
  operating_margin_q?: FundamentalPoint[];
  fcf_q?: FundamentalPoint[];
  fcf_margin_q?: FundamentalPoint[];
  ebitda_q?: FundamentalPoint[];
}

export interface GrowthBasis {
  basis: 'ttm' | 'fiscal_year' | 'unavailable';
  status: 'available' | 'non_positive_prior' | 'insufficient_history';
  current_period_end?: string;
  prior_period_end?: string;
  absolute_change?: number;
}

export interface FundamentalsTTM {
  ticker: string;
  revenue_ttm?: number | null;
  operating_income_ttm?: number | null;
  operating_margin_ttm?: number | null;
  fcf_ttm?: number | null;
  fcf_margin_ttm?: number | null;
  ebitda_ttm?: number | null;
  revenue_growth_yoy?: number | null;
  fcf_growth_yoy?: number | null;
  ebitda_growth_yoy?: number | null;
  margin_growth_yoy_pp?: number | null;
  debt_to_cash?: number | null;
  insufficient_data: boolean;
  growth_metadata?: Record<string, GrowthBasis>;
  period_metadata?: Record<string, { basis: string; quarter_ends: string[]; period_end: string }>;
}

export interface FundamentalsResponse {
  ttm: FundamentalsTTM;
  series: FundamentalsSeries;
  metadata?: { source?: string; retrieved_at?: string };
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
  total_attempted: number;
  total_failed: number;
  total_insufficient: number;
  total_evaluated: number;
  total_matches: number;
  universe_name: string;
  universe_as_of?: string | null;
  filters_applied: Record<string, string | number | boolean | null | undefined>;
}
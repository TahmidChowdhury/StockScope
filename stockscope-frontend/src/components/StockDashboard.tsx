'use client'

import { useState, useEffect, useCallback } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { TrendingUp, TrendingDown, Activity, MessageSquare, Newspaper, Building2, X, AlertCircle, Target, Shield } from 'lucide-react'
import type { StockDashboardProps, StockAnalysis, InvestmentAdvice, QuantitativeAnalysis } from '@/types'

export default function StockDashboard({ symbol, onBack }: StockDashboardProps) {
  const [stockData, setStockData] = useState<StockAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // New state for button functionality
  const [investmentAdvice, setInvestmentAdvice] = useState<InvestmentAdvice | null>(null)
  const [quantAnalysis, setQuantAnalysis] = useState<QuantitativeAnalysis | null>(null)
  const [showAdviceModal, setShowAdviceModal] = useState(false)
  const [showAnalysisModal, setShowAnalysisModal] = useState(false)
  const [showNewsModal, setShowNewsModal] = useState(false)
  const [loadingAdvice, setLoadingAdvice] = useState(false)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)

  // New state for delete functionality
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [userRole, setUserRole] = useState<string>('')

  // New state for company information
  const [companyInfo, setCompanyInfo] = useState<{displayName?: string} | null>(null)

  // Get API URL from environment variables
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Get password for API calls
  const getPasswordParam = () => {
    const password = localStorage.getItem('stockscope_password')
    return password ? `?password=${encodeURIComponent(password)}` : ''
  }

  // Function to fetch company information - memoized to prevent infinite loops
  const fetchCompanyInfo = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/info${getPasswordParam()}`)
      if (response.ok) {
        const data = await response.json()
        setCompanyInfo(data)
      }
    } catch (error) {
      console.error('Error fetching company info:', error)
      // Don't show error for this, just use symbol if company name fails
    }
  }, [API_BASE_URL, symbol])

  useEffect(() => {
    const fetchStockData = async () => {
      try {
        setLoading(true)
        setError(null)
        
        // Fetch both stock data and company info in parallel
        const [stockResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/stocks/${symbol}${getPasswordParam()}`),
          fetchCompanyInfo() // This handles its own errors
        ])
        
        if (!stockResponse.ok) {
          throw new Error(`Failed to fetch data for ${symbol}`)
        }
        
        const data = await stockResponse.json()
        setStockData(data)
      } catch (error) {
        console.error('Error fetching stock data:', error)
        setError(error instanceof Error ? error.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchStockData()
  }, [symbol, API_BASE_URL, fetchCompanyInfo])

  const refetchStockData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch both stock data and company info in parallel
      const [stockResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/stocks/${symbol}${getPasswordParam()}`),
        fetchCompanyInfo() // This handles its own errors
      ])
      
      if (!stockResponse.ok) {
        throw new Error(`Failed to fetch data for ${symbol}`)
      }
      
      const data = await stockResponse.json()
      setStockData(data)
    } catch (error) {
      console.error('Error fetching stock data:', error)
      setError(error instanceof Error ? error.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  // New function to get investment advice
  const getInvestmentAdvice = async () => {
    try {
      setLoadingAdvice(true)
      const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/investment-advice${getPasswordParam()}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch investment advice')
      }
      
      const data = await response.json()
      setInvestmentAdvice(data)
      setShowAdviceModal(true)
    } catch (error) {
      console.error('Error fetching investment advice:', error)
      alert('Failed to fetch investment advice. Please try again.')
    } finally {
      setLoadingAdvice(false)
    }
  }

  // New function to get quantitative analysis
  const getQuantitativeAnalysis = async () => {
    try {
      setLoadingAnalysis(true)
      const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}/quantitative${getPasswordParam()}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch quantitative analysis')
      }
      
      const data = await response.json()
      setQuantAnalysis(data)
      setShowAnalysisModal(true)
    } catch (error) {
      console.error('Error fetching quantitative analysis:', error)
      alert('Failed to fetch detailed analysis. Please try again.')
    } finally {
      setLoadingAnalysis(false)
    }
  }

  // New function to show recent news & posts
  const showRecentPosts = () => {
    setShowNewsModal(true)
  }

  // Check user role on component mount
  useEffect(() => {
    const checkUserRole = async () => {
      try {
        const password = localStorage.getItem('stockscope_password')
        if (password) {
          // Make a test API call to determine role
          const response = await fetch(`${API_BASE_URL}/api/stocks${getPasswordParam()}`)
          if (response.status === 403) {
            setUserRole('guest')
          } else {
            // Check if it's admin by trying an admin endpoint
            const testResponse = await fetch(`${API_BASE_URL}/api/cache${getPasswordParam()}`, {
              method: 'DELETE',
              headers: { 'Content-Type': 'application/json' }
            })
            setUserRole(testResponse.status === 403 ? 'demo' : 'admin')
          }
        }
      } catch (error) {
        console.error('Error checking user role:', error)
        setUserRole('guest')
      }
    }
    
    checkUserRole()
  }, [API_BASE_URL])

  // Function to delete stock data
  const handleDeleteStock = async () => {
    try {
      setIsDeleting(true)
      const response = await fetch(`${API_BASE_URL}/api/stocks/${symbol}${getPasswordParam()}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete stock data')
      }
      
      const result = await response.json()
      alert(`Successfully deleted ${result.deleted_files.length} files for ${symbol}`)
      
      // Go back to search after successful deletion
      onBack()
      
    } catch (error) {
      console.error('Error deleting stock:', error)
      alert(error instanceof Error ? error.message : 'Failed to delete stock data')
    } finally {
      setIsDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center px-4">
        <div className="text-center">
          <div className="h-12 w-12 sm:h-16 sm:w-16 animate-spin rounded-full border-4 border-white/30 border-t-white mx-auto mb-4" />
          <p className="text-white text-lg sm:text-xl">Loading {symbol} analysis...</p>
        </div>
      </div>
    )
  }

  if (error || !stockData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center px-4">
        <div className="text-center">
          <div className="text-4xl sm:text-6xl mb-4">📊</div>
          <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">No Data Available</h2>
          <p className="text-white/70 mb-6 text-sm sm:text-base">{error || `No analysis found for ${symbol}`}</p>
          <button
            onClick={onBack}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 sm:px-6 py-2 sm:py-3 rounded-lg transition-colors"
          >
            ← Back to Search
          </button>
        </div>
      </div>
    )
  }

  // Prepare chart data - now using SourceAnalysis objects
  const chartData = stockData.sources.map(sourceAnalysis => ({
    source: sourceAnalysis.source,
    count: sourceAnalysis.count,
    color: sourceAnalysis.source === 'Reddit' ? '#FF4500' : 
           sourceAnalysis.source === 'News' ? '#1DA1F2' : '#6366F1'
  }))

  // Get sentiment from either new structure or legacy fallback
  const avgSentiment = stockData.sentiment_metrics?.avg_sentiment ?? stockData.avg_sentiment ?? 0
  const sentimentColor = avgSentiment > 0.1 ? '#10B981' : 
                        avgSentiment < -0.1 ? '#EF4444' : '#F59E0B'

  const sentimentEmoji = avgSentiment > 0.1 ? '🟢' : 
                        avgSentiment < -0.1 ? '🔴' : '🟡'

  // Calculate counts for each source type using SourceAnalysis objects
  const redditData = stockData.sources.find(s => s.source === 'Reddit')
  const newsData = stockData.sources.find(s => s.source === 'News')
  
  const redditCount = redditData?.count ?? 0
  const newsCount = newsData?.count ?? 0

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-8">
        {/* Header - Mobile optimized */}
        <div className="flex items-center justify-between mb-6 sm:mb-8">
          <div className="flex items-center gap-2 sm:gap-4 min-w-0 flex-1">
            <button
              onClick={onBack}
              className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors backdrop-blur-sm flex-shrink-0"
            >
              ←
            </button>
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-4xl font-bold text-white truncate">{companyInfo?.displayName || symbol}</h1>
              <p className="text-white/70 text-sm sm:text-base">Sentiment Analysis Dashboard</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            {/* Delete button - only for admin users */}
            {userRole === 'admin' && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="bg-red-600 hover:bg-red-700 text-white px-2 sm:px-4 py-1.5 sm:py-2 rounded-lg transition-colors flex items-center gap-1 sm:gap-2 text-xs sm:text-sm"
                title="Delete all data for this stock (Admin only)"
              >
                <X className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="hidden sm:inline">Delete Stock</span>
              </button>
            )}
            
            <button
              onClick={refetchStockData}
              className="bg-blue-600 hover:bg-blue-700 text-white px-2 sm:px-4 py-1.5 sm:py-2 rounded-lg transition-colors flex items-center gap-1 sm:gap-2 text-xs sm:text-sm"
            >
              <Activity className="h-3 w-3 sm:h-4 sm:w-4" />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Key Metrics - Mobile optimized grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6 mb-6 sm:mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-xs sm:text-sm">Total Posts</p>
                <p className="text-xl sm:text-3xl font-bold text-white">{(stockData.total_posts ?? 0).toLocaleString()}</p>
              </div>
              <MessageSquare className="h-6 w-6 sm:h-8 sm:w-8 text-blue-400" />
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-xs sm:text-sm">Avg Sentiment</p>
                <p className="text-xl sm:text-3xl font-bold" style={{ color: sentimentColor }}>
                  {avgSentiment.toFixed(3)}
                </p>
                <p className="text-xs sm:text-sm text-white/60">{sentimentEmoji} {avgSentiment > 0 ? 'Positive' : avgSentiment < 0 ? 'Negative' : 'Neutral'}</p>
              </div>
              {avgSentiment > 0 ? 
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-400" /> : 
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-red-400" />
              }
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-xs sm:text-sm">Reddit Posts</p>
                <p className="text-xl sm:text-3xl font-bold text-white">{redditCount.toLocaleString()}</p>
              </div>
              <MessageSquare className="h-6 w-6 sm:h-8 sm:w-8 text-orange-400" />
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-xs sm:text-sm">News Articles</p>
                <p className="text-xl sm:text-3xl font-bold text-white">{newsCount.toLocaleString()}</p>
              </div>
              <Newspaper className="h-6 w-6 sm:h-8 sm:w-8 text-blue-400" />
            </div>
          </div>
        </div>

        {/* Charts - Mobile stacked layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {/* Source Distribution */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-white/20">
            <h3 className="text-lg sm:text-xl font-semibold text-white mb-3 sm:mb-4 flex items-center gap-2">
              <Building2 className="h-4 w-4 sm:h-5 sm:w-5" />
              Data Sources
            </h3>
            <div className="h-48 sm:h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    outerRadius={window.innerWidth < 640 ? 60 : 80}
                    dataKey="count"
                    label={false}
                    labelLine={false}
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value, name, props) => [
                      `${value} posts`,
                      props.payload.source
                    ]}
                    labelFormatter={() => "Data Source"}
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.2)', 
                      borderRadius: '8px',
                      color: 'white',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                      fontSize: window.innerWidth < 640 ? '12px' : '14px'
                    }}
                    itemStyle={{
                      color: 'white'
                    }}
                    labelStyle={{
                      color: 'white'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            {/* Custom Legend */}
            <div className="flex flex-wrap justify-center gap-3 sm:gap-4 mt-3 sm:mt-4">
              {chartData.map((entry, index) => (
                <div key={index} className="flex items-center gap-1 sm:gap-2">
                  <div 
                    className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" 
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-white text-xs sm:text-sm">
                    {entry.source}: {entry.count}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Source Breakdown Bar Chart */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-white/20">
            <h3 className="text-lg sm:text-xl font-semibold text-white mb-3 sm:mb-4 flex items-center gap-2">
              <BarChart className="h-4 w-4 sm:h-5 sm:w-5" />
              Source Breakdown
            </h3>
            <div className="h-48 sm:h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis 
                    dataKey="source" 
                    stroke="rgba(255,255,255,0.7)" 
                    fontSize={window.innerWidth < 640 ? 10 : 12}
                  />
                  <YAxis 
                    stroke="rgba(255,255,255,0.7)" 
                    fontSize={window.innerWidth < 640 ? 10 : 12}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.8)', 
                      border: 'none', 
                      borderRadius: '8px',
                      color: 'white',
                      fontSize: window.innerWidth < 640 ? '12px' : '14px'
                    }} 
                  />
                  <Bar dataKey="count" fill="#6366F1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Source Details Table - Mobile optimized */}
        <div className="mt-4 sm:mt-6 bg-white/10 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-white/20">
          <h3 className="text-lg sm:text-xl font-semibold text-white mb-3 sm:mb-4">Source Details</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-white">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="text-left py-2 text-sm sm:text-base">Source</th>
                  <th className="text-right py-2 text-sm sm:text-base">Posts</th>
                  <th className="text-right py-2 text-sm sm:text-base hidden sm:table-cell">Avg Sentiment</th>
                  <th className="text-right py-2 text-sm sm:text-base hidden md:table-cell">Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {stockData.sources.map((source) => (
                  <tr key={source.source} className="border-b border-white/10">
                    <td className="py-3">
                      <div className="flex items-center gap-1 sm:gap-2">
                        <div 
                          className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" 
                          style={{ 
                            backgroundColor: source.source === 'Reddit' ? '#FF4500' : 
                                           source.source === 'News' ? '#1DA1F2' : '#6366F1' 
                          }}
                        />
                        <span className="text-sm sm:text-base">{source.source}</span>
                      </div>
                    </td>
                    <td className="text-right py-3 text-sm sm:text-base">{source.count.toLocaleString()}</td>
                    <td className="text-right py-3 hidden sm:table-cell">
                      <span style={{ 
                        color: source.avg_sentiment > 0.1 ? '#10B981' : 
                               source.avg_sentiment < -0.1 ? '#EF4444' : '#F59E0B' 
                      }} className="text-sm sm:text-base">
                        {source.avg_sentiment.toFixed(3)}
                      </span>
                    </td>
                    <td className="text-right py-3 text-white/60 text-sm hidden md:table-cell">
                      {new Date(source.latest_update).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Actions - Enhanced with more information */}
        <div className="mt-6 sm:mt-8 bg-white/10 backdrop-blur-sm rounded-xl p-4 sm:p-6 border border-white/20">
          <h3 className="text-lg sm:text-xl font-semibold text-white mb-3 sm:mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <button 
              onClick={getInvestmentAdvice}
              disabled={loadingAdvice}
              className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed text-white p-3 sm:p-4 rounded-lg transition-all duration-200 flex flex-col items-center justify-center gap-2 text-sm sm:text-base hover:scale-105"
            >
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="font-semibold">AI Investment Advice</span>
              </div>
              {loadingAdvice ? (
                <span className="text-xs text-blue-200">Loading analysis...</span>
              ) : (
                <span className="text-xs text-blue-200">BUY/SELL/HOLD + Risk Level</span>
              )}
            </button>

            <button 
              onClick={getQuantitativeAnalysis}
              disabled={loadingAnalysis}
              className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 disabled:opacity-50 disabled:cursor-not-allowed text-white p-3 sm:p-4 rounded-lg transition-all duration-200 flex flex-col items-center justify-center gap-2 text-sm sm:text-base hover:scale-105"
            >
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="font-semibold">Technical Analysis</span>
              </div>
              {loadingAnalysis ? (
                <span className="text-xs text-purple-200">Computing metrics...</span>
              ) : (
                <span className="text-xs text-purple-200">RSI, MACD, Sharpe Ratio</span>
              )}
            </button>

            <button 
              onClick={showRecentPosts}
              className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white p-3 sm:p-4 rounded-lg transition-all duration-200 flex flex-col items-center justify-center gap-2 text-sm sm:text-base hover:scale-105"
            >
              <div className="flex items-center gap-2">
                <Newspaper className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="font-semibold">Latest Sentiment</span>
              </div>
              <span className="text-xs text-green-200">
                {stockData.total_posts > 0 ? `${stockData.total_posts.toLocaleString()} posts analyzed` : 'View news & posts'}
              </span>
            </button>

            <a
              href={`/fundamentals/${symbol}`}
              className="bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 text-white p-3 sm:p-4 rounded-lg transition-all duration-200 flex flex-col items-center justify-center gap-2 text-sm sm:text-base hover:scale-105 text-center"
            >
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="font-semibold">Fundamentals</span>
              </div>
              <span className="text-xs text-orange-200">Revenue, Margins, Cash Flow</span>
            </a>
          </div>

          {/* Additional Quick Info Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            <div className="bg-white/5 rounded-lg p-3 text-center border border-white/10">
              <div className="text-xs text-white/60 mb-1">Sentiment Trend</div>
              <div className={`text-sm font-semibold flex items-center justify-center gap-1 ${
                avgSentiment > 0.1 ? 'text-green-400' : 
                avgSentiment < -0.1 ? 'text-red-400' : 'text-yellow-400'
              }`}>
                {avgSentiment > 0.1 ? '📈 Bullish' : 
                 avgSentiment < -0.1 ? '📉 Bearish' : '➡️ Neutral'}
              </div>
            </div>

            <div className="bg-white/5 rounded-lg p-3 text-center border border-white/10">
              <div className="text-xs text-white/60 mb-1">Data Sources</div>
              <div className="text-sm font-semibold text-white">
                {stockData.sources.length} Active
              </div>
            </div>

            <div className="bg-white/5 rounded-lg p-3 text-center border border-white/10">
              <div className="text-xs text-white/60 mb-1">Last Updated</div>
              <div className="text-sm font-semibold text-white">
                {stockData.last_updated ? new Date(stockData.last_updated).toLocaleDateString() : 'N/A'}
              </div>
            </div>

            <div className="bg-white/5 rounded-lg p-3 text-center border border-white/10">
              <div className="text-xs text-white/60 mb-1">Analysis Score</div>
              <div className="text-sm font-semibold text-white">
                {stockData.data_quality_score ? `${(stockData.data_quality_score * 100).toFixed(0)}%` : 'N/A'}
              </div>
            </div>
          </div>
        </div>

        {/* Investment Advice Modal - Mobile optimized */}
        {showAdviceModal && investmentAdvice && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-3 sm:p-4">
            <div className="bg-gradient-to-br from-slate-900 to-purple-900 rounded-xl p-4 sm:p-6 max-w-2xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-y-auto border border-white/20">
              <div className="flex items-center justify-between mb-4 sm:mb-6">
                <h2 className="text-xl sm:text-2xl font-bold text-white">Investment Advice for {symbol}</h2>
                <button
                  onClick={() => setShowAdviceModal(false)}
                  className="text-white/60 hover:text-white transition-colors p-1"
                >
                  <X className="h-5 w-5 sm:h-6 sm:w-6" />
                </button>
              </div>
              
              <div className="space-y-4 sm:space-y-6">
                {/* Recommendation */}
                <div className="bg-white/10 rounded-lg p-3 sm:p-4">
                  <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
                    <Target className="h-5 w-5 sm:h-6 sm:w-6 text-blue-400" />
                    <h3 className="text-base sm:text-lg font-semibold text-white">Recommendation</h3>
                  </div>
                  <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                    <span className={`px-3 sm:px-4 py-2 rounded-full font-bold text-xs sm:text-sm w-fit ${
                      investmentAdvice.recommendation === 'BUY' ? 'bg-green-600 text-white' :
                      investmentAdvice.recommendation === 'SELL' ? 'bg-red-600 text-white' :
                      'bg-yellow-600 text-white'
                    }`}>
                      {investmentAdvice.recommendation}
                    </span>
                    <div className="text-white text-sm sm:text-base">
                      <span className="text-white/70">Confidence: </span>
                      <span className="font-semibold">{(investmentAdvice.confidence * 100).toFixed(1)}%</span>
                    </div>
                    {investmentAdvice.target_price && (
                      <div className="text-white text-sm sm:text-base">
                        <span className="text-white/70">Target: </span>
                        <span className="font-semibold">${investmentAdvice.target_price.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Risk Level */}
                <div className="bg-white/10 rounded-lg p-3 sm:p-4">
                  <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
                    <Shield className="h-5 w-5 sm:h-6 sm:w-6 text-orange-400" />
                    <h3 className="text-base sm:text-lg font-semibold text-white">Risk Assessment</h3>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs sm:text-sm font-medium ${
                    investmentAdvice.risk_level === 'LOW' ? 'bg-green-600/20 text-green-300' :
                    investmentAdvice.risk_level === 'HIGH' ? 'bg-red-600/20 text-red-300' :
                    'bg-yellow-600/20 text-yellow-300'
                  }`}>
                    {investmentAdvice.risk_level} RISK
                  </span>
                </div>

                {/* Reasoning */}
                <div className="bg-white/10 rounded-lg p-3 sm:p-4">
                  <h3 className="text-base sm:text-lg font-semibold text-white mb-2 sm:mb-3">Analysis Reasoning</h3>
                  <ul className="space-y-2">
                    {investmentAdvice.reasoning.map((reason, index) => (
                      <li key={index} className="text-white/80 flex items-start gap-2 text-sm sm:text-base">
                        <span className="text-blue-400 mt-1">•</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Factors */}
                {investmentAdvice.factors && (
                  <div className="grid grid-cols-1 gap-3 sm:gap-4">
                    {investmentAdvice.factors.positive.length > 0 && (
                      <div className="bg-green-600/20 rounded-lg p-3 sm:p-4">
                        <h4 className="font-semibold text-green-300 mb-2 text-sm sm:text-base">Positive Factors</h4>
                        <ul className="space-y-1">
                          {investmentAdvice.factors.positive.map((factor, index) => (
                            <li key={index} className="text-green-200 text-xs sm:text-sm">• {factor}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {investmentAdvice.factors.negative.length > 0 && (
                      <div className="bg-red-600/20 rounded-lg p-3 sm:p-4">
                        <h4 className="font-semibold text-red-300 mb-2 text-sm sm:text-base">Risk Factors</h4>
                        <ul className="space-y-1">
                          {investmentAdvice.factors.negative.map((factor, index) => (
                            <li key={index} className="text-red-200 text-xs sm:text-sm">• {factor}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {investmentAdvice.factors.neutral.length > 0 && (
                      <div className="bg-gray-600/20 rounded-lg p-3 sm:p-4">
                        <h4 className="font-semibold text-gray-300 mb-2 text-sm sm:text-base">Neutral Factors</h4>
                        <ul className="space-y-1">
                          {investmentAdvice.factors.neutral.map((factor, index) => (
                            <li key={index} className="text-gray-200 text-xs sm:text-sm">• {factor}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Quantitative Analysis Modal */}
        {showAnalysisModal && quantAnalysis && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-gradient-to-br from-slate-900 to-purple-900 rounded-xl p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-white/20">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Quantitative Analysis for {symbol}</h2>
                <button
                  onClick={() => setShowAnalysisModal(false)}
                  className="text-white/60 hover:text-white transition-colors"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              
              <div className="space-y-6">
                {/* Metrics */}
                {quantAnalysis.metrics && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {quantAnalysis.metrics.sharpe_ratio && (
                      <div className="bg-white/10 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-white">{quantAnalysis.metrics.sharpe_ratio.toFixed(2)}</div>
                        <div className="text-white/70 text-sm">Sharpe Ratio</div>
                      </div>
                    )}
                    {quantAnalysis.metrics.volatility && (
                      <div className="bg-white/10 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-white">{(quantAnalysis.metrics.volatility * 100).toFixed(1)}%</div>
                        <div className="text-white/70 text-sm">Volatility</div>
                      </div>
                    )}
                    {quantAnalysis.metrics.beta && (
                      <div className="bg-white/10 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-white">{quantAnalysis.metrics.beta.toFixed(2)}</div>
                        <div className="text-white/70 text-sm">Beta</div>
                      </div>
                    )}
                    {quantAnalysis.metrics.alpha && (
                      <div className="bg-white/10 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-white">{(quantAnalysis.metrics.alpha * 100).toFixed(1)}%</div>
                        <div className="text-white/70 text-sm">Alpha</div>
                      </div>
                    )}
                  </div>
                )}

                {/* Signals */}
                {quantAnalysis.signals && (
                  <div className="bg-white/10 rounded-lg p-4">
                    <h3 className="text-lg font-semibold text-white mb-3">Technical Signals</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {quantAnalysis.signals.rsi && (
                        <div className="text-center">
                          <div className="text-xl font-bold text-white">{quantAnalysis.signals.rsi.toFixed(1)}</div>
                          <div className="text-white/70 text-sm">RSI</div>
                        </div>
                      )}
                      {quantAnalysis.signals.macd && (
                        <div className="text-center">
                          <div className="text-xl font-bold text-white">{quantAnalysis.signals.macd.toFixed(3)}</div>
                          <div className="text-white/70 text-sm">MACD</div>
                        </div>
                      )}
                      {quantAnalysis.signals.bollinger_bands && (
                        <div className="text-center">
                          <div className="text-xl font-bold text-white">{quantAnalysis.signals.bollinger_bands}</div>
                          <div className="text-white/70 text-sm">Bollinger Bands</div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Recommendation */}
                <div className="bg-white/10 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-white mb-3">Quantitative Recommendation</h3>
                  <div className="flex items-center gap-4">
                    <span className="text-xl font-bold text-blue-400">{quantAnalysis.recommendation}</span>
                    <div className="text-white">
                      <span className="text-sm text-white/70">Confidence: </span>
                      <span className="font-semibold">{(quantAnalysis.confidence * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Recent News & Posts Modal */}
        {showNewsModal && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-gradient-to-br from-slate-900 to-purple-900 rounded-xl p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-white/20">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Recent News & Posts for {symbol}</h2>
                <button
                  onClick={() => setShowNewsModal(false)}
                  className="text-white/60 hover:text-white transition-colors"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              
              <div className="space-y-4">
                {stockData?.sources.map((source) => (
                  <div key={source.source} className="bg-white/10 rounded-lg p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ 
                          backgroundColor: source.source === 'Reddit' ? '#FF4500' : 
                                         source.source === 'News' ? '#1DA1F2' : '#6366F1' 
                        }}
                      />
                      <h3 className="text-lg font-semibold text-white">{source.source}</h3>
                      <span className="text-white/60 text-sm">({source.count} posts)</span>
                    </div>
                    <div className="text-white/80">
                      <p>Average Sentiment: <span className={`font-semibold ${
                        source.avg_sentiment > 0.1 ? 'text-green-400' : 
                        source.avg_sentiment < -0.1 ? 'text-red-400' : 'text-yellow-400'
                      }`}>
                        {source.avg_sentiment.toFixed(3)}
                      </span></p>
                      <p className="text-sm text-white/60">Last Updated: {new Date(source.latest_update).toLocaleString()}</p>
                    </div>
                  </div>
                ))}
                
                <div className="bg-white/10 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-white/80">
                    <AlertCircle className="h-5 w-5" />
                    <span>Individual posts and articles are processed and aggregated into the sentiment metrics shown above.</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-gradient-to-br from-slate-900 to-red-900 rounded-xl p-6 max-w-md w-full border border-red-500/20">
              <div className="flex items-center gap-3 mb-4">
                <div className="bg-red-600/20 rounded-full p-2">
                  <X className="h-6 w-6 text-red-400" />
                </div>
                <h2 className="text-xl font-bold text-white">Delete Stock Data</h2>
              </div>
              
              <div className="mb-6">
                <p className="text-white/80 mb-3">
                  Are you sure you want to delete all data for <strong className="text-white">{symbol}</strong>?
                </p>
                <p className="text-red-300 text-sm">
                  This will permanently remove all sentiment analysis files, and this action cannot be undone.
                </p>
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={isDeleting}
                  className="flex-1 bg-white/10 hover:bg-white/20 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteStock}
                  disabled={isDeleting}
                  className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  {isDeleting ? (
                    <>
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Deleting...
                    </>
                  ) : (
                    'Delete Forever'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
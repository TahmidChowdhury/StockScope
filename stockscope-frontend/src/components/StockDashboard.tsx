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
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="h-16 w-16 animate-spin rounded-full border-4 border-white/30 border-t-white mx-auto mb-4" />
          <p className="text-white text-xl">Loading {symbol} analysis...</p>
        </div>
      </div>
    )
  }

  if (error || !stockData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-white mb-2">No Data Available</h2>
          <p className="text-white/70 mb-6">{error || `No analysis found for ${symbol}`}</p>
          <button
            onClick={onBack}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
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
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-lg transition-colors backdrop-blur-sm"
            >
              ←
            </button>
            <div>
              <h1 className="text-4xl font-bold text-white">{companyInfo?.displayName || symbol}</h1>
              <p className="text-white/70">Sentiment Analysis Dashboard</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Delete button - only for admin users */}
            {userRole === 'admin' && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                title="Delete all data for this stock (Admin only)"
              >
                <X className="h-4 w-4" />
                Delete Stock
              </button>
            )}
            
            <button
              onClick={refetchStockData}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              <Activity className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Total Posts</p>
                <p className="text-3xl font-bold text-white">{(stockData.total_posts ?? 0).toLocaleString()}</p>
              </div>
              <MessageSquare className="h-8 w-8 text-blue-400" />
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Avg Sentiment</p>
                <p className="text-3xl font-bold" style={{ color: sentimentColor }}>
                  {avgSentiment.toFixed(3)}
                </p>
                <p className="text-sm text-white/60">{sentimentEmoji} {avgSentiment > 0 ? 'Positive' : avgSentiment < 0 ? 'Negative' : 'Neutral'}</p>
              </div>
              {avgSentiment > 0 ? 
                <TrendingUp className="h-8 w-8 text-green-400" /> : 
                <TrendingDown className="h-8 w-8 text-red-400" />
              }
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Reddit Posts</p>
                <p className="text-3xl font-bold text-white">{redditCount.toLocaleString()}</p>
              </div>
              <MessageSquare className="h-8 w-8 text-orange-400" />
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">News Articles</p>
                <p className="text-3xl font-bold text-white">{newsCount.toLocaleString()}</p>
              </div>
              <Newspaper className="h-8 w-8 text-blue-400" />
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Source Distribution */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Data Sources
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
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
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
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
            <div className="flex flex-wrap justify-center gap-4 mt-4">
              {chartData.map((entry, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-white text-sm">
                    {entry.source}: {entry.count}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Source Breakdown Bar Chart */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <BarChart className="h-5 w-5" />
              Source Breakdown
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="source" stroke="rgba(255,255,255,0.7)" />
                  <YAxis stroke="rgba(255,255,255,0.7)" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.8)', 
                      border: 'none', 
                      borderRadius: '8px',
                      color: 'white'
                    }} 
                  />
                  <Bar dataKey="count" fill="#6366F1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Source Details Table */}
        <div className="mt-6 bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
          <h3 className="text-xl font-semibold text-white mb-4">Source Details</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-white">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="text-left py-2">Source</th>
                  <th className="text-right py-2">Posts</th>
                  <th className="text-right py-2">Avg Sentiment</th>
                  <th className="text-right py-2">Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {stockData.sources.map((source) => (
                  <tr key={source.source} className="border-b border-white/10">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-3 h-3 rounded-full" 
                          style={{ 
                            backgroundColor: source.source === 'Reddit' ? '#FF4500' : 
                                           source.source === 'News' ? '#1DA1F2' : '#6366F1' 
                          }}
                        />
                        {source.source}
                      </div>
                    </td>
                    <td className="text-right py-3">{source.count.toLocaleString()}</td>
                    <td className="text-right py-3">
                      <span style={{ 
                        color: source.avg_sentiment > 0.1 ? '#10B981' : 
                               source.avg_sentiment < -0.1 ? '#EF4444' : '#F59E0B' 
                      }}>
                        {source.avg_sentiment.toFixed(3)}
                      </span>
                    </td>
                    <td className="text-right py-3 text-white/60">
                      {new Date(source.latest_update).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
          <h3 className="text-xl font-semibold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button 
              onClick={getInvestmentAdvice}
              disabled={loadingAdvice}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white p-4 rounded-lg transition-colors flex items-center gap-2"
            >
              <TrendingUp className="h-5 w-5" />
              {loadingAdvice ? 'Loading...' : 'Get Investment Advice'}
            </button>
            <button 
              onClick={getQuantitativeAnalysis}
              disabled={loadingAnalysis}
              className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white p-4 rounded-lg transition-colors flex items-center gap-2"
            >
              <Activity className="h-5 w-5" />
              {loadingAnalysis ? 'Loading...' : 'View Detailed Analysis'}
            </button>
            <button 
              onClick={showRecentPosts}
              className="bg-green-600 hover:bg-green-700 text-white p-4 rounded-lg transition-colors flex items-center gap-2"
            >
              <Newspaper className="h-5 w-5" />
              Recent News & Posts
            </button>
          </div>
        </div>

        {/* Investment Advice Modal */}
        {showAdviceModal && investmentAdvice && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-gradient-to-br from-slate-900 to-purple-900 rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-white/20">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Investment Advice for {symbol}</h2>
                <button
                  onClick={() => setShowAdviceModal(false)}
                  className="text-white/60 hover:text-white transition-colors"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              
              <div className="space-y-6">
                {/* Recommendation */}
                <div className="bg-white/10 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <Target className="h-6 w-6 text-blue-400" />
                    <h3 className="text-lg font-semibold text-white">Recommendation</h3>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`px-4 py-2 rounded-full font-bold text-sm ${
                      investmentAdvice.recommendation === 'BUY' ? 'bg-green-600 text-white' :
                      investmentAdvice.recommendation === 'SELL' ? 'bg-red-600 text-white' :
                      'bg-yellow-600 text-white'
                    }`}>
                      {investmentAdvice.recommendation}
                    </span>
                    <div className="text-white">
                      <span className="text-sm text-white/70">Confidence: </span>
                      <span className="font-semibold">{(investmentAdvice.confidence * 100).toFixed(1)}%</span>
                    </div>
                    {investmentAdvice.target_price && (
                      <div className="text-white">
                        <span className="text-sm text-white/70">Target: </span>
                        <span className="font-semibold">${investmentAdvice.target_price.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Risk Level */}
                <div className="bg-white/10 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <Shield className="h-6 w-6 text-orange-400" />
                    <h3 className="text-lg font-semibold text-white">Risk Assessment</h3>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    investmentAdvice.risk_level === 'LOW' ? 'bg-green-600/20 text-green-300' :
                    investmentAdvice.risk_level === 'HIGH' ? 'bg-red-600/20 text-red-300' :
                    'bg-yellow-600/20 text-yellow-300'
                  }`}>
                    {investmentAdvice.risk_level} RISK
                  </span>
                </div>

                {/* Reasoning */}
                <div className="bg-white/10 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-white mb-3">Analysis Reasoning</h3>
                  <ul className="space-y-2">
                    {investmentAdvice.reasoning.map((reason, index) => (
                      <li key={index} className="text-white/80 flex items-start gap-2">
                        <span className="text-blue-400 mt-1">•</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Factors */}
                {investmentAdvice.factors && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {investmentAdvice.factors.positive.length > 0 && (
                      <div className="bg-green-600/20 rounded-lg p-4">
                        <h4 className="font-semibold text-green-300 mb-2">Positive Factors</h4>
                        <ul className="space-y-1">
                          {investmentAdvice.factors.positive.map((factor, index) => (
                            <li key={index} className="text-green-200 text-sm">• {factor}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {investmentAdvice.factors.negative.length > 0 && (
                      <div className="bg-red-600/20 rounded-lg p-4">
                        <h4 className="font-semibold text-red-300 mb-2">Risk Factors</h4>
                        <ul className="space-y-1">
                          {investmentAdvice.factors.negative.map((factor, index) => (
                            <li key={index} className="text-red-200 text-sm">• {factor}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {investmentAdvice.factors.neutral.length > 0 && (
                      <div className="bg-gray-600/20 rounded-lg p-4">
                        <h4 className="font-semibold text-gray-300 mb-2">Neutral Factors</h4>
                        <ul className="space-y-1">
                          {investmentAdvice.factors.neutral.map((factor, index) => (
                            <li key={index} className="text-gray-200 text-sm">• {factor}</li>
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
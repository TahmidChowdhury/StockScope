'use client'

import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'
import { TrendingUp, TrendingDown, Activity, MessageSquare, Newspaper, Building2 } from 'lucide-react'

interface StockData {
  ticker: string
  total_posts: number
  avg_sentiment: number
  sources: {
    Reddit?: number
    News?: number
    SEC?: number
  }
}

interface StockDashboardProps {
  symbol: string
  onBack: () => void
}

export default function StockDashboard({ symbol, onBack }: StockDashboardProps) {
  const [stockData, setStockData] = useState<StockData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStockData()
  }, [symbol])

  const fetchStockData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`http://localhost:8000/api/stocks/${symbol}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch data for ${symbol}`)
      }
      
      const data = await response.json()
      setStockData(data)
    } catch (error) {
      console.error('Error fetching stock data:', error)
      setError(error instanceof Error ? error.message : 'Unknown error')
    } finally {
      setLoading(false)
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

  // Prepare chart data
  const sourceData = Object.entries(stockData.sources).map(([source, count]) => ({
    source,
    count,
    color: source === 'Reddit' ? '#FF4500' : source === 'News' ? '#1DA1F2' : '#6366F1'
  }))

  const sentimentColor = stockData.avg_sentiment > 0.1 ? '#10B981' : 
                        stockData.avg_sentiment < -0.1 ? '#EF4444' : '#F59E0B'

  const sentimentEmoji = stockData.avg_sentiment > 0.1 ? '🟢' : 
                        stockData.avg_sentiment < -0.1 ? '🔴' : '🟡'

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
              <h1 className="text-4xl font-bold text-white">{symbol}</h1>
              <p className="text-white/70">Sentiment Analysis Dashboard</p>
            </div>
          </div>
          
          <button
            onClick={fetchStockData}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
          >
            <Activity className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Total Posts</p>
                <p className="text-3xl font-bold text-white">{stockData.total_posts.toLocaleString()}</p>
              </div>
              <MessageSquare className="h-8 w-8 text-blue-400" />
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Avg Sentiment</p>
                <p className="text-3xl font-bold" style={{ color: sentimentColor }}>
                  {stockData.avg_sentiment.toFixed(3)}
                </p>
                <p className="text-sm text-white/60">{sentimentEmoji} {stockData.avg_sentiment > 0 ? 'Positive' : stockData.avg_sentiment < 0 ? 'Negative' : 'Neutral'}</p>
              </div>
              {stockData.avg_sentiment > 0 ? 
                <TrendingUp className="h-8 w-8 text-green-400" /> : 
                <TrendingDown className="h-8 w-8 text-red-400" />
              }
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Reddit Posts</p>
                <p className="text-3xl font-bold text-white">{(stockData.sources.Reddit || 0).toLocaleString()}</p>
              </div>
              <MessageSquare className="h-8 w-8 text-orange-400" />
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">News Articles</p>
                <p className="text-3xl font-bold text-white">{(stockData.sources.News || 0).toLocaleString()}</p>
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
                    data={sourceData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    dataKey="count"
                    label={({ source, count }) => `${source}: ${count}`}
                  >
                    {sourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.8)', 
                      border: 'none', 
                      borderRadius: '8px',
                      color: 'white'
                    }} 
                  />
                </PieChart>
              </ResponsiveContainer>
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
                <BarChart data={sourceData}>
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

        {/* Quick Actions */}
        <div className="mt-8 bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
          <h3 className="text-xl font-semibold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-lg transition-colors flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Get Investment Advice
            </button>
            <button className="bg-purple-600 hover:bg-purple-700 text-white p-4 rounded-lg transition-colors flex items-center gap-2">
              <Activity className="h-5 w-5" />
              View Detailed Analysis
            </button>
            <button className="bg-green-600 hover:bg-green-700 text-white p-4 rounded-lg transition-colors flex items-center gap-2">
              <Newspaper className="h-5 w-5" />
              Recent News & Posts
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
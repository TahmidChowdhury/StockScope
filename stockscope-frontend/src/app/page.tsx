'use client'

import { useState, useEffect } from 'react'
import StockSearch from '@/components/StockSearch'
import StockDashboard from '@/components/StockDashboard'
import type { ViewType, StockMetadata } from '@/types'

// Get API URL from environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const [currentView, setCurrentView] = useState<ViewType>('search')
  const [selectedStock, setSelectedStock] = useState<string>('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState<string | null>(null)

  const handleAnalyze = async (symbol: string) => {
    setIsAnalyzing(true)
    setAnalysisStatus(`Starting analysis for ${symbol}...`)

    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: symbol,
          sources: ['reddit', 'news', 'sec']
        }),
      })

      const data = await response.json()
      
      if (response.ok) {
        setAnalysisStatus(`✅ Analysis started for ${symbol}! This may take 30-60 seconds.`)
        
        // Check if data already exists and show dashboard
        setTimeout(async () => {
          try {
            const checkResponse = await fetch(`${API_BASE_URL}/api/stocks/${symbol}`)
            if (checkResponse.ok) {
              setSelectedStock(symbol)
              setCurrentView('dashboard')
              setAnalysisStatus(null)
            } else {
              setAnalysisStatus(`🎉 Analysis completed for ${symbol}!`)
            }
          } catch (error) {
            setAnalysisStatus(`🎉 Analysis completed for ${symbol}!`)
          }
          setIsAnalyzing(false)
        }, 3000)
      } else {
        throw new Error(data.detail || 'Analysis failed')
      }
    } catch (error) {
      console.error('Analysis failed:', error)
      setAnalysisStatus(`❌ Analysis failed for ${symbol}. Please try again.`)
      setIsAnalyzing(false)
    }
  }

  const handleViewDashboard = (symbol: string) => {
    setSelectedStock(symbol)
    setCurrentView('dashboard')
  }

  const handleBackToSearch = () => {
    setCurrentView('search')
    setSelectedStock('')
    setAnalysisStatus(null)
  }

  if (currentView === 'dashboard' && selectedStock) {
    return <StockDashboard symbol={selectedStock} onBack={handleBackToSearch} />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            📊 StockScope Pro
          </h1>
          <p className="text-xl text-white/80 max-w-2xl mx-auto">
            AI-Powered Stock Sentiment Analysis with Real-Time Data from Reddit, News, and SEC Filings
          </p>
        </div>

        {/* Stock Search */}
        <div className="mb-8">
          <StockSearch onAnalyze={handleAnalyze} isLoading={isAnalyzing} />
        </div>

        {/* Analysis Status */}
        {analysisStatus && (
          <div className="max-w-2xl mx-auto mb-8">
            <div className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 p-6 text-center">
              <p className="text-white text-lg">{analysisStatus}</p>
              {isAnalyzing && (
                <div className="mt-4 w-full bg-white/20 rounded-full h-2">
                  <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full animate-pulse" style={{ width: '70%' }}></div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Portfolio Section */}
        <PortfolioView onViewDashboard={handleViewDashboard} />

        {/* Features */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-white mb-2">Real-Time Search</h3>
            <p className="text-white/70">Instant autocomplete with 70+ popular stocks and custom symbol support</p>
          </div>
          
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-4xl mb-4">🤖</div>
            <h3 className="text-xl font-semibold text-white mb-2">AI Analysis</h3>
            <p className="text-white/70">Advanced sentiment analysis from multiple data sources with ML insights</p>
          </div>
          
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-4xl mb-4">📈</div>
            <h3 className="text-xl font-semibold text-white mb-2">Investment Insights</h3>
            <p className="text-white/70">Get BUY/SELL/HOLD recommendations with confidence scores and risk analysis</p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-16 text-center text-white/60">
          <p>Built with Next.js + Turbopack ⚡ FastAPI + Python 🐍</p>
        </div>
      </div>
    </div>
  )
}

// Portfolio component to show existing analyzed stocks
function PortfolioView({ onViewDashboard }: { onViewDashboard: (symbol: string) => void }) {
  const [stocks, setStocks] = useState<StockMetadata[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAvailableStocks()
  }, [])

  const fetchAvailableStocks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stocks`)
      if (response.ok) {
        const data = await response.json()
        // Handle both old format (array of strings) and new format (array of objects)
        if (Array.isArray(data.stocks)) {
          if (data.stocks.length > 0 && typeof data.stocks[0] === 'string') {
            // Old format: convert strings to objects
            setStocks(data.stocks.map((symbol: string) => ({
              symbol,
              total_posts: 0,
              avg_sentiment: 0,
              last_updated: '',
              sources: []
            })))
          } else {
            // New format: use objects directly
            setStocks(data.stocks || [])
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch stocks:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto mb-12">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/30 border-t-white mx-auto mb-2" />
          <p className="text-white/60">Loading your portfolio...</p>
        </div>
      </div>
    )
  }

  if (stocks.length === 0) {
    return (
      <div className="max-w-4xl mx-auto mb-12 text-center">
        <div className="bg-white/5 backdrop-blur-sm rounded-xl p-8 border border-white/10">
          <div className="text-4xl mb-4">📈</div>
          <h3 className="text-xl font-semibold text-white mb-2">No Stocks Analyzed Yet</h3>
          <p className="text-white/70">Use the search above to analyze your first stock and start building your portfolio</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto mb-12">
      <h2 className="text-2xl font-bold text-white mb-6 text-center">📊 Your Portfolio</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {stocks.map((stock) => (
          <button
            key={stock.symbol}
            onClick={() => onViewDashboard(stock.symbol)}
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 border border-white/20 transition-all duration-200 hover:scale-105"
          >
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">{stock.symbol}</div>
              <div className="text-sm text-white/60">
                {stock.total_posts > 0 ? `${stock.total_posts} posts` : 'View Dashboard'}
              </div>
              {stock.avg_sentiment !== 0 && (
                <div className={`text-xs mt-1 ${
                  stock.avg_sentiment > 0.1 ? 'text-green-400' : 
                  stock.avg_sentiment < -0.1 ? 'text-red-400' : 'text-yellow-400'
                }`}>
                  {stock.avg_sentiment > 0 ? '📈' : stock.avg_sentiment < 0 ? '📉' : '➡️'} 
                  {(stock.avg_sentiment * 100).toFixed(0)}%
                </div>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

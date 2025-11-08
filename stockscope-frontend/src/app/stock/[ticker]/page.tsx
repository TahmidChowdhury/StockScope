'use client'

import { use } from 'react'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import Link from 'next/link'
import PriceChart from '@/components/PriceChart'
import NewsComponent from '@/components/NewsComponent'
import KeyMetricsComponent from '@/components/KeyMetrics'

interface StockViewPageProps {
  params: Promise<{
    ticker: string
  }>
}

export default function StockViewPage({ params }: StockViewPageProps) {
  const { ticker } = use(params)
  const symbol = ticker.toUpperCase()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 backdrop-blur-sm border-b border-purple-500/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Link 
                href="/"
                className="flex items-center space-x-2 text-gray-300 hover:text-white transition-colors"
              >
                <ArrowLeftIcon className="h-5 w-5" />
                <span>Back to Dashboard</span>
              </Link>
              <div className="h-6 w-px bg-gray-600"></div>
              <h1 className="text-2xl font-bold text-white">{symbol}</h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <Link
                href={`/fundamentals/${ticker}`}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                View Fundamentals
              </Link>
              <Link
                href="/compare"
                className="px-4 py-2 border border-purple-500/50 text-gray-300 rounded-lg hover:bg-purple-500/20 transition-colors"
              >
                Compare Stocks
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Column - Chart and News */}
          <div className="lg:col-span-3 space-y-6">
            {/* Price Chart */}
            <PriceChart symbol={symbol} className="shadow-sm" />
            
            {/* News Component */}
            <NewsComponent symbol={symbol} className="shadow-sm" />
          </div>

          {/* Right Column - Key Metrics */}
          <div className="lg:col-span-1">
            <KeyMetricsComponent symbol={symbol} className="shadow-sm sticky top-6" />
          </div>
        </div>

        {/* Bottom Section - Additional Actions */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href={`/fundamentals/${ticker}`}
            className="p-6 bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 hover:border-purple-500/40 transition-all"
          >
            <div className="flex items-center space-x-3">
              <div className="h-12 w-12 bg-purple-900/50 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-purple-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-white">Fundamentals Analysis</h3>
                <p className="text-sm text-gray-300">Deep dive into financial metrics</p>
              </div>
            </div>
          </Link>

          <Link
            href="/compare"
            className="p-6 bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 hover:border-purple-500/40 transition-all"
          >
            <div className="flex items-center space-x-3">
              <div className="h-12 w-12 bg-green-900/50 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-white">Compare Stocks</h3>
                <p className="text-sm text-gray-300">Side-by-side comparison</p>
              </div>
            </div>
          </Link>

          <Link
            href="/screener"
            className="p-6 bg-slate-800/50 backdrop-blur-sm rounded-lg border border-purple-500/20 hover:border-purple-500/40 transition-all"
          >
            <div className="flex items-center space-x-3">
              <div className="h-12 w-12 bg-purple-900/50 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-purple-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-white">Stock Screener</h3>
                <p className="text-sm text-gray-300">Find stocks by criteria</p>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  )
}
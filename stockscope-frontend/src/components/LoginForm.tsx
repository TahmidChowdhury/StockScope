'use client'

import React, { useState } from 'react'
import { LoginRequest, SimpleAuthResponse } from '@/types'

// Get API URL from environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface LoginFormProps {
  onLoginSuccess: () => void
}

export default function LoginForm({ onLoginSuccess }: LoginFormProps) {
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password } as LoginRequest),
      })

      if (!response.ok) {
        throw new Error('Invalid password')
      }

      const authData: SimpleAuthResponse = await response.json()
      
      if (authData.success) {
        // Store simple auth state in localStorage
        localStorage.setItem('stockscope_authenticated', 'true')
        localStorage.setItem('stockscope_password', password) // Store for API calls
        onLoginSuccess()
      } else {
        throw new Error(authData.message || 'Authentication failed')
      }
    } catch (error) {
      console.error('Login failed:', error)
      setError('Login failed. Please check your password and try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full">
        {/* Header */}
        <div className="text-center mb-8 lg:mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-4">
            <span className="text-2xl">📊</span>
          </div>
          <h1 className="text-4xl lg:text-5xl font-bold text-white mb-4">
            StockScope Pro
          </h1>
          <p className="text-xl text-gray-300 max-w-2xl mx-auto">
            Professional stock sentiment analysis and investment insights
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 lg:mb-12">
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-3xl mb-4">🔍</div>
            <h3 className="text-lg font-semibold text-white mb-2">Real-Time Search</h3>
            <p className="text-sm text-gray-300">Instant autocomplete with 70+ popular stocks and custom symbol support</p>
          </div>
          
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-3xl mb-4">🤖</div>
            <h3 className="text-lg font-semibold text-white mb-2">AI Analysis</h3>
            <p className="text-sm text-gray-300">Advanced sentiment analysis from multiple data sources with ML insights</p>
          </div>
          
          <div className="text-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
            <div className="text-3xl mb-4">📈</div>
            <h3 className="text-lg font-semibold text-white mb-2">Investment Insights</h3>
            <p className="text-sm text-gray-300">Get BUY/SELL/HOLD recommendations with confidence scores and risk analysis</p>
          </div>
        </div>

        {/* Login Form */}
        <div className="max-w-md mx-auto">
          <div className="bg-white/10 backdrop-blur-lg rounded-xl shadow-2xl border border-white/20 p-8">
            <div className="text-center mb-6">
              <div className="mx-auto h-12 w-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-4">
                <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">Secure Access</h2>
              <p className="text-gray-300 text-sm">Enter your password to continue</p>
            </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
              Master Password
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                required
                className="appearance-none relative block w-full px-4 py-3 border border-gray-600 placeholder-gray-400 text-white bg-gray-800/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => setShowPassword(!showPassword)}
              >
                <svg className="h-5 w-5 text-gray-400 hover:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {showPassword ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  )}
                </svg>
              </button>
            </div>
          </div>

          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !password}
            className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          >
            {isLoading ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Authenticating...
              </div>
            ) : (
              'Access StockScope'
            )}
          </button>
        </form>

        <div className="text-center mt-6">
          <p className="text-xs text-gray-400">
            🔒 This application requires authentication for security
          </p>
        </div>
          </div>
        </div>
      </div>
    </div>
  )
}
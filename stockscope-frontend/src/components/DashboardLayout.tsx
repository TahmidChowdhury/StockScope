'use client'

import { ReactNode } from 'react'

interface DashboardLayoutProps {
  children?: ReactNode
  header?: ReactNode
  sidebar?: ReactNode
  className?: string
}

export default function DashboardLayout({ 
  children, 
  header, 
  sidebar,
  className = '' 
}: DashboardLayoutProps) {
  return (
    <div className={`min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 ${className}`}>
      {/* Header */}
      {header && (
        <div className="sticky top-0 z-20 bg-slate-800/50 backdrop-blur-sm border-b border-purple-500/20">
          {header}
        </div>
      )}

      {/* Main Layout */}
      <div className="flex min-h-[calc(100vh-4rem)]">
        {/* Sidebar */}
        {sidebar && (
          <div className="hidden lg:block w-80 flex-shrink-0 p-6 border-r border-white/10">
            <div className="space-y-6">
              {sidebar}
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

// Grid Component for organizing dashboard sections
interface DashboardGridProps {
  children: ReactNode
  columns?: 1 | 2 | 3
  gap?: 'sm' | 'md' | 'lg'
  className?: string
}

export function DashboardGrid({ 
  children, 
  columns = 2, 
  gap = 'md',
  className = '' 
}: DashboardGridProps) {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 lg:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3'
  }

  const gapClasses = {
    sm: 'gap-4',
    md: 'gap-6',
    lg: 'gap-8'
  }

  return (
    <div className={`grid ${gridCols[columns]} ${gapClasses[gap]} ${className}`}>
      {children}
    </div>
  )
}

// Section Component for organizing content areas
interface DashboardSectionProps {
  title: string
  icon?: ReactNode
  children: ReactNode
  className?: string
  headerAction?: ReactNode
  variant?: 'default' | 'prominent' | 'subtle'
}

export function DashboardSection({ 
  title, 
  icon, 
  children, 
  className = '',
  headerAction,
  variant = 'default'
}: DashboardSectionProps) {
  const variants = {
    default: 'bg-white/5 border-white/10',
    prominent: 'bg-gradient-to-br from-purple-600/10 to-pink-600/10 border-purple-500/20',
    subtle: 'bg-white/[0.02] border-white/5'
  }

  return (
    <div className={`backdrop-blur-sm border rounded-2xl p-6 ${variants[variant]} ${className}`}>
      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {icon && <div className="text-purple-400">{icon}</div>}
          <h2 className="text-xl font-semibold text-white">{title}</h2>
        </div>
        {headerAction && (
          <div className="flex-shrink-0">
            {headerAction}
          </div>
        )}
      </div>

      {/* Section Content */}
      <div>
        {children}
      </div>
    </div>
  )
}

// Card Component for dashboard widgets
interface DashboardCardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  clickable?: boolean
  onClick?: () => void
}

export function DashboardCard({ 
  children, 
  className = '',
  hover = false,
  clickable = false,
  onClick
}: DashboardCardProps) {
  const baseClasses = 'bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4'
  const interactiveClasses = hover || clickable 
    ? 'hover:bg-white/8 hover:border-white/20 transition-all duration-200'
    : ''
  const clickableClasses = clickable ? 'cursor-pointer' : ''

  return (
    <div 
      className={`${baseClasses} ${interactiveClasses} ${clickableClasses} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}
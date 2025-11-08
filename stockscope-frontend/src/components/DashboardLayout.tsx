'use client'

import { ReactNode, useState } from 'react'
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'

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
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className={`min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 ${className}`}>
      {/* Header */}
      {header && (
        <div className="sticky top-0 z-30 bg-slate-800/50 backdrop-blur-sm border-b border-purple-500/20">
          <div className="flex items-center justify-between px-4 py-3">
            {sidebar && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden text-white p-2 rounded-lg hover:bg-white/10 transition-colors"
                aria-label="Open menu"
              >
                <Bars3Icon className="h-6 w-6" />
              </button>
            )}
            <div className="flex-1">
              {header}
            </div>
          </div>
        </div>
      )}

      {/* Mobile Sidebar Overlay */}
      {sidebar && sidebarOpen && (
        <div className="lg:hidden">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setSidebarOpen(false)
            }}
            role="button"
            tabIndex={0}
            aria-label="Close menu"
          />
          
          {/* Sidebar Drawer */}
          <div className="fixed inset-y-0 left-0 z-50 w-80 max-w-[85vw] bg-slate-900/95 backdrop-blur-sm border-r border-white/10 overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">Menu</h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="text-white/60 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors"
                aria-label="Close menu"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="p-6 space-y-6">
              {sidebar}
            </div>
          </div>
        </div>
      )}

      {/* Main Layout */}
      <div className="flex min-h-[calc(100vh-4rem)]">
        {/* Desktop Sidebar */}
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

// Enhanced Grid Component with better mobile handling
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
    3: 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3'
  }

  const gapClasses = {
    sm: 'gap-3 sm:gap-4',
    md: 'gap-4 sm:gap-6',
    lg: 'gap-6 sm:gap-8'
  }

  return (
    <div className={`grid ${gridCols[columns]} ${gapClasses[gap]} ${className}`}>
      {children}
    </div>
  )
}

// Enhanced Section Component with mobile-first design
interface DashboardSectionProps {
  title: string
  icon?: ReactNode
  children: ReactNode
  className?: string
  headerAction?: ReactNode
  variant?: 'default' | 'prominent' | 'subtle'
  collapsible?: boolean
}

export function DashboardSection({ 
  title, 
  icon, 
  children, 
  className = '',
  headerAction,
  variant = 'default',
  collapsible = false
}: DashboardSectionProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  
  const variants = {
    default: 'bg-white/5 border-white/10',
    prominent: 'bg-gradient-to-br from-purple-600/10 to-pink-600/10 border-purple-500/20',
    subtle: 'bg-white/[0.02] border-white/5'
  }

  return (
    <div className={`backdrop-blur-sm border rounded-xl sm:rounded-2xl p-4 sm:p-6 ${variants[variant]} ${className}`}>
      {/* Section Header */}
      <div className="flex items-center justify-between mb-4 sm:mb-6">
        {collapsible ? (
          <button
            className="flex items-center gap-2 sm:gap-3 cursor-pointer hover:opacity-80 transition-opacity flex-1 min-w-0"
            onClick={() => setIsCollapsed(!isCollapsed)}
            aria-expanded={!isCollapsed}
            aria-controls={`section-${title.replace(/\s+/g, '-').toLowerCase()}`}
          >
            {icon && <div className="text-purple-400 flex-shrink-0">{icon}</div>}
            <h2 className="text-lg sm:text-xl font-semibold text-white truncate">{title}</h2>
            <div className={`text-white/60 transition-transform duration-200 ${isCollapsed ? 'rotate-180' : ''}`}>
              ▼
            </div>
          </button>
        ) : (
          <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
            {icon && <div className="text-purple-400 flex-shrink-0">{icon}</div>}
            <h2 className="text-lg sm:text-xl font-semibold text-white truncate">{title}</h2>
          </div>
        )}
        {headerAction && (
          <div className="flex-shrink-0 ml-2">
            {headerAction}
          </div>
        )}
      </div>

      {/* Section Content */}
      {!isCollapsed && (
        <div 
          className="transition-opacity duration-200 opacity-100"
          id={`section-${title.replace(/\s+/g, '-').toLowerCase()}`}
        >
          {children}
        </div>
      )}
    </div>
  )
}

// Enhanced Card Component with better touch targets
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
  const baseClasses = 'bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4 transition-all duration-200'
  const interactiveClasses = hover || clickable 
    ? 'hover:bg-white/8 hover:border-white/20 active:scale-[0.98] active:bg-white/12'
    : ''
  const clickableClasses = clickable ? 'cursor-pointer touch-manipulation' : ''

  return (
    <div 
      className={`${baseClasses} ${interactiveClasses} ${clickableClasses} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}
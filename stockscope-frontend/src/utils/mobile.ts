// Mobile-first utility classes and constants
export const MOBILE_BREAKPOINTS = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px'
} as const

// Responsive text sizing patterns
export const RESPONSIVE_TEXT = {
  xs: 'text-xs sm:text-sm',
  sm: 'text-sm sm:text-base',
  base: 'text-base sm:text-lg',
  lg: 'text-lg sm:text-xl',
  xl: 'text-xl sm:text-2xl',
  '2xl': 'text-2xl sm:text-3xl',
  '3xl': 'text-3xl sm:text-4xl',
  '4xl': 'text-4xl sm:text-5xl'
} as const

// Responsive spacing patterns
export const RESPONSIVE_SPACING = {
  xs: 'p-2 sm:p-3',
  sm: 'p-3 sm:p-4',
  md: 'p-4 sm:p-6',
  lg: 'p-6 sm:p-8',
  xl: 'p-8 sm:p-10'
} as const

// Responsive gap patterns
export const RESPONSIVE_GAPS = {
  xs: 'gap-2 sm:gap-3',
  sm: 'gap-3 sm:gap-4',
  md: 'gap-4 sm:gap-6',
  lg: 'gap-6 sm:gap-8'
} as const

// Modal sizes for different screen sizes
export const MODAL_SIZES = {
  sm: 'max-w-sm',
  md: 'max-w-md sm:max-w-lg',
  lg: 'max-w-lg sm:max-w-2xl',
  xl: 'max-w-xl sm:max-w-4xl',
  full: 'max-w-[95vw] sm:max-w-6xl'
} as const

// Touch-friendly button sizes
export const BUTTON_SIZES = {
  xs: 'px-2 py-1 text-xs min-h-[32px]',
  sm: 'px-3 py-1.5 text-sm min-h-[36px] sm:min-h-[40px]',
  md: 'px-4 py-2 text-base min-h-[40px] sm:min-h-[44px]',
  lg: 'px-6 py-3 text-lg min-h-[44px] sm:min-h-[48px]'
} as const

// Grid patterns for different content types
export const GRID_PATTERNS = {
  cards: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  metrics: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4',
  charts: 'grid-cols-1 lg:grid-cols-2',
  features: 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3'
} as const

/**
 * Utility function to detect mobile device based on user agent
 * Returns false during SSR (when window is undefined)
 * Returns true if user agent matches mobile device patterns
 */
export const isMobileDevice = () => {
  if (typeof window !== 'undefined') {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
  }
  return false
}

// Breakpoint value in pixels matching MOBILE_BREAKPOINTS.sm
const MOBILE_BREAKPOINT_PX = 640

/**
 * Get responsive chart dimensions based on device type
 * @param isMobile - Optional flag to force mobile dimensions. If false, automatically detects based on screen width (<640px)
 * @returns Object containing height, pieRadius, fontSize, and legendGap values optimized for mobile or desktop
 */
export const getChartDimensions = (isMobile: boolean = false) => {
  let actualIsMobile = isMobile
  if (typeof window !== 'undefined') {
    const screenWidth = window.innerWidth
    actualIsMobile = isMobile || screenWidth < MOBILE_BREAKPOINT_PX
  }
  
  return {
    height: actualIsMobile ? 200 : 300,
    pieRadius: actualIsMobile ? 60 : 80,
    fontSize: actualIsMobile ? 12 : 14,
    legendGap: actualIsMobile ? 3 : 4
  }
}

// Safe area handling for mobile devices with notches
// Use these style objects in your components: e.g. <div style={SAFE_AREA.top}>...</div>
export const SAFE_AREA = {
  top: { paddingTop: 'env(safe-area-inset-top)' },
  bottom: { paddingBottom: 'env(safe-area-inset-bottom)' },
  left: { paddingLeft: 'env(safe-area-inset-left)' },
  right: { paddingRight: 'env(safe-area-inset-right)' },
  x: { paddingLeft: 'env(safe-area-inset-left)', paddingRight: 'env(safe-area-inset-right)' },
  y: { paddingTop: 'env(safe-area-inset-top)', paddingBottom: 'env(safe-area-inset-bottom)' },
  all: {
    paddingTop: 'env(safe-area-inset-top)',
    paddingBottom: 'env(safe-area-inset-bottom)',
    paddingLeft: 'env(safe-area-inset-left)',
    paddingRight: 'env(safe-area-inset-right)'
  }
} as const
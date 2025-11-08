/**
 * Color constants for consistent theming across the application
 */

// Source colors for different data sources
export const SOURCE_COLORS = {
  NEWS: '#1DA1F2',
  SEC: '#6366F1',
  DEFAULT: '#8B5CF6'
} as const

// Sentiment colors based on sentiment score
export const SENTIMENT_COLORS = {
  POSITIVE: '#10B981',
  NEGATIVE: '#EF4444',
  NEUTRAL: '#F59E0B'
} as const

// Chart colors
export const CHART_COLORS = {
  PRIMARY: '#6366F1'
} as const

/**
 * Get the color for a given source
 * @param source - The source name (e.g., 'News', 'SEC')
 * @returns The corresponding color hex code
 */
export const getSourceColor = (source: string): string => {
  switch (source) {
    case 'News':
      return SOURCE_COLORS.NEWS
    case 'SEC':
      return SOURCE_COLORS.SEC
    default:
      return SOURCE_COLORS.DEFAULT
  }
}

/**
 * Get the color based on sentiment value
 * @param sentiment - The sentiment score
 * @returns The corresponding color hex code
 */
export const getSentimentColor = (sentiment: number): string => {
  if (sentiment > 0.1) {
    return SENTIMENT_COLORS.POSITIVE
  } else if (sentiment < -0.1) {
    return SENTIMENT_COLORS.NEGATIVE
  }
  return SENTIMENT_COLORS.NEUTRAL
}

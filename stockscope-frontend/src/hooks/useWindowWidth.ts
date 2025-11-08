import { useState, useEffect } from 'react'

/**
 * Custom hook to track window width with proper SSR support
 * Returns the current window width, updating on resize events
 */
export function useWindowWidth(): number {
  // Initialize with undefined to avoid hydration mismatch
  const [windowWidth, setWindowWidth] = useState<number | undefined>(undefined)

  useEffect(() => {
    // Handler to call on window resize
    function handleResize() {
      setWindowWidth(window.innerWidth)
    }

    // Set initial width
    handleResize()

    // Add event listener
    window.addEventListener('resize', handleResize)

    // Clean up event listener on unmount
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Return a default value for SSR (desktop size)
  return windowWidth ?? 1024
}

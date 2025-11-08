/**
 * Authentication utility functions
 */

/**
 * Retrieves the password parameter from localStorage and formats it as a query string
 * @returns Query string with password parameter (e.g., "?password=xxx") or empty string if no password
 */
export const getPasswordParam = (): string => {
  const password = localStorage.getItem('stockscope_password')
  return password ? `?password=${encodeURIComponent(password)}` : ''
}

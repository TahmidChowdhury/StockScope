const HISTORY_ENTRY_KEY = '__stockscopeMobileScrollEntry'

/** Scroll ownership for the mobile app frame; Next.js still owns navigation. */
export function createMobileScrollManager() {
  const positions = new Map<string, number>()
  let active: { element: HTMLElement; url: string; entry: string } | null = null
  let historyTarget: { url: string; entry: string; top: number | undefined } | null = null
  let stopRestoring: (() => void) | null = null
  const url = () => window.location.pathname + window.location.search + window.location.hash
  const mobile = () => window.matchMedia('(max-width: 1023px)').matches
  const pathname = (value: string) => value.split(/[?#]/, 1)[0]

  function entryId(preferred?: string) {
    // Native hash navigation can create a null state. Leave it untouched:
    // Next treats a truthy state without its own __NA marker as an external entry.
    if (!mobile() || window.history.state?.__NA !== true) return ''
    const existing = window.history.state?.[HISTORY_ENTRY_KEY]
    const entry = preferred || (typeof existing === 'string' && existing ? existing : window.crypto.randomUUID())
    if (existing !== entry) {
      // Preserve Next's router tree and flags. This labels the current entry;
      // it does not wrap history methods or add a navigation entry.
      window.history.replaceState({ ...window.history.state, [HISTORY_ENTRY_KEY]: entry }, '')
    }
    return entry
  }

  function remember() {
    if (!active?.entry || !mobile() || stopRestoring) return
    positions.delete(active.entry)
    positions.set(active.entry, active.element.scrollTop)
    // This is session-local UI state, never persisted across accounts or reloads.
    if (positions.size > 100) positions.delete(positions.keys().next().value!)
  }

  function restore(top?: number, hash?: string) {
    stopRestoring?.()
    if (!active || !mobile()) return
    const element = active.element
    let frame = 0
    let stopped = false
    const resize = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(schedule)
    const mutation = new MutationObserver(() => {
      observeSize()
      schedule()
    })
    const cancel = () => {
      if (stopped) return
      stopped = true
      window.cancelAnimationFrame(frame)
      resize?.disconnect()
      mutation.disconnect()
      for (const event of ['touchstart', 'pointerdown', 'wheel', 'keydown']) {
        element.removeEventListener(event, cancel)
      }
      if (stopRestoring === cancel) stopRestoring = null
    }
    function observeSize() {
      resize?.disconnect()
      resize?.observe(element)
      // AppShell's inner content wrapper grows as queries and deferred panels load.
      if (element.firstElementChild) resize?.observe(element.firstElementChild)
    }
    function apply() {
      if (stopped || !mobile()) return cancel()
      if (hash) {
        let id = hash.slice(1)
        try { id = decodeURIComponent(id) } catch { /* Keep a malformed fragment literal. */ }
        const target = document.getElementById(id)
        if (id === 'top' || target === element) {
          element.scrollTop = 0
          element.focus({ preventScroll: true })
          cancel()
        } else if (target && element.contains(target)) {
          target.scrollIntoView({ block: 'start' })
          cancel()
        }
        return
      }
      const destination = Math.max(0, top ?? 0)
      element.scrollTop = destination
      // A loading placeholder may not yet have room for the saved position.
      // Keep observing until content grows or the user starts interacting.
      if (element.scrollHeight - element.clientHeight >= destination - 1) cancel()
    }
    function schedule() {
      window.cancelAnimationFrame(frame)
      frame = window.requestAnimationFrame(apply)
    }
    stopRestoring = cancel
    observeSize()
    mutation.observe(element, { childList: true, subtree: true })
    for (const event of ['touchstart', 'pointerdown', 'wheel', 'keydown']) {
      element.addEventListener(event, cancel, { passive: true })
    }
    schedule()
  }

  function sync() {
    if (!active) return
    const next = url()
    const previous = active.url
    const traversal = historyTarget?.url === next ? historyTarget : null
    // Pathname context can update the departing AppShell before its replacement
    // mounts. Only that destination's attach may consume a cross-page traversal.
    if (pathname(next) !== pathname(previous)) return
    const entry = entryId(traversal?.entry)
    if (next === previous && entry === active.entry && !traversal) return
    remember()
    stopRestoring?.()
    active.url = next
    active.entry = entry
    historyTarget = null
    const hash = window.location.hash
    if (traversal) restore(traversal.top, traversal.top === undefined ? hash : undefined)
    else if (hash && hash !== new URL(previous, window.location.origin).hash) restore(undefined, hash)
    // Same-path filters and tabs use scroll:false and retain their current view.
    else remember()
  }

  return {
    start() {
      const onPopState = () => {
        remember()
        const next = url()
        const entry = entryId()
        historyTarget = { url: next, entry, top: positions.get(entry) }
        // Next's earlier listener may commit the destination synchronously. Its
        // entry identity distinguishes that case from an old view at the same URL.
        if (active?.entry === entry) sync()
      }
      const onHashChange = () => sync()
      window.addEventListener('popstate', onPopState)
      window.addEventListener('hashchange', onHashChange)
      window.addEventListener('pagehide', remember)
      return () => {
        window.removeEventListener('popstate', onPopState)
        window.removeEventListener('hashchange', onHashChange)
        window.removeEventListener('pagehide', remember)
        stopRestoring?.()
      }
    },
    attach(element: HTMLElement) {
      const next = url()
      const traversal = historyTarget?.url === next ? historyTarget : null
      active = { element, url: next, entry: entryId(traversal?.entry) }
      historyTarget = null
      element.addEventListener('scroll', remember, { passive: true })
      restore(traversal?.top, traversal?.top === undefined ? window.location.hash : undefined)
      return () => {
        if (active?.element !== element) return
        remember()
        stopRestoring?.()
        element.removeEventListener('scroll', remember)
        active = null
      }
    },
    sync,
  }
}

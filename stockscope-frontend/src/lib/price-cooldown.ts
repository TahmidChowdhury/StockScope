/** A single cancellable deadline timer, including deadlines beyond the timer limit. */
export function scheduleDeadline(deadline: number, expired: () => void): () => void {
  let timer: ReturnType<typeof setTimeout> | undefined
  let cancelled = false
  const check = () => {
    if (cancelled) return
    const remaining = deadline - Date.now()
    if (remaining <= 0) expired()
    else timer = setTimeout(check, Math.min(remaining, 2147483647))
  }
  check()
  return () => { cancelled = true; if (timer !== undefined) clearTimeout(timer) }
}

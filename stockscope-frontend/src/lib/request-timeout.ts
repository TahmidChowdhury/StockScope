/** Combine query cancellation and a timeout without newer AbortSignal static APIs. */
export async function withRequestTimeout<T>(
  parent: AbortSignal,
  milliseconds: number,
  request: (signal: AbortSignal) => Promise<T>,
): Promise<T> {
  const controller = new AbortController()
  const cancel = () => controller.abort()
  if (parent.aborted) cancel()
  else parent.addEventListener('abort', cancel, { once: true })
  const timer = setTimeout(cancel, milliseconds)
  try {
    return await request(controller.signal)
  } finally {
    clearTimeout(timer)
    parent.removeEventListener('abort', cancel)
  }
}

/** Only explicitly selected workspace data belongs here; credentials never do. */
export type DraftStatus =
  'loading' | 'saved' | 'empty' | 'memory-only' | 'invalid' | 'unavailable'
export interface DraftSnapshot<T> {
  value: T
  ready: boolean
  status: DraftStatus
  savedAt: string | null
  message: string | null
  generation: number
}
export type DraftValidator<T> = (value: unknown) => value is T
export type DraftUpdate<T> = T | ((previous: T) => T)
type BrowserStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
export const MAX_DRAFT_CHARACTERS = 1_000_000

export function workspaceDraftKey(
  apiOrigin: string,
  role: string,
  key: string,
): string {
  return `stockscope.workspace.v1:${encodeURIComponent(apiOrigin)}:${role}:${encodeURIComponent(key)}`
}

/** Synchronous, shared store: pending work can finish after its page unmounts. */
export function createDraftStore<T>(
  storage: BrowserStorage,
  storageKey: string,
  initial: T,
  validate: DraftValidator<T>,
) {
  let snapshot: DraftSnapshot<T> = {
    value: initial,
    ready: true,
    status: 'empty',
    savedAt: null,
    message: null,
    generation: 0,
  }
  let lastRaw: string | null | undefined
  const listeners = new Set<() => void>()
  const publish = (next: DraftSnapshot<T>) => {
    snapshot = next
    listeners.forEach((listener) => listener())
  }
  const refresh = () => {
    let raw: string | null
    try {
      raw = storage.getItem(storageKey)
    } catch {
      if (
        snapshot.status !== 'unavailable' &&
        snapshot.status !== 'memory-only'
      )
        publish({
          ...snapshot,
          status: 'unavailable',
          message:
            'Browser storage is unavailable. Changes will stay in memory until you leave or refresh.',
        })
      return
    }
    if (raw === lastRaw) return
    lastRaw = raw
    if (raw === null) {
      publish({
        value: initial,
        ready: true,
        status: 'empty',
        savedAt: null,
        message: null,
        generation: snapshot.generation + 1,
      })
      return
    }
    try {
      if (raw.length > MAX_DRAFT_CHARACTERS) throw new Error('oversized')
      const stored = JSON.parse(raw)
      if (
        stored.version !== 1 ||
        typeof stored.updatedAt !== 'string' ||
        !Number.isFinite(Date.parse(stored.updatedAt)) ||
        !validate(stored.value)
      )
        throw new Error('invalid')
      publish({
        value: stored.value,
        ready: true,
        status: 'saved',
        savedAt: stored.updatedAt,
        message: null,
        generation: snapshot.generation + 1,
      })
    } catch {
      publish({
        value: initial,
        ready: true,
        status: 'invalid',
        savedAt: null,
        message:
          'This browser’s saved draft could not be restored. Reset it or start a new draft.',
        generation: snapshot.generation + 1,
      })
    }
  }
  refresh()
  return {
    getSnapshot: () => snapshot,
    subscribe(listener: () => void) {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
    refresh,
    setValue(update: DraftUpdate<T>, expectedGeneration?: number): boolean {
      refresh()
      if (
        expectedGeneration !== undefined &&
        expectedGeneration !== snapshot.generation
      )
        return false
      const value =
        typeof update === 'function'
          ? (update as (previous: T) => T)(snapshot.value)
          : update
      if (Object.is(value, snapshot.value)) return true
      if (!validate(value)) {
        publish({
          ...snapshot,
          status: 'memory-only',
          message:
            'These changes could not be saved because the draft format is invalid.',
        })
        return false
      }
      const updatedAt = new Date().toISOString()
      try {
        const raw = JSON.stringify({ version: 1, updatedAt, value })
        if (raw.length > MAX_DRAFT_CHARACTERS) throw new Error('oversized')
        storage.setItem(storageKey, raw)
        lastRaw = raw
        publish({
          ...snapshot,
          value,
          status: 'saved',
          savedAt: updatedAt,
          message: null,
        })
        return true
      } catch {
        publish({
          ...snapshot,
          value,
          status: 'memory-only',
          message:
            'This draft could not be saved in browser storage. Your latest changes will be lost if you leave or refresh.',
        })
        return false
      }
    },
    reset() {
      try {
        storage.removeItem(storageKey)
        lastRaw = null
        publish({
          value: initial,
          ready: true,
          status: 'empty',
          savedAt: null,
          message: null,
          generation: snapshot.generation + 1,
        })
      } catch {
        publish({
          value: initial,
          ready: true,
          status: 'memory-only',
          savedAt: null,
          message:
            'Browser storage could not clear this draft. The previous saved copy may return after refresh.',
          generation: snapshot.generation + 1,
        })
      }
    },
  }
}

export type WorkspaceDraftStore<T> = ReturnType<typeof createDraftStore<T>>

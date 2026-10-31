'use client'

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { API_BASE_URL, AUTH_CHANGED_EVENT, getAuthSession } from '@/lib/api'
import {
  createDraftStore,
  workspaceDraftKey,
  type DraftSnapshot,
  type DraftUpdate,
  type DraftValidator,
  type WorkspaceDraftStore,
} from '@/lib/workspace-drafts'

const stores = new Map<string, WorkspaceDraftStore<unknown>>()
const nothing = () => () => {}

export function useWorkspaceDraft<T>(
  key: string,
  initialValue: T,
  validate: DraftValidator<T>,
) {
  const defaults = useRef({ key, value: initialValue, validate })
  const [binding, setBinding] = useState<{
    store: WorkspaceDraftStore<T>
    token: string
    role: string
    storageKey: string
    key: string
  } | null>(null)
  const fallback = useRef<{ key: string; snapshot: DraftSnapshot<T> }>({
    key,
    snapshot: {
      value: initialValue,
      ready: false,
      status: 'loading',
      savedAt: null,
      message: null,
      generation: 0,
    },
  })
  // A different company/portfolio is a different workspace, including defaults.
  if (defaults.current.key !== key) {
    defaults.current = { key, value: initialValue, validate }
    fallback.current = {
      key,
      snapshot: {
        value: initialValue,
        ready: false,
        status: 'loading',
        savedAt: null,
        message: null,
        generation: 0,
      },
    }
  }
  const active = binding?.key === key ? binding : null

  useEffect(() => {
    const session = getAuthSession()
    if (!session) return
    const storageKey = workspaceDraftKey(API_BASE_URL, session.user ? `user-${session.user.id}` : session.role, key)
    let store = stores.get(storageKey) as WorkspaceDraftStore<T> | undefined
    if (!store) {
      // Access to the localStorage property itself may be disabled by the browser.
      const storage = {
        getItem: (name: string) => window.localStorage.getItem(name),
        setItem: (name: string, value: string) =>
          window.localStorage.setItem(name, value),
        removeItem: (name: string) => window.localStorage.removeItem(name),
      }
      store = createDraftStore(
        storage,
        storageKey,
        defaults.current.value,
        defaults.current.validate,
      )
      stores.set(storageKey, store as WorkspaceDraftStore<unknown>)
    } else store.refresh()
    setBinding({
      store,
      token: session.accessToken,
      role: session.role,
      storageKey,
      key,
    })
    const sync = (event: StorageEvent) => {
      if (event.key === storageKey || event.key === null) store.refresh()
    }
    const authChanged = () => setBinding(null)
    window.addEventListener('storage', sync)
    window.addEventListener(AUTH_CHANGED_EVENT, authChanged)
    return () => {
      window.removeEventListener('storage', sync)
      window.removeEventListener(AUTH_CHANGED_EVENT, authChanged)
    }
  }, [key])

  const snapshot = useSyncExternalStore(
    active?.store.subscribe ?? nothing,
    active?.store.getSnapshot ?? (() => fallback.current.snapshot),
    () => fallback.current.snapshot,
  )
  const authorized = useCallback(() => {
    const session = getAuthSession()
    return (
      !!active &&
      session?.accessToken === active.token &&
      session.role === active.role
    )
  }, [active])
  const setValue = useCallback(
    (update: DraftUpdate<T>, expectedGeneration?: number) => {
      if (active && authorized())
        active.store.setValue(update, expectedGeneration)
    },
    [active, authorized],
  )
  const reset = useCallback(() => {
    if (active && authorized()) active.store.reset()
  }, [active, authorized])
  return { ...snapshot, setValue, reset }
}

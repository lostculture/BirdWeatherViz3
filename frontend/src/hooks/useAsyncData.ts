/**
 * useAsyncData
 * Loads one panel's data independently of every other panel on the page.
 *
 * The Analytics page used to fetch all ten charts in a single Promise.all, so
 * one slow query took the whole page down with "Error: timeout of 30000ms
 * exceeded" and nothing rendered. Each chart now owns its own request: the
 * fast ones paint immediately, and a failure is confined to its own panel with
 * a Retry button.
 *
 * Version: 1.0.0
 */

import { useCallback, useEffect, useRef, useState } from 'react'

export interface AsyncData<T> {
  data: T
  loading: boolean
  error: string | null
  reload: () => void
}

function messageFor(err: unknown): string {
  if (err && typeof err === 'object') {
    const axiosLike = err as { code?: string; message?: string }
    // Axios reports a client-side timeout with this code. Say what it means
    // rather than echoing "timeout of 30000ms exceeded" at the user.
    if (axiosLike.code === 'ECONNABORTED') {
      return 'This chart took too long to load. The analytics summaries may still be building.'
    }
    if (axiosLike.message) return axiosLike.message
  }
  return 'Failed to load'
}

/**
 * Run `fetcher` whenever `deps` change, tracking loading and error state.
 *
 * @param fetcher   Loader for this panel. Must be stable or wrapped in useCallback.
 * @param deps      Values that should trigger a refetch.
 * @param initial   Value to show before the first response.
 */
export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList,
  initial: T,
): AsyncData<T> {
  const [data, setData] = useState<T>(initial)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)

  // Guards against a slow earlier request overwriting a newer one's result.
  const requestId = useRef(0)

  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    const id = ++requestId.current
    let cancelled = false

    setLoading(true)
    setError(null)

    fetcherRef
      .current()
      .then((result) => {
        if (cancelled || id !== requestId.current) return
        setData(result)
      })
      .catch((err) => {
        if (cancelled || id !== requestId.current) return
        setError(messageFor(err))
      })
      .finally(() => {
        if (cancelled || id !== requestId.current) return
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
    // biome-ignore lint/correctness/useExhaustiveDependencies: the caller declares its own dependencies; `nonce` drives manual reloads
  }, [...deps, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  return { data, loading, error, reload }
}

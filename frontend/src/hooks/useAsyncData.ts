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
 * @param fetcher   Loader for this panel. Held in a ref, so the caller does
 *                  not need to memoise it.
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

  // Guards against a slow earlier request overwriting a newer one's result.
  const requestId = useRef(0)

  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  // Stable, so it can serve as both the effect body and the Retry handler —
  // which is why this hook needs no separate "reload nonce" dependency.
  const run = useCallback(() => {
    const id = ++requestId.current

    setLoading(true)
    setError(null)

    fetcherRef
      .current()
      .then((result) => {
        // A newer request has started, or we unmounted: its result wins.
        if (id !== requestId.current) return
        setData(result)
        setLoading(false)
      })
      .catch((err) => {
        if (id !== requestId.current) return
        setError(messageFor(err))
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    run()
    return () => {
      // Abandon the in-flight request when the dependencies change or the
      // panel unmounts, so a late response never writes to dead state.
      requestId.current++
    }
  }, [run, ...deps])

  return { data, loading, error, reload: run }
}

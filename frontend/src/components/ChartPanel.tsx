/**
 * ChartPanel
 * Card wrapper that carries one chart's own loading, error and empty states.
 *
 * Pairs with useAsyncData: because every panel loads independently, a panel
 * that fails or times out shows a Retry button in place of the chart while the
 * rest of the page stays usable.
 *
 * Version: 1.0.0
 */

import React, { ReactNode } from 'react'

interface ChartPanelProps {
  /** Optional heading shown above the description. */
  title?: string
  /** One-line explanation of what the chart shows. */
  description?: ReactNode
  loading: boolean
  error: string | null
  /** True when the request succeeded but returned nothing to plot. */
  isEmpty: boolean
  /** Message for the empty state. */
  emptyMessage?: string
  onRetry?: () => void
  /** Height of the loading/empty placeholder, so the page doesn't jump. */
  minHeight?: string
  className?: string
  children: ReactNode
}

const ChartPanel: React.FC<ChartPanelProps> = ({
  title,
  description,
  loading,
  error,
  isEmpty,
  emptyMessage = 'No data available',
  onRetry,
  minHeight = 'h-64',
  className = '',
  children,
}) => {
  // Keep showing the previous chart while a refetch is in flight — swapping a
  // rendered chart for a spinner on every filter change is more disruptive
  // than a brief stale frame.
  const showPlaceholder = (loading && isEmpty) || error !== null || isEmpty

  return (
    <div className={`bg-white rounded-lg shadow p-4 ${className}`}>
      {title && (
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-lg font-semibold">{title}</h3>
          {loading && !isEmpty && (
            <span
              className="inline-block w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"
              aria-label="Refreshing"
            />
          )}
        </div>
      )}
      {description && <p className="text-sm text-muted-foreground mb-2">{description}</p>}

      {showPlaceholder ? (
        <div className={`${minHeight} flex flex-col items-center justify-center gap-3 text-center`}>
          {error !== null ? (
            <>
              <p className="text-sm text-red-600 max-w-md">{error}</p>
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="px-3 py-1 text-sm rounded border border-red-300 text-red-700 hover:bg-red-50"
                >
                  Retry
                </button>
              )}
            </>
          ) : loading ? (
            <>
              <span className="inline-block w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-muted-foreground">Loading…</span>
            </>
          ) : (
            <span className="text-sm text-muted-foreground">{emptyMessage}</span>
          )}
        </div>
      ) : (
        children
      )}
    </div>
  )
}

export default ChartPanel

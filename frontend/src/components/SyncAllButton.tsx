import React from 'react'
import { useSync } from '../context/SyncContext'

interface SyncAllButtonProps {
  variant: 'header' | 'page'
  disabled?: boolean
}

const SyncAllButton: React.FC<SyncAllButtonProps> = ({ variant, disabled }) => {
  const { syncing, syncAll } = useSync()

  if (variant === 'header') {
    return (
      <button
        type="button"
        onClick={syncAll}
        disabled={syncing || disabled}
        className="flex items-center space-x-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors bg-green-600 hover:bg-green-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
        title={syncing ? 'Sync in progress...' : 'Sync all stations'}
      >
        {syncing ? (
          <span className="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <svg
            className="w-3.5 h-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        )}
        <span>{syncing ? 'Syncing...' : 'Sync'}</span>
      </button>
    )
  }

  // page variant — same style as existing Configuration page button
  return (
    <button
      type="button"
      onClick={syncAll}
      disabled={syncing || disabled}
      className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
    >
      {syncing ? 'Syncing All...' : 'Sync All Stations'}
    </button>
  )
}

export default SyncAllButton

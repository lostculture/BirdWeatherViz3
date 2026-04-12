/**
 * Layout Component
 * Main application layout with navigation and content area.
 *
 * Version: 1.1.0
 */

import React, { ReactNode, useEffect, useState, useRef } from 'react'
import { stationsApi } from '../../api'
import FilterBar from './FilterBar'
import Navigation from './Navigation'

interface LayoutProps {
  children: ReactNode
}

interface SyncStatus {
  syncing: boolean
  message: string
  error: boolean
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const hasSynced = useRef(false)

  // Auto-sync all stations on app load
  useEffect(() => {
    if (hasSynced.current) return
    hasSynced.current = true

    const autoSync = async () => {
      try {
        // Check if there are any stations first
        const stations = await stationsApi.getAll({ active_only: true })
        if (stations.length === 0) {
          return // No stations to sync
        }

        setSyncStatus({
          syncing: true,
          message: 'Syncing stations (this may take a few minutes)...',
          error: false,
        })

        const result = await stationsApi.syncAll()

        if (result.total_detections_added > 0) {
          setSyncStatus({
            syncing: false,
            message: `Synced ${result.total_detections_added} new detections`,
            error: false,
          })
        } else {
          setSyncStatus({
            syncing: false,
            message: 'All stations up to date',
            error: false,
          })
        }

        // Auto-hide success message after 5 seconds
        setTimeout(() => setSyncStatus(null), 5000)
      } catch (err: any) {
        console.error('Auto-sync failed:', err)

        // Check if it's a timeout error
        const isTimeout = err.message?.includes('timeout') || err.code === 'ECONNABORTED'

        setSyncStatus({
          syncing: false,
          message: isTimeout
            ? 'Initial sync taking longer than expected - sync manually from Configuration'
            : 'Sync failed - check Configuration',
          error: true,
        })
        // Keep error visible for longer
        setTimeout(() => setSyncStatus(null), 15000)
      }
    }

    // Small delay to let the app initialize
    const timer = setTimeout(autoSync, 1000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navigation />
      <FilterBar />

      {/* Sync Status Banner */}
      {syncStatus && (
        <div
          className={`px-4 py-2 text-center text-sm font-medium transition-all ${
            syncStatus.error
              ? 'bg-red-100 text-red-800'
              : syncStatus.syncing
                ? 'bg-indigo-cerulean/20 text-indigo-deep'
                : 'bg-green-100 text-green-800'
          }`}
        >
          {syncStatus.syncing && (
            <span className="inline-block w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
          )}
          {syncStatus.message}
          {!syncStatus.syncing && (
            <button type="button"
              onClick={() => setSyncStatus(null)}
              className="ml-4 opacity-60 hover:opacity-100"
              aria-label="Dismiss"
            >
              ×
            </button>
          )}
        </div>
      )}

      <main className="flex-1 container mx-auto px-4 py-6">{children}</main>
      <footer className="bg-indigo-dark text-white/80 py-4 mt-auto">
        <div className="container mx-auto px-4 text-center text-sm">
          <p>BirdWeatherViz3 - Next Generation Bird Detection Visualization Platform</p>
          <p className="mt-1 opacity-75">Powered by BirdWeather API | Version 1.1.0</p>
        </div>
      </footer>
    </div>
  )
}

export default Layout

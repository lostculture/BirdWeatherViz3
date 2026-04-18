/**
 * Layout Component
 * Main application layout with navigation and content area.
 *
 * Version: 2.0.0
 */

import React, { ReactNode, useEffect, useRef, useState } from 'react'
import { settingsApi, stationsApi } from '../../api'
import { useSync } from '../../context/SyncContext'
import FilterBar from './FilterBar'
import Navigation from './Navigation'

interface LayoutProps {
  children: ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { syncing, progress, error, lastResult, syncAll } = useSync()
  const hasSynced = useRef(false)
  const [bannerVisible, setBannerVisible] = useState(false)
  const [bannerMessage, setBannerMessage] = useState('')
  const [bannerError, setBannerError] = useState(false)

  // Show banner when sync state changes
  useEffect(() => {
    if (syncing) {
      setBannerVisible(true)
      setBannerMessage(progress || 'Syncing stations...')
      setBannerError(false)
    } else if (error) {
      setBannerVisible(true)
      setBannerMessage(error)
      setBannerError(true)
      const timer = setTimeout(() => setBannerVisible(false), 15000)
      return () => clearTimeout(timer)
    } else if (lastResult) {
      setBannerVisible(true)
      setBannerMessage(
        lastResult.total > 0
          ? `Synced ${lastResult.total} new detections`
          : 'All stations up to date',
      )
      setBannerError(false)
      const timer = setTimeout(() => setBannerVisible(false), 5000)
      return () => clearTimeout(timer)
    }
  }, [syncing, progress, error, lastResult])

  // Auto-sync on app load if the setting is enabled
  useEffect(() => {
    if (hasSynced.current) return
    hasSynced.current = true

    const maybeAutoSync = async () => {
      try {
        const enabled = await settingsApi.getAutoUpdateOnStart()
        if (!enabled) return

        const stations = await stationsApi.getAll({ active_only: true })
        if (stations.length === 0) return

        await syncAll()
      } catch (err) {
        console.error('Auto-sync check failed:', err)
      }
    }

    const timer = setTimeout(maybeAutoSync, 1000)
    return () => clearTimeout(timer)
  }, [syncAll])

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navigation />
      <FilterBar />

      {/* Sync Status Banner */}
      {bannerVisible && (
        <div
          className={`px-4 py-2 text-center text-sm font-medium transition-all ${
            bannerError
              ? 'bg-red-100 text-red-800'
              : syncing
                ? 'bg-indigo-cerulean/20 text-indigo-deep'
                : 'bg-green-100 text-green-800'
          }`}
        >
          {syncing && (
            <span className="inline-block w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
          )}
          {bannerMessage}
          {!syncing && (
            <button
              type="button"
              onClick={() => setBannerVisible(false)}
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
          <p className="mt-1 opacity-75">Powered by BirdWeather API</p>
        </div>
      </footer>
    </div>
  )
}

export default Layout

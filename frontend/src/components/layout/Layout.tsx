/**
 * Layout Component
 * Main application layout with navigation and content area.
 *
 * Version: 2.0.0
 */

import React, { ReactNode, useEffect, useRef, useState } from 'react'
import { authApi, settingsApi, stationsApi, systemApi } from '../../api'
import type { UpdateInfo } from '../../api/system'
import { useSync } from '../../context/SyncContext'
import FilterBar from './FilterBar'
import Navigation from './Navigation'

const UPDATE_DISMISS_KEY_PREFIX = 'update_dismissed_v'

interface LayoutProps {
  children: ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { syncing, progress, error, lastResult, syncAll } = useSync()
  const hasSynced = useRef(false)
  const hasCheckedUpdate = useRef(false)
  const [bannerVisible, setBannerVisible] = useState(false)
  const [bannerMessage, setBannerMessage] = useState('')
  const [bannerError, setBannerError] = useState(false)
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null)
  const [updateDismissed, setUpdateDismissed] = useState(false)

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
        // Skip silently for unauthenticated visitors. The backend scheduler
        // (apscheduler, every 10 min) keeps detections fresh without any
        // frontend interaction; auto-sync-on-load is just a "catch up
        // immediately" nicety for logged-in users and the desktop app.
        const info = await systemApi.getInfo().catch(() => null)
        const isDesktop = info?.mode === 'desktop'
        if (!isDesktop && !authApi.isAuthenticated()) return

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

  // Check for newer release on GitHub. The backend caches for 6 hours; we
  // call once per page load. Dismiss is per-version so a newer release
  // re-shows the banner automatically.
  useEffect(() => {
    if (hasCheckedUpdate.current) return
    hasCheckedUpdate.current = true

    systemApi
      .getUpdateInfo()
      .then((info) => {
        setUpdateInfo(info)
        if (info.latest) {
          const dismissed =
            localStorage.getItem(UPDATE_DISMISS_KEY_PREFIX + info.latest) === '1'
          setUpdateDismissed(dismissed)
        }
      })
      .catch((err) => {
        // Network or server error — silent. The banner just doesn't appear.
        console.debug('Update check failed:', err)
      })
  }, [])

  const dismissUpdateBanner = () => {
    if (updateInfo?.latest) {
      localStorage.setItem(UPDATE_DISMISS_KEY_PREFIX + updateInfo.latest, '1')
    }
    setUpdateDismissed(true)
  }

  const showUpdateBanner =
    updateInfo?.update_available && updateInfo.enabled && !updateDismissed

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navigation />
      <FilterBar />

      {/* Update-available banner */}
      {showUpdateBanner && updateInfo && (
        <div className="px-4 py-2 text-center text-sm font-medium bg-amber-100 text-amber-900 border-b border-amber-200">
          <span className="inline-block w-2 h-2 mr-2 rounded-full bg-amber-500 animate-pulse" />
          Update available: <strong>v{updateInfo.latest}</strong> (you're on
          v{updateInfo.current}).
          {updateInfo.release_url && (
            <>
              {' '}
              <a
                href={updateInfo.release_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:no-underline"
              >
                Release notes →
              </a>
            </>
          )}
          <button
            type="button"
            onClick={dismissUpdateBanner}
            className="ml-4 opacity-60 hover:opacity-100"
            aria-label="Dismiss update notification"
            title="Dismiss until the next release"
          >
            ×
          </button>
        </div>
      )}

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

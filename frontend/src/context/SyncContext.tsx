import React, { createContext, useContext, useState, useRef, useCallback, ReactNode } from 'react'
import { stationsApi } from '../api'

interface SyncDetail {
  station_name: string
  detections_added: number
  status: string
}

interface SyncContextType {
  syncing: boolean
  progress: string
  details: SyncDetail[]
  lastResult: { total: number; stations: number } | null
  error: string | null
  lastSyncedAt: Date | null
  syncAll: () => Promise<void>
}

const SyncContext = createContext<SyncContextType | undefined>(undefined)

export const SyncProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [syncing, setSyncing] = useState(false)
  const [progress, setProgress] = useState('')
  const [details, setDetails] = useState<SyncDetail[]>([])
  const [lastResult, setLastResult] = useState<{ total: number; stations: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null)
  const lockRef = useRef(false)

  const syncAll = useCallback(async () => {
    if (lockRef.current) return
    lockRef.current = true
    setSyncing(true)
    setProgress('Starting sync...')
    setDetails([])
    setError(null)

    try {
      for await (const event of stationsApi.syncAllStream()) {
        switch (event.type) {
          case 'start':
            setProgress(event.message || 'Starting...')
            break
          case 'progress':
            setProgress(event.message || 'Processing...')
            break
          case 'station_complete':
            setProgress(`Completed: ${event.station_name} (+${event.detections_added} detections)`)
            setDetails((prev) => [
              ...prev,
              {
                station_name: event.station_name || '',
                detections_added: event.detections_added || 0,
                status: event.status || '',
              },
            ])
            break
          case 'station_error':
            setProgress(`Error syncing ${event.station_name}`)
            setDetails((prev) => [
              ...prev,
              {
                station_name: event.station_name || '',
                detections_added: 0,
                status: `error: ${event.error}`,
              },
            ])
            break
          case 'weather_complete':
            setProgress(
              event.days_fetched
                ? `Weather: ${event.days_fetched} days synced`
                : 'Weather: Already up to date',
            )
            break
          case 'weather_error':
            setProgress(`Weather sync failed: ${event.error}`)
            break
          case 'complete':
            setProgress(`Complete! ${event.total_detections_added} new detections`)
            setLastResult({
              total: event.total_detections_added || 0,
              stations: event.stations_synced || 0,
            })
            setLastSyncedAt(new Date())
            break
        }
      }
    } catch (err: any) {
      const isTimeout = err.message?.includes('timeout') || err.code === 'ECONNABORTED'
      setError(
        isTimeout
          ? 'Sync timed out — try syncing individual stations from Configuration'
          : err.message || 'Sync failed',
      )
    } finally {
      setSyncing(false)
      lockRef.current = false
    }
  }, [])

  return (
    <SyncContext.Provider
      value={{ syncing, progress, details, lastResult, error, lastSyncedAt, syncAll }}
    >
      {children}
    </SyncContext.Provider>
  )
}

export function useSync(): SyncContextType {
  const ctx = useContext(SyncContext)
  if (!ctx) throw new Error('useSync must be used within a SyncProvider')
  return ctx
}

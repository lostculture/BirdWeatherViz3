/**
 * Stations API Service
 * API methods for station-related endpoints.
 *
 * Version: 1.0.0
 */

import type { StationCreate, StationResponse, StationStats, StationUpdate } from '../types/api'
import { apiClient } from './client'

export const stationsApi = {
  /**
   * Get all stations
   */
  getAll: async (params?: { active_only?: boolean }): Promise<StationResponse[]> => {
    return apiClient.get<StationResponse[]>('/stations/', params)
  },

  /**
   * Get station by ID
   */
  getById: async (stationId: number): Promise<StationResponse> => {
    return apiClient.get<StationResponse>(`/stations/${stationId}`)
  },

  /**
   * Create new station
   */
  create: async (data: StationCreate): Promise<StationResponse> => {
    return apiClient.post<StationResponse>('/stations/', data)
  },

  /**
   * Update station
   */
  update: async (stationId: number, data: StationUpdate): Promise<StationResponse> => {
    return apiClient.put<StationResponse>(`/stations/${stationId}`, data)
  },

  /**
   * Delete station
   */
  delete: async (stationId: number): Promise<void> => {
    return apiClient.delete<void>(`/stations/${stationId}`)
  },

  /**
   * Get station statistics
   */
  getStats: async (stationId: number): Promise<StationStats> => {
    return apiClient.get<StationStats>(`/stations/${stationId}/stats`)
  },

  /**
   * Get comparison statistics for all stations
   */
  getComparison: async (): Promise<StationStats[]> => {
    return apiClient.get<StationStats[]>('/stations/comparison/all')
  },

  /**
   * Sync detection data from BirdWeather API (intelligent sync).
   * Pass `forceFull: true` to paginate BirdWeather's full history — use to
   * recover from a station whose history was truncated by an earlier sync.
   */
  sync: async (
    stationId: number,
    forceFull?: boolean,
  ): Promise<{ success: boolean; detections_added: number; message: string }> => {
    const qs = forceFull ? '?force_full=true' : ''
    return apiClient.post<{ success: boolean; detections_added: number; message: string }>(
      `/stations/${stationId}/sync${qs}`,
      undefined,
      { timeout: forceFull ? 1800000 : 300000 }, // 30 min for full re-sync
    )
  },

  /**
   * Sync all active stations (legacy non-streaming)
   */
  syncAll: async (): Promise<{
    success: boolean
    total_detections_added: number
    stations_synced: number
    details: Array<{ station_name: string; detections_added: number; status: string }>
    weather_synced: boolean
    weather_days_fetched: number
  }> => {
    return apiClient.post(
      '/stations/sync-all',
      undefined,
      { timeout: 600000 }, // 10 minute timeout for sync all
    )
  },

  /**
   * Sync all active stations with streaming progress updates.
   * Returns an async generator that yields progress events.
   */
  syncAllStream: async function* (
    onProgress?: (event: SyncProgressEvent) => void,
    forceFull?: boolean,
  ): AsyncGenerator<SyncProgressEvent, void, unknown> {
    const token = localStorage.getItem('auth_token')
    const qs = forceFull ? '?force_full=true' : ''
    const response = await fetch(`/api/v1/stations/sync-all-stream${qs}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    })

    if (!response.ok) {
      let detail = response.statusText
      try {
        const body = await response.text()
        detail = JSON.parse(body).detail || body || detail
      } catch {
        // use statusText
      }
      throw new Error(`Sync failed: ${detail}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Process complete lines (newline-delimited JSON)
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.trim()) {
          try {
            const event = JSON.parse(line) as SyncProgressEvent
            if (onProgress) {
              onProgress(event)
            }
            yield event
          } catch (e) {
            console.error('Failed to parse sync event:', line, e)
          }
        }
      }
    }

    // Process any remaining data
    if (buffer.trim()) {
      try {
        const event = JSON.parse(buffer) as SyncProgressEvent
        if (onProgress) {
          onProgress(event)
        }
        yield event
      } catch (e) {
        console.error('Failed to parse final sync event:', buffer, e)
      }
    }
  },

  /**
   * Get species lists for each station (for UpSet plot)
   */
  getSpeciesByStation: async (): Promise<
    Record<
      string,
      Array<{
        common_name: string
        scientific_name: string
        ebird_code?: string
        inat_taxon_id?: number | null
      }>
    >
  > => {
    return apiClient.get<
      Record<
        string,
        Array<{
          common_name: string
          scientific_name: string
          ebird_code?: string
          inat_taxon_id?: number | null
        }>
      >
    >('/stations/species/by-station')
  },
}

// Types for streaming sync
export interface SyncProgressEvent {
  type:
    | 'start'
    | 'progress'
    | 'station_complete'
    | 'station_error'
    | 'weather_complete'
    | 'weather_error'
    | 'complete'
  message?: string
  total_stations?: number
  station_index?: number
  station_name?: string
  detections_added?: number
  status?: string
  running_total?: number
  error?: string
  success?: boolean
  total_detections_added?: number
  stations_synced?: number
  details?: Array<{ station_name: string; detections_added: number; status: string }>
  weather_synced?: boolean
  weather_days_fetched?: number
  days_fetched?: number
}

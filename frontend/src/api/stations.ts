/**
 * Stations API Service
 * API methods for station-related endpoints.
 *
 * Version: 1.0.0
 */

import { apiClient } from './client'
import type { StationResponse, StationCreate, StationUpdate, StationStats } from '../types/api'

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
}

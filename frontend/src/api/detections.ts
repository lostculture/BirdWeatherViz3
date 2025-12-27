/**
 * Detections API Service
 * API methods for detection-related endpoints.
 *
 * Version: 1.0.0
 */

import { apiClient } from './client'
import type {
  DailyDetectionCount,
  HourlyDetectionPattern,
  DetectionResponse,
  DatabaseStats,
} from '../types/api'

export const detectionsApi = {
  /**
   * Get daily detection counts
   */
  getDailyCounts: async (params?: {
    start_date?: string
    end_date?: string
    station_ids?: string
  }): Promise<DailyDetectionCount[]> => {
    return apiClient.get<DailyDetectionCount[]>('/detections/daily-counts', params)
  },

  /**
   * Get detections by species
   */
  getBySpecies: async (
    speciesId: number,
    params?: {
      start_date?: string
      end_date?: string
      station_ids?: string
    }
  ): Promise<any[]> => {
    return apiClient.get<any[]>(`/detections/by-species/${speciesId}`, params)
  },

  /**
   * Get hourly detection pattern
   */
  getHourlyPattern: async (params?: {
    species_id?: number
    station_ids?: string
  }): Promise<HourlyDetectionPattern[]> => {
    return apiClient.get<HourlyDetectionPattern[]>('/detections/hourly-pattern', params)
  },

  /**
   * Get recent detections
   */
  getRecent: async (params?: {
    limit?: number
    station_ids?: string
  }): Promise<DetectionResponse[]> => {
    return apiClient.get<DetectionResponse[]>('/detections/recent', params)
  },

  /**
   * Get detection statistics
   */
  getStats: async (params?: {
    start_date?: string
    end_date?: string
    station_ids?: string
  }): Promise<DatabaseStats> => {
    return apiClient.get<DatabaseStats>('/detections/stats', params)
  },
}

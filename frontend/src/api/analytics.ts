/**
 * Analytics API Service
 * API methods for advanced analytics endpoints.
 *
 * Version: 1.0.0
 */

import { apiClient } from './client'

export interface SpeciesHourBubble {
  species_id: number
  common_name: string
  scientific_name: string
  hour: number
  detection_count: number
  total_detections: number
}

export interface PhenologyCell {
  species_id: number
  common_name: string
  week_number: number
  year: number
  detection_count: number
}

export interface ConfidenceScatterPoint {
  species_id: number
  common_name: string
  scientific_name: string
  total_detections: number
  avg_confidence: number
  detection_days: number
}

export interface ConfidenceByHour {
  hour: number
  confidence_bin: string
  confidence_min: number
  confidence_max: number
  detection_count: number
}

export interface TemporalDistribution {
  species_id: number
  common_name: string
  date: string
  detection_count: number
}

export const analyticsApi = {
  /**
   * Get species activity by hour for bubble chart
   */
  getSpeciesHourBubble: async (params?: {
    limit?: number
    months?: number
    station_ids?: string
    min_confidence?: number
  }): Promise<SpeciesHourBubble[]> => {
    return apiClient.get<SpeciesHourBubble[]>('/analytics/species-hour-bubble', params)
  },

  /**
   * Get phenology data for heatmap
   */
  getPhenology: async (params?: {
    year?: number
    station_ids?: string
    min_confidence?: number
    limit?: number
  }): Promise<PhenologyCell[]> => {
    return apiClient.get<PhenologyCell[]>('/analytics/phenology', params)
  },

  /**
   * Get detection count vs confidence scatter data
   */
  getConfidenceScatter: async (params?: {
    station_ids?: string
    min_detections?: number
  }): Promise<ConfidenceScatterPoint[]> => {
    return apiClient.get<ConfidenceScatterPoint[]>('/analytics/confidence-scatter', params)
  },

  /**
   * Get confidence by hour for heatmap
   */
  getConfidenceByHour: async (params?: {
    station_ids?: string
    months?: number
  }): Promise<ConfidenceByHour[]> => {
    return apiClient.get<ConfidenceByHour[]>('/analytics/confidence-by-hour', params)
  },

  /**
   * Get temporal distribution data
   */
  getTemporalDistribution: async (params?: {
    species_ids?: string
    months?: number
    station_ids?: string
    min_confidence?: number
    limit?: number
  }): Promise<TemporalDistribution[]> => {
    return apiClient.get<TemporalDistribution[]>('/analytics/temporal-distribution', params)
  },
}

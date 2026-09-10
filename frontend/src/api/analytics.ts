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

export interface ChorusSpecies {
  species_id: number
  common_name: string
  english_name?: string | null
  detection_count: number
}

export interface DawnChorusPoint {
  minutes_from_sunrise: number
  detection_count: number
  species_count: number
  /** Most-detected species in this bin, for the hover tooltip. */
  top_species: ChorusSpecies[]
}

export interface DuskChorusPoint {
  minutes_from_sunset: number
  detection_count: number
  species_count: number
  /** Most-detected species in this bin, for the hover tooltip. */
  top_species: ChorusSpecies[]
}

export interface RollupTableState {
  name: string
  last_detection_id: number
  status: 'idle' | 'building' | 'error'
  rows_processed: number
  total_rows: number
  message: string | null
  updated_at: string | null
}

export interface RollupStatus {
  detection: RollupTableState
  solar: RollupTableState
  max_detection_id: number
  detections_pending: number
  ready: boolean
  building: boolean
}

export interface WeatherImpact {
  temperature_bin: string | null
  condition: string | null
  avg_detections: number
  total_detections: number
  observation_count: number
}

export interface WeeklyTrend {
  week_start: string
  year: number
  week_number: number
  total_detections: number
  unique_species: number
  avg_daily_detections: number
}

export interface CoOccurrenceCell {
  species_1: string
  species_2: string
  co_occurrence_days: number
  species_1_total_days: number
  species_2_total_days: number
  jaccard_index: number
}

export interface SpeciesSeasonality {
  species_id: number
  common_name: string
  first_seen: string
  last_seen: string
  peak_month: number
  peak_month_name: string
  total_detections: number
  active_days: number
}

export interface MonthlyChampion {
  month: number
  month_name: string
  species_id: number
  common_name: string
  detection_count: number
  percentage_of_month: number
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

  /**
   * Get dawn chorus analysis data
   */
  getDawnChorus: async (params?: {
    station_ids?: string
    months?: number
    min_confidence?: number
    window_minutes?: number
  }): Promise<DawnChorusPoint[]> => {
    return apiClient.get<DawnChorusPoint[]>('/analytics/dawn-chorus', params)
  },

  /**
   * Get dusk chorus analysis data (sunset-relative)
   */
  getDuskChorus: async (params?: {
    station_ids?: string
    months?: number
    min_confidence?: number
    window_minutes?: number
  }): Promise<DuskChorusPoint[]> => {
    return apiClient.get<DuskChorusPoint[]>('/analytics/dusk-chorus', params)
  },

  /**
   * Get the build state of the analytics rollups.
   */
  getRollupStatus: async (): Promise<RollupStatus> => {
    return apiClient.get<RollupStatus>('/analytics/rollups/status')
  },

  /**
   * Get weather impact analysis data
   */
  getWeatherImpact: async (params?: {
    station_ids?: string
    months?: number
    min_confidence?: number
    analysis_type?: 'temperature' | 'condition' | 'precipitation'
  }): Promise<WeatherImpact[]> => {
    return apiClient.get<WeatherImpact[]>('/analytics/weather-impact', params)
  },

  /**
   * Get weekly detection trends
   */
  getWeeklyTrends: async (params?: {
    station_ids?: string
    months?: number
    min_confidence?: number
  }): Promise<WeeklyTrend[]> => {
    return apiClient.get<WeeklyTrend[]>('/analytics/weekly-trends', params)
  },

  /**
   * Get species co-occurrence matrix data
   */
  getCoOccurrence: async (params?: {
    station_ids?: string
    months?: number
    min_confidence?: number
    limit?: number
  }): Promise<CoOccurrenceCell[]> => {
    return apiClient.get<CoOccurrenceCell[]>('/analytics/co-occurrence', params)
  },

  /**
   * Get species seasonality (first/last sighting) data
   */
  getSpeciesSeasonality: async (params?: {
    station_ids?: string
    min_confidence?: number
    limit?: number
  }): Promise<SpeciesSeasonality[]> => {
    return apiClient.get<SpeciesSeasonality[]>('/analytics/species-seasonality', params)
  },

  /**
   * Get monthly detection champions
   */
  getMonthlyChampions: async (params?: {
    station_ids?: string
    year?: number
    min_confidence?: number
  }): Promise<MonthlyChampion[]> => {
    return apiClient.get<MonthlyChampion[]>('/analytics/monthly-champions', params)
  },
}

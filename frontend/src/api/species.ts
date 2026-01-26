/**
 * Species API Service
 * API methods for species-related endpoints.
 *
 * Version: 1.1.0
 */

import { apiClient } from './client'
import type {
  SpeciesResponse,
  SpeciesDiversityTrend,
  SpeciesDiscoveryCurve,
  NewSpeciesThisWeek,
  FamilyStats,
} from '../types/api'

export interface HourlyPattern {
  hour: number
  detection_count: number
}

export interface MonthlyPattern {
  month: number
  month_name: string
  detection_count: number
}

export interface TimelinePoint {
  date: string
  station_name: string
  detection_count: number
}

export interface StationDistribution {
  station_name: string
  detection_count: number
  percentage: number
}

export interface ConfidenceByStation {
  station_name: string
  avg_confidence: number
  detection_count: number
}

export const speciesApi = {
  /**
   * Get species list
   */
  getList: async (params?: {
    station_ids?: string
    search?: string
  }): Promise<SpeciesResponse[]> => {
    return apiClient.get<SpeciesResponse[]>('/species/', params)
  },

  /**
   * Get species by ID
   */
  getById: async (speciesId: number): Promise<SpeciesResponse> => {
    return apiClient.get<SpeciesResponse>(`/species/${speciesId}`)
  },

  /**
   * Get diversity trend
   */
  getDiversityTrend: async (params?: {
    start_date?: string
    end_date?: string
    station_ids?: string
  }): Promise<SpeciesDiversityTrend[]> => {
    return apiClient.get<SpeciesDiversityTrend[]>('/species/diversity/trend', params)
  },

  /**
   * Get discovery curve
   */
  getDiscoveryCurve: async (params?: {
    start_date?: string
    end_date?: string
    station_ids?: string
  }): Promise<SpeciesDiscoveryCurve[]> => {
    return apiClient.get<SpeciesDiscoveryCurve[]>('/species/discovery/curve', params)
  },

  /**
   * Get new species this week
   */
  getThisWeek: async (params?: {
    station_ids?: string
  }): Promise<NewSpeciesThisWeek[]> => {
    return apiClient.get<NewSpeciesThisWeek[]>('/species/new/this-week', params)
  },

  /**
   * Get family statistics
   */
  getFamilyStats: async (params?: {
    start_date?: string
    end_date?: string
    station_ids?: string
  }): Promise<FamilyStats[]> => {
    return apiClient.get<FamilyStats[]>('/species/families/stats', params)
  },

  /**
   * Get species by family
   */
  getByFamily: async (familyName: string, params?: {
    station_ids?: string
  }): Promise<SpeciesResponse[]> => {
    return apiClient.get<SpeciesResponse[]>(`/species/by-family/${encodeURIComponent(familyName)}`, params)
  },

  /**
   * Get hourly detection pattern for a species
   */
  getHourlyPattern: async (speciesId: number): Promise<HourlyPattern[]> => {
    return apiClient.get<HourlyPattern[]>(`/species/${speciesId}/hourly-pattern`)
  },

  /**
   * Get monthly detection pattern for a species
   */
  getMonthlyPattern: async (speciesId: number): Promise<MonthlyPattern[]> => {
    return apiClient.get<MonthlyPattern[]>(`/species/${speciesId}/monthly-pattern`)
  },

  /**
   * Get detection timeline for a species
   */
  getTimeline: async (speciesId: number, months?: number): Promise<TimelinePoint[]> => {
    const params = months ? { months } : undefined
    return apiClient.get<TimelinePoint[]>(`/species/${speciesId}/timeline`, params)
  },

  /**
   * Get station distribution for a species
   */
  getStationDistribution: async (speciesId: number): Promise<StationDistribution[]> => {
    return apiClient.get<StationDistribution[]>(`/species/${speciesId}/station-distribution`)
  },

  /**
   * Get confidence by station for a species
   */
  getConfidenceByStation: async (speciesId: number): Promise<ConfidenceByStation[]> => {
    return apiClient.get<ConfidenceByStation[]>(`/species/${speciesId}/confidence-by-station`)
  },

  /**
   * Refresh cached statistics for all species
   */
  refreshStats: async (): Promise<{ success: boolean; species_updated: number }> => {
    return apiClient.post<{ success: boolean; species_updated: number }>('/species/refresh-stats')
  },

  /**
   * Get iNaturalist taxon ID for a species (fetches and caches if not available)
   */
  getInatTaxonId: async (scientificName: string): Promise<{
    scientific_name: string
    taxon_id: number | null
    url: string
    cached: boolean
  }> => {
    return apiClient.get(`/species/inat-taxon/${encodeURIComponent(scientificName)}`)
  },
}

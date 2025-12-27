/**
 * Species API Service
 * API methods for species-related endpoints.
 *
 * Version: 1.0.0
 */

import { apiClient } from './client'
import type {
  SpeciesResponse,
  SpeciesDiversityTrend,
  SpeciesDiscoveryCurve,
  NewSpeciesThisWeek,
  FamilyStats,
} from '../types/api'

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
}

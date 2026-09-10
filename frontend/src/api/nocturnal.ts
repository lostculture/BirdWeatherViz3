/**
 * Nocturnal API Service
 * API methods for the Nocturnal page (bats, owls, nightjars and allies).
 *
 * Version: 1.0.0
 */

import type { DawnChorusPoint, DuskChorusPoint } from './analytics'
import { apiClient } from './client'

export type NocturnalGroupKey = 'bats' | 'owls' | 'nightjars'

export interface NocturnalGroup {
  group: NocturnalGroupKey
  label: string
  description: string
  species_count: number
  detection_count: number
}

export interface NocturnalSpecies {
  species_id: number
  common_name: string
  english_name?: string | null
  scientific_name: string
  family: string | null
  group: NocturnalGroupKey | null
  group_label: string
  detection_count: number
  active_nights: number
  first_seen: string | null
  last_seen: string | null
}

export interface NocturnalSummary {
  /** False when no species carries order/family taxonomy at all. */
  taxonomy_available: boolean
  groups: NocturnalGroup[]
  species: NocturnalSpecies[]
}

export interface NocturnalGroupsResponse {
  taxonomy_available: boolean
  groups: Array<Omit<NocturnalGroup, 'detection_count'>>
}

export interface NocturnalHourPoint {
  species_id: number
  common_name: string
  group: NocturnalGroupKey | null
  hour: number
  detection_count: number
}

export interface NocturnalNightPoint {
  date: string
  group: string
  detection_count: number
  species_count: number
}

interface BaseParams {
  groups?: string
  station_ids?: string
  months?: number
  min_confidence?: number
}

export const nocturnalApi = {
  /**
   * List the nocturnal groups and how many catalogued species fall in each.
   */
  getGroups: async (): Promise<NocturnalGroupsResponse> => {
    return apiClient.get<NocturnalGroupsResponse>('/nocturnal/groups')
  },

  /**
   * Per-group totals plus the species table.
   */
  getSummary: async (params?: BaseParams): Promise<NocturnalSummary> => {
    return apiClient.get<NocturnalSummary>('/nocturnal/summary', params)
  },

  /**
   * Hour-of-day activity per nocturnal species.
   */
  getHourly: async (params?: BaseParams): Promise<NocturnalHourPoint[]> => {
    return apiClient.get<NocturnalHourPoint[]>('/nocturnal/hourly', params)
  },

  /**
   * Detections per night per group.
   */
  getNightly: async (params?: BaseParams): Promise<NocturnalNightPoint[]> => {
    return apiClient.get<NocturnalNightPoint[]>('/nocturnal/nightly', params)
  },

  /**
   * Sunset-relative activity, nocturnal species only.
   */
  getDuskChorus: async (
    params?: BaseParams & { window_minutes?: number },
  ): Promise<DuskChorusPoint[]> => {
    return apiClient.get<DuskChorusPoint[]>('/nocturnal/dusk-chorus', params)
  },

  /**
   * Sunrise-relative activity, nocturnal species only.
   */
  getDawnChorus: async (
    params?: BaseParams & { window_minutes?: number },
  ): Promise<DawnChorusPoint[]> => {
    return apiClient.get<DawnChorusPoint[]>('/nocturnal/dawn-chorus', params)
  },
}

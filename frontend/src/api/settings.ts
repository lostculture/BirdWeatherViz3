/**
 * Settings API
 * API functions for application settings and configuration.
 *
 * Version: 1.0.0
 */

import { apiClient } from './client'

export interface Setting {
  key: string
  value: string | null
  data_type: string | null
  description: string | null
}

export interface TaxonomyStats {
  species_with_codes: number
  species_with_families: number
  total_species: number
  coverage_percent: number
  unique_families: number
  ebird_entries: number
  last_updated: string | null
}

export interface TaxonomyUploadResponse {
  success: boolean
  species_updated: number
  species_created: number
  families_added: number
  total_ebird_species: number
  message: string
}

export interface DetectionUploadResponse {
  success: boolean
  detections_added: number
  detections_skipped: number
  species_created: number
  stations_matched: number
  message: string
}

export const settingsApi = {
  /**
   * Get all settings
   */
  getAll: async (): Promise<Setting[]> => {
    return apiClient.get<Setting[]>('/settings/')
  },

  /**
   * Get a specific setting
   */
  get: async (key: string): Promise<Setting> => {
    return apiClient.get<Setting>(`/settings/${key}`)
  },

  /**
   * Update or create a setting
   */
  update: async (key: string, value: string, dataType?: string, description?: string): Promise<Setting> => {
    return apiClient.put<Setting>(`/settings/${key}`, {
      value,
      data_type: dataType || 'str',
      description,
    })
  },

  /**
   * Delete a setting
   */
  delete: async (key: string): Promise<{ success: boolean; message: string }> => {
    return apiClient.delete(`/settings/${key}`)
  },

  /**
   * Upload eBird taxonomy CSV
   */
  uploadTaxonomy: async (file: File): Promise<TaxonomyUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)

    // Use axios for file upload to properly handle proxy
    const axios = (await import('axios')).default
    const response = await axios.post<TaxonomyUploadResponse>(
      '/api/v1/settings/ebird-taxonomy',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 2 minute timeout for large files
      }
    )

    return response.data
  },

  /**
   * Get eBird taxonomy statistics
   */
  getTaxonomyStats: async (): Promise<TaxonomyStats> => {
    return apiClient.get<TaxonomyStats>('/settings/ebird-taxonomy/stats')
  },

  /**
   * Upload detection CSV file
   */
  uploadDetections: async (file: File): Promise<DetectionUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)

    const axios = (await import('axios')).default
    const response = await axios.post<DetectionUploadResponse>(
      '/api/v1/settings/detections/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 600000, // 10 minute timeout for large files
      }
    )

    return response.data
  },
}

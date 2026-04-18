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

export interface DetectionUploadProgressEvent {
  type: 'start' | 'progress' | 'complete' | 'error'
  total_lines?: number
  lines_processed?: number
  detections_added?: number
  detections_skipped?: number
  species_created?: number
  stations_matched?: number
  message?: string
  success?: boolean
}

// Bird Information Sources Configuration
export interface BirdInfoSource {
  id: string
  name: string
  region: string
  description: string
}

export const BIRD_INFO_SOURCES: Record<string, BirdInfoSource> = {
  ebird: {
    id: 'ebird',
    name: 'eBird',
    region: 'Global',
    description: 'Cornell Lab - Global bird observations and data',
  },
  allaboutbirds: {
    id: 'allaboutbirds',
    name: 'All About Birds',
    region: 'North America',
    description: 'Cornell Lab - Bird guide for North America',
  },
  audubon: {
    id: 'audubon',
    name: 'Audubon',
    region: 'North America',
    description: 'Audubon Society field guide',
  },
  rspb: {
    id: 'rspb',
    name: 'RSPB',
    region: 'United Kingdom',
    description: 'Royal Society for the Protection of Birds (UK)',
  },
  bto: {
    id: 'bto',
    name: 'BTO BirdFacts',
    region: 'United Kingdom',
    description: 'British Trust for Ornithology',
  },
  xenocanto: {
    id: 'xenocanto',
    name: 'Xeno-canto',
    region: 'Global',
    description: 'Bird sound recordings from around the world',
  },
  wikipedia: {
    id: 'wikipedia',
    name: 'Wikipedia',
    region: 'Global',
    description: 'Wikipedia article',
  },
  inaturalist: {
    id: 'inaturalist',
    name: 'iNat',
    region: 'Global',
    description: 'iNaturalist - Community-driven species observations',
  },
}

export const BIRD_SOURCE_REGIONS: Record<string, string[]> = {
  'North America': ['ebird', 'allaboutbirds', 'audubon'],
  'United Kingdom': ['rspb', 'bto'],
  Global: ['xenocanto', 'wikipedia', 'inaturalist'],
}

export const DEFAULT_BIRD_SOURCES = ['ebird', 'wikipedia']

export const settingsApi = {
  /**
   * Get auto-update-on-start preference (public, no auth required)
   */
  getAutoUpdateOnStart: async (): Promise<boolean> => {
    const resp = await apiClient.get<{ enabled: boolean }>('/settings/auto-update-on-start')
    return resp.enabled
  },

  /**
   * Set auto-update-on-start preference (requires auth)
   */
  setAutoUpdateOnStart: async (enabled: boolean): Promise<{ enabled: boolean }> => {
    return apiClient.put<{ enabled: boolean }>('/settings/auto-update-on-start', {
      value: String(enabled),
      data_type: 'bool',
    })
  },

  /**
   * Get app info (mode, version, data_dir)
   */
  getAppInfo: async (): Promise<{ mode: string; version: string; data_dir: string }> => {
    return apiClient.get<{ mode: string; version: string; data_dir: string }>('/app-info')
  },

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
  update: async (
    key: string,
    value: string,
    dataType?: string,
    description?: string,
  ): Promise<Setting> => {
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

    // Use axios for file upload with auth token
    const axios = (await import('axios')).default
    const token = localStorage.getItem('auth_token')
    const response = await axios.post<TaxonomyUploadResponse>(
      '/api/v1/settings/ebird-taxonomy',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        timeout: 180000, // 3 minute timeout for large files
      },
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
    const token = localStorage.getItem('auth_token')
    const response = await axios.post<DetectionUploadResponse>(
      '/api/v1/settings/detections/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        timeout: 600000, // 10 minute timeout for large files
      },
    )

    return response.data
  },

  /**
   * Upload detection CSV with streaming progress via NDJSON.
   */
  uploadDetectionsStream: async function* (
    file: File,
  ): AsyncGenerator<DetectionUploadProgressEvent, void, unknown> {
    const formData = new FormData()
    formData.append('file', file)

    const token = localStorage.getItem('auth_token')
    const response = await fetch('/api/v1/settings/detections/upload-stream', {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: formData,
    })

    if (!response.ok) {
      const text = await response.text()
      let detail = text
      try {
        detail = JSON.parse(text).detail || text
      } catch {
        // use raw text
      }
      throw new Error(detail)
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
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.trim()) {
          const event = JSON.parse(line) as DetectionUploadProgressEvent
          yield event
        }
      }
    }

    if (buffer.trim()) {
      const event = JSON.parse(buffer) as DetectionUploadProgressEvent
      yield event
    }
  },

  /**
   * Get bird info sources setting
   */
  getBirdInfoSources: async (): Promise<string[]> => {
    try {
      const setting = await apiClient.get<Setting>('/settings/bird_info_sources')
      if (setting.value) {
        return setting.value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s)
      }
    } catch (err) {
      // Setting doesn't exist yet, use defaults
    }
    return DEFAULT_BIRD_SOURCES
  },

  /**
   * Set bird info sources
   */
  setBirdInfoSources: async (sources: string[]): Promise<Setting> => {
    return apiClient.put<Setting>('/settings/bird_info_sources', {
      value: sources.join(','),
      data_type: 'str',
      description: 'Enabled bird information link sources',
    })
  },

  /**
   * Get temperature unit setting
   */
  getTemperatureUnit: async (): Promise<'imperial' | 'metric'> => {
    try {
      const setting = await apiClient.get<Setting>('/settings/temperature_unit')
      if (setting.value === 'metric') return 'metric'
    } catch (err) {
      // Setting doesn't exist yet, use default
    }
    return 'imperial'
  },

  /**
   * Set temperature unit
   */
  setTemperatureUnit: async (unit: 'imperial' | 'metric'): Promise<Setting> => {
    return apiClient.put<Setting>('/settings/temperature_unit', {
      value: unit,
      data_type: 'str',
      description: 'Temperature display unit (imperial=°F, metric=°C)',
    })
  },

  /**
   * Get wind speed unit setting
   */
  getWindSpeedUnit: async (): Promise<'imperial' | 'metric'> => {
    try {
      const setting = await apiClient.get<Setting>('/settings/wind_speed_unit')
      if (setting.value === 'metric') return 'metric'
    } catch (err) {
      // Setting doesn't exist yet, use default
    }
    return 'imperial'
  },

  /**
   * Set wind speed unit
   */
  setWindSpeedUnit: async (unit: 'imperial' | 'metric'): Promise<Setting> => {
    return apiClient.put<Setting>('/settings/wind_speed_unit', {
      value: unit,
      data_type: 'str',
      description: 'Wind speed display unit (imperial=mph, metric=km/h)',
    })
  },
}

/**
 * Generate bird information links for a species.
 */
export function generateBirdLinks(
  commonName: string,
  scientificName: string,
  ebirdCode: string | null | undefined,
  enabledSources: string[],
  inatTaxonId?: number | null,
): Array<{ name: string; url: string; source_id: string }> {
  const links: Array<{ name: string; url: string; source_id: string }> = []

  // Prepare name variations
  const commonNameUnderscore = commonName.replace(/ /g, '_')
  const commonNameHyphenLower = commonName.toLowerCase().replace(/ /g, '-').replace(/'/g, '')
  const scientificNameHyphen = scientificName.replace(/ /g, '-')
  const scientificNameHyphenLower = scientificName.toLowerCase().replace(/ /g, '-')
  const scientificNamePlus = encodeURIComponent(scientificName)

  // Generate iNat URL - use direct link if we have taxon ID
  const inatUrl = inatTaxonId
    ? `https://www.inaturalist.org/taxa/${inatTaxonId}-${scientificNameHyphen}`
    : `https://www.inaturalist.org/taxa/search?q=${scientificNamePlus}`

  const urlPatterns: Record<string, { pattern: string; requires: string }> = {
    ebird: { pattern: `https://ebird.org/species/${ebirdCode || ''}`, requires: 'ebird_code' },
    allaboutbirds: {
      pattern: `https://www.allaboutbirds.org/guide/${commonNameUnderscore}/overview`,
      requires: 'common_name',
    },
    audubon: {
      pattern: `https://www.audubon.org/field-guide/bird/${commonNameHyphenLower}`,
      requires: 'common_name',
    },
    rspb: {
      pattern: `https://www.rspb.org.uk/birds-and-wildlife/${commonNameHyphenLower}`,
      requires: 'common_name',
    },
    bto: {
      pattern: `https://www.bto.org/understanding-birds/birdfacts/${commonNameHyphenLower}`,
      requires: 'common_name',
    },
    xenocanto: {
      pattern: `https://xeno-canto.org/species/${scientificNameHyphenLower}`,
      requires: 'scientific_name',
    },
    wikipedia: {
      pattern: `https://en.wikipedia.org/wiki/${commonNameUnderscore}`,
      requires: 'common_name',
    },
    inaturalist: { pattern: inatUrl, requires: 'scientific_name' },
  }

  for (const sourceId of enabledSources) {
    const source = BIRD_INFO_SOURCES[sourceId]
    const urlInfo = urlPatterns[sourceId]
    if (!source || !urlInfo) continue

    // Skip eBird if no code
    if (urlInfo.requires === 'ebird_code' && !ebirdCode) continue

    links.push({
      name: source.name,
      url: urlInfo.pattern,
      source_id: sourceId,
    })
  }

  return links
}

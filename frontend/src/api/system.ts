/**
 * System API
 * /system/info — running version, schema version, mode, platform.
 * /system/update-info — GitHub releases comparison for the update banner.
 */

import { apiClient } from './client'

export interface SystemInfo {
  version: string
  schema_version: string
  mode: string
  platform: string
  python_version: string
}

export interface UpdateInfo {
  current: string
  latest: string | null
  update_available: boolean
  release_url: string | null
  published_at: string | null
  body: string | null
  enabled: boolean
  error: string | null
}

export const systemApi = {
  getInfo: async (): Promise<SystemInfo> => apiClient.get<SystemInfo>('/system/info'),

  getUpdateInfo: async (refresh = false): Promise<UpdateInfo> =>
    apiClient.get<UpdateInfo>(`/system/update-info${refresh ? '?refresh=true' : ''}`),
}

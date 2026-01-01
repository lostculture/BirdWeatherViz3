/**
 * Weather API
 * API functions for weather data management.
 *
 * Version: 1.0.0
 */

import { apiClient } from './client'

export interface WeatherStats {
  total_weather_records: number
  first_date: string | null
  last_date: string | null
  detection_days: number
  weather_days: number
  missing_days: number
  weather_station: string | null
}

export interface WeatherStationSetting {
  station_id: number | null
  station_name: string | null
}

export interface WeatherSyncResponse {
  success: boolean
  days_fetched: number
  days_skipped: number
  days_failed: number
  message: string
}

export interface WeatherRecord {
  id: number
  station_id: number
  weather_date: string
  latitude: number
  longitude: number
  temp_max: number | null
  temp_min: number | null
  temp_avg: number | null
  humidity: number | null
  pressure: number | null
  wind_speed: number | null
  precipitation: number | null
  weather_description: string | null
  sunrise: string | null
  sunset: string | null
  day_length: string | null
}

export const weatherApi = {
  /**
   * Get weather statistics
   */
  getStats: async (): Promise<WeatherStats> => {
    return apiClient.get<WeatherStats>('/weather/stats')
  },

  /**
   * Get recent weather records
   */
  getRecent: async (limit: number = 7): Promise<WeatherRecord[]> => {
    return apiClient.get<WeatherRecord[]>(`/weather/?limit=${limit}`)
  },

  /**
   * Get weather for a specific date
   */
  getForDate: async (date: string): Promise<WeatherRecord | null> => {
    return apiClient.get<WeatherRecord | null>(`/weather/date/${date}`)
  },

  /**
   * Get current weather station setting
   */
  getStationSetting: async (): Promise<WeatherStationSetting> => {
    return apiClient.get<WeatherStationSetting>('/weather/station-setting')
  },

  /**
   * Set weather station
   */
  setStation: async (stationId: number): Promise<WeatherStationSetting> => {
    return apiClient.put<WeatherStationSetting>(`/weather/station-setting/${stationId}`, {})
  },

  /**
   * Sync weather for all detection days
   */
  sync: async (): Promise<WeatherSyncResponse> => {
    return apiClient.post<WeatherSyncResponse>('/weather/sync', {})
  },
}

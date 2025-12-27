/**
 * API Type Definitions
 * TypeScript types for API requests and responses.
 *
 * Version: 1.0.0
 */

// Detection Types
export interface DetectionResponse {
  id: number
  station_id: number
  species_id: number
  detection_id: number
  timestamp: string
  confidence: number
  latitude?: number
  longitude?: number
  detection_date: string
  detection_hour: number
  common_name: string
  scientific_name: string
  station_name: string
}

export interface DailyDetectionCount {
  detection_date: string
  station_id: number
  station_name: string
  detection_count: number
}

export interface HourlyDetectionPattern {
  hour: number
  detection_count: number
  avg_confidence: number
}

// Species Types
export interface SpeciesResponse {
  id: number
  species_id: string
  common_name: string
  scientific_name: string
  family?: string
  ebird_code?: string
  total_detections: number
  first_seen?: string
  last_seen?: string
}

export interface SpeciesDiversityTrend {
  detection_date: string
  unique_species_count: number
  seven_day_avg: number
}

export interface SpeciesDiscoveryCurve {
  detection_date: string
  cumulative_species: number
}

export interface NewSpeciesThisWeek {
  species_id: number
  common_name: string
  scientific_name: string
  first_detection_date: string
  detection_count: number
}

export interface FamilyStats {
  family: string
  species_count: number
  detection_count: number
  avg_confidence: number
}

// Station Types
export interface StationResponse {
  id: number
  station_id: string
  name: string
  latitude?: number
  longitude?: number
  active: boolean
  last_update?: string
  last_detection_id?: number
  masked_token?: string
}

export interface StationCreate {
  station_id: string
  name: string
  api_token: string
  latitude?: number
  longitude?: number
  active?: boolean
}

export interface StationUpdate {
  name?: string
  api_token?: string
  latitude?: number
  longitude?: number
  active?: boolean
}

export interface StationStats {
  station_id: number
  station_name: string
  total_detections: number
  unique_species: number
  days_active: number
  avg_confidence: number
  first_detection?: string
  last_detection?: string
}

// Common Types
export interface DatabaseStats {
  total_detections: number
  unique_species: number
  total_stations: number
  nighttime_percentage: number
  date_range_start?: string
  date_range_end?: string
}

export interface PlotlyData {
  data: any[]
  layout: any
}

// Filter Types
export interface DateRange {
  start_date?: string
  end_date?: string
}

export interface StationFilter {
  station_ids?: number[]
}

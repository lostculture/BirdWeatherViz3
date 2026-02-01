/**
 * API Module
 * Exports all API services.
 *
 * Version: 1.0.0
 */

export { apiClient } from './client'
export { authApi } from './auth'
export { analyticsApi } from './analytics'
export { detectionsApi } from './detections'
export { speciesApi } from './species'
export { stationsApi } from './stations'
export { settingsApi, BIRD_INFO_SOURCES, BIRD_SOURCE_REGIONS, DEFAULT_BIRD_SOURCES, generateBirdLinks } from './settings'
export { weatherApi } from './weather'

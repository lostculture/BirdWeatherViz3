/**
 * Global Filter Context
 * Provides date range and station filters across all pages.
 *
 * Version: 1.1.0
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { stationsApi } from '../api'
import type { StationResponse } from '../types/api'

interface FilterState {
  startDate: string | null
  endDate: string | null
  stationIds: number[]
  stations: StationResponse[]
  loading: boolean
  /** Set when the station list could not be fetched, so the bar can say so. */
  stationsError: string | null
}

interface FilterContextType extends FilterState {
  setDateRange: (start: string | null, end: string | null) => void
  setStationIds: (ids: number[]) => void
  clearFilters: () => void
  getStationIdsParam: () => string | undefined
}

const FilterContext = createContext<FilterContextType | undefined>(undefined)

export const FilterProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [startDate, setStartDate] = useState<string | null>(null)
  const [endDate, setEndDate] = useState<string | null>(null)
  const [stationIds, setStationIdsState] = useState<number[]>([])
  const [stations, setStations] = useState<StationResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [stationsError, setStationsError] = useState<string | null>(null)

  // Load stations on mount
  useEffect(() => {
    loadStations()
  }, [])

  const loadStations = async () => {
    try {
      // Every station, not just the active ones. A station missing from this
      // list cannot be selected anywhere in the app, and issue #22 was exactly
      // that: stations with no `active` flag disappeared from the filter bar.
      const stationList = await stationsApi.getAll()
      setStations(stationList)
      setStationsError(null)
    } catch (err) {
      console.error('Failed to load stations for filter:', err)
      setStationsError('Could not load stations')
    } finally {
      setLoading(false)
    }
  }

  const setDateRange = (start: string | null, end: string | null) => {
    setStartDate(start)
    setEndDate(end)
  }

  const setStationIds = (ids: number[]) => {
    setStationIdsState(ids)
  }

  const clearFilters = () => {
    setStartDate(null)
    setEndDate(null)
    setStationIdsState([])
  }

  // Helper to get station IDs as comma-separated string for API calls
  const getStationIdsParam = (): string | undefined => {
    if (stationIds.length === 0 || stationIds.length === stations.length) {
      return undefined // All stations or none selected = no filter
    }
    return stationIds.join(',')
  }

  return (
    <FilterContext.Provider
      value={{
        startDate,
        endDate,
        stationIds,
        stations,
        loading,
        stationsError,
        setDateRange,
        setStationIds,
        clearFilters,
        getStationIdsParam,
      }}
    >
      {children}
    </FilterContext.Provider>
  )
}

export const useFilters = (): FilterContextType => {
  const context = useContext(FilterContext)
  if (!context) {
    throw new Error('useFilters must be used within a FilterProvider')
  }
  return context
}

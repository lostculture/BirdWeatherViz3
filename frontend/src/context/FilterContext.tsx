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

  // Load stations on mount
  useEffect(() => {
    loadStations()
  }, [])

  const loadStations = async () => {
    try {
      const stationList = await stationsApi.getAll({ active_only: true })
      setStations(stationList)
    } catch (err) {
      console.error('Failed to load stations for filter:', err)
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

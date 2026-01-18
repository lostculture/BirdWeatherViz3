/**
 * Global Filter Bar
 * Displays date range and station selection filters.
 *
 * Version: 1.1.0
 */

import React from 'react'
import { useFilters } from '../../context/FilterContext'

const FilterBar: React.FC = () => {
  const {
    startDate,
    endDate,
    stationIds,
    stations,
    loading,
    setDateRange,
    setStationIds,
    clearFilters,
  } = useFilters()

  const hasActiveFilters = startDate || endDate || stationIds.length > 0

  const handleStationToggle = (stationId: number) => {
    if (stationIds.includes(stationId)) {
      setStationIds(stationIds.filter((id) => id !== stationId))
    } else {
      setStationIds([...stationIds, stationId])
    }
  }

  const handleSelectAllStations = () => {
    if (stationIds.length === stations.length) {
      setStationIds([])
    } else {
      setStationIds(stations.map((s) => s.id))
    }
  }

  if (loading) {
    return null
  }

  return (
    <div className="bg-white border-b shadow-sm">
      <div className="container mx-auto px-4 py-3">
        <div className="flex flex-wrap items-center gap-4">
          {/* Date Range Filters */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-600">From:</label>
            <input
              type="date"
              value={startDate || ''}
              onChange={(e) => setDateRange(e.target.value || null, endDate)}
              className="px-2 py-1 text-sm border rounded focus:ring-2 focus:ring-indigo-brilliant focus:border-indigo-brilliant"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-600">To:</label>
            <input
              type="date"
              value={endDate || ''}
              onChange={(e) => setDateRange(startDate, e.target.value || null)}
              className="px-2 py-1 text-sm border rounded focus:ring-2 focus:ring-indigo-brilliant focus:border-indigo-brilliant"
            />
          </div>

          {/* Separator */}
          <div className="h-6 w-px bg-gray-300" />

          {/* Station Filters */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-600">Stations:</label>
            <div className="flex flex-wrap gap-1">
              {stations.map((station) => (
                <button
                  key={station.id}
                  onClick={() => handleStationToggle(station.id)}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    stationIds.length === 0 || stationIds.includes(station.id)
                      ? 'bg-indigo-brilliant text-white'
                      : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                  }`}
                >
                  {station.name}
                </button>
              ))}
              {stations.length > 1 && (
                <button
                  onClick={handleSelectAllStations}
                  className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200 ml-1"
                >
                  {stationIds.length === stations.length ? 'Deselect All' : 'Select All'}
                </button>
              )}
            </div>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <>
              <div className="h-6 w-px bg-gray-300" />
              <button
                onClick={clearFilters}
                className="px-3 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
              >
                Clear Filters
              </button>
            </>
          )}

          {/* Active Filter Indicator */}
          {hasActiveFilters && (
            <span className="text-xs text-gray-500 italic">
              Filters active
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default FilterBar

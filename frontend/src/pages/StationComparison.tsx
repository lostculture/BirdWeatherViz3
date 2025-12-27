/**
 * Station Comparison Page
 * Compare statistics across multiple stations.
 *
 * Version: 1.0.0
 */

import React, { useEffect, useState } from 'react'
import { stationsApi } from '../api'
import type { StationStats } from '../types/api'

const StationComparison: React.FC = () => {
  const [stations, setStations] = useState<StationStats[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await stationsApi.getComparison()
      setStations(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-red-600">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Station Comparison</h1>
        <p className="text-muted-foreground mt-2">
          Compare statistics and data across all stations
        </p>
      </div>

      {/* Station Comparison Table */}
      {stations.length > 0 ? (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Station Statistics</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Station Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Total Detections
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Unique Species
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Days Active
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Avg Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    First Detection
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Last Detection
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {stations.map((station) => (
                  <tr key={station.station_id}>
                    <td className="px-6 py-4 whitespace-nowrap font-medium">
                      {station.station_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {station.total_detections.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {station.unique_species}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {station.days_active}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {station.avg_confidence.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {station.first_detection
                        ? new Date(station.first_detection).toLocaleDateString()
                        : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {station.last_detection
                        ? new Date(station.last_detection).toLocaleDateString()
                        : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center text-muted-foreground py-8">
            No station data available
          </div>
        </div>
      )}
    </div>
  )
}

export default StationComparison

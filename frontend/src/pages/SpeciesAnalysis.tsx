/**
 * Species Analysis Page
 * Displays species diversity trends and discovery curves.
 *
 * Version: 1.1.0
 */

import React, { useEffect, useState } from 'react'
import { speciesApi } from '../api'
import { LineChart } from '../components/charts'
import { useFilters } from '../context/FilterContext'
import type { SpeciesDiversityTrend, SpeciesDiscoveryCurve } from '../types/api'
import type { Data } from 'plotly.js'

const SpeciesAnalysis: React.FC = () => {
  const { startDate, endDate, getStationIdsParam } = useFilters()
  const [diversityData, setDiversityData] = useState<SpeciesDiversityTrend[]>([])
  const [discoveryData, setDiscoveryData] = useState<SpeciesDiscoveryCurve[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Reload when filters change
  useEffect(() => {
    loadData()
  }, [startDate, endDate, getStationIdsParam()])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Build filter params
      const filterParams = {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        station_ids: getStationIdsParam(),
      }

      const [diversity, discovery] = await Promise.all([
        speciesApi.getDiversityTrend(filterParams),
        speciesApi.getDiscoveryCurve(filterParams),
      ])

      setDiversityData(diversity)
      setDiscoveryData(discovery)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const prepareDiversityChart = (): Data[] => {
    return [
      {
        x: diversityData.map((d) => d.detection_date),
        y: diversityData.map((d) => d.unique_species_count),
        name: 'Daily Unique Species',
        type: 'scatter' as const,
        mode: 'lines' as const,
        line: { color: '#3b82f6', width: 1 },
      },
      {
        x: diversityData.map((d) => d.detection_date),
        y: diversityData.map((d) => d.seven_day_avg),
        name: '7-Day Average',
        type: 'scatter' as const,
        mode: 'lines' as const,
        line: { color: '#ef4444', width: 2 },
      },
    ]
  }

  const prepareDiscoveryChart = (): Data[] => {
    return [
      {
        x: discoveryData.map((d) => d.discovery_date),
        y: discoveryData.map((d) => d.cumulative_species_count),
        name: 'Cumulative Species',
        type: 'scatter' as const,
        mode: 'lines' as const,
        fill: 'tozeroy' as const,
        line: { color: '#10b981', width: 2 },
      },
    ]
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
        <h1 className="text-3xl font-bold">Species Analysis</h1>
        <p className="text-muted-foreground mt-2">
          Diversity trends and species discovery over time
        </p>
      </div>

      {/* Species Diversity Trend */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Species Diversity Trend</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Daily count of unique species detected with 7-day moving average
        </p>
        {diversityData.length > 0 ? (
          <LineChart
            data={prepareDiversityChart()}
            layout={{
              title: { text: 'Daily Unique Species Count' },
              xaxis: { title: { text: 'Date' } },
              yaxis: { title: { text: 'Number of Unique Species' } },
              height: 450,
            }}
          />
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No diversity data available
          </div>
        )}
      </div>

      {/* Discovery Curve */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Species Discovery Curve</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Cumulative count of unique species discovered over time
        </p>
        {discoveryData.length > 0 ? (
          <LineChart
            data={prepareDiscoveryChart()}
            layout={{
              title: { text: 'Cumulative Species Discovery' },
              xaxis: { title: { text: 'Date' } },
              yaxis: { title: { text: 'Total Unique Species' } },
              height: 450,
            }}
          />
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No discovery data available
          </div>
        )}
      </div>

      {/* Summary Stats */}
      {discoveryData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-muted-foreground">Total Species</div>
            <div className="text-3xl font-bold mt-2">
              {discoveryData[discoveryData.length - 1]?.cumulative_species_count || 0}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-muted-foreground">First Detection</div>
            <div className="text-xl font-bold mt-2">
              {discoveryData[0]
                ? new Date(discoveryData[0].discovery_date).toLocaleDateString()
                : 'N/A'}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-muted-foreground">Latest Detection</div>
            <div className="text-xl font-bold mt-2">
              {discoveryData[discoveryData.length - 1]
                ? new Date(
                    discoveryData[discoveryData.length - 1].discovery_date
                  ).toLocaleDateString()
                : 'N/A'}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SpeciesAnalysis

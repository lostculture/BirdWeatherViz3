/**
 * Daily Detections Page
 * Displays daily detection trends and new species gallery.
 *
 * Version: 1.0.0
 */

import React, { useEffect, useState } from 'react'
import { detectionsApi, speciesApi, weatherApi } from '../api'
import { LineChart } from '../components/charts'
import type { DailyDetectionCount, NewSpeciesThisWeek, DatabaseStats } from '../types/api'
import type { WeatherRecord } from '../api/weather'
import type { Data } from 'plotly.js'

const DailyDetections: React.FC = () => {
  const [dailyData, setDailyData] = useState<DailyDetectionCount[]>([])
  const [newSpecies, setNewSpecies] = useState<NewSpeciesThisWeek[]>([])
  const [stats, setStats] = useState<DatabaseStats | null>(null)
  const [weather, setWeather] = useState<WeatherRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
    syncWeatherInBackground()
  }, [])

  const syncWeatherInBackground = async () => {
    try {
      // Check if we have a weather station configured
      const stationSetting = await weatherApi.getStationSetting()
      if (stationSetting.station_id) {
        // Check if we need to sync (only if there are missing days)
        const stats = await weatherApi.getStats()
        if (stats.missing_days > 0) {
          // Sync weather silently in background
          await weatherApi.sync()
          // Reload weather after sync
          loadWeather()
        }
      }
    } catch (err) {
      // Silent fail for background sync
      console.log('Background weather sync skipped:', err)
    }
  }

  const loadWeather = async () => {
    try {
      const records = await weatherApi.getRecent(1)
      if (records.length > 0) {
        setWeather(records[0])
      }
    } catch (err) {
      console.log('Failed to load weather:', err)
    }
  }

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [daily, species, statsData] = await Promise.all([
        detectionsApi.getDailyCounts(),
        speciesApi.getThisWeek(),
        detectionsApi.getStats(),
      ])

      setDailyData(daily)
      setNewSpecies(species)
      setStats(statsData)

      // Also load weather
      loadWeather()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  // Prepare chart data
  const prepareChartData = (): Data[] => {
    // Group by station
    const stationGroups: Record<string, DailyDetectionCount[]> = {}
    dailyData.forEach((item) => {
      if (!stationGroups[item.station_name]) {
        stationGroups[item.station_name] = []
      }
      stationGroups[item.station_name].push(item)
    })

    // Create traces for each station
    return Object.entries(stationGroups).map(([stationName, data]) => ({
      x: data.map((d) => d.detection_date),
      y: data.map((d) => d.detection_count),
      name: stationName,
      type: 'scatter' as const,
      mode: 'lines+markers' as const,
    }))
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
        <h1 className="text-3xl font-bold">Daily Detections</h1>
        <p className="text-muted-foreground mt-2">
          Bird detection trends and new species this week
        </p>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-muted-foreground">Total Detections</div>
            <div className="text-3xl font-bold mt-2">{stats.total_detections.toLocaleString()}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-muted-foreground">Unique Species</div>
            <div className="text-3xl font-bold mt-2">{stats.unique_species}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-muted-foreground">Active Stations</div>
            <div className="text-3xl font-bold mt-2">{stats.total_stations}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-muted-foreground">Nighttime %</div>
            <div className="text-3xl font-bold mt-2">
              {stats.nighttime_percentage.toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      {/* Weather Card */}
      {weather && (
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg shadow p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm opacity-80">
                Weather for {new Date(weather.weather_date).toLocaleDateString()}
              </div>
              <div className="text-2xl font-bold mt-1">
                {weather.weather_description || 'N/A'}
              </div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold">
                {weather.temp_avg !== null ? `${Math.round(weather.temp_avg)}°F` : '--'}
              </div>
              <div className="text-sm opacity-80">
                {weather.temp_min !== null && weather.temp_max !== null
                  ? `${Math.round(weather.temp_min)}° / ${Math.round(weather.temp_max)}°`
                  : ''
                }
              </div>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-white/20">
            <div className="text-center">
              <div className="text-sm opacity-80">Sunrise</div>
              <div className="font-semibold">{weather.sunrise?.substring(0, 5) || '--'}</div>
            </div>
            <div className="text-center">
              <div className="text-sm opacity-80">Sunset</div>
              <div className="font-semibold">{weather.sunset?.substring(0, 5) || '--'}</div>
            </div>
            <div className="text-center">
              <div className="text-sm opacity-80">Humidity</div>
              <div className="font-semibold">{weather.humidity !== null ? `${Math.round(weather.humidity)}%` : '--'}</div>
            </div>
            <div className="text-center">
              <div className="text-sm opacity-80">Wind</div>
              <div className="font-semibold">{weather.wind_speed !== null ? `${Math.round(weather.wind_speed)} mph` : '--'}</div>
            </div>
          </div>
        </div>
      )}

      {/* Daily Detections Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Daily Detection Trends</h2>
        {dailyData.length > 0 ? (
          <LineChart
            data={prepareChartData()}
            layout={{
              title: { text: 'Daily Detections by Station' },
              xaxis: { title: { text: 'Date' } },
              yaxis: { title: { text: 'Number of Detections' } },
              height: 400,
            }}
          />
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No detection data available
          </div>
        )}
      </div>

      {/* New Species This Week */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">New Species This Week</h2>
        {newSpecies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {newSpecies.map((species) => (
              <div
                key={species.species_id}
                className="border rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="font-semibold text-lg">{species.common_name}</div>
                <div className="text-sm text-muted-foreground italic">
                  {species.scientific_name}
                </div>
                <div className="mt-2 text-sm">
                  <span className="text-muted-foreground">First seen: </span>
                  {new Date(species.first_detection_date).toLocaleDateString()}
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">Detections: </span>
                  {species.detection_count}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No new species this week
          </div>
        )}
      </div>
    </div>
  )
}

export default DailyDetections

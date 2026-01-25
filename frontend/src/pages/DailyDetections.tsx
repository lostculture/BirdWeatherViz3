/**
 * Daily Detections Page
 * Displays daily detection trends and new species gallery.
 *
 * Version: 1.1.0
 */

import React, { useEffect, useState } from 'react'
import { detectionsApi, speciesApi, weatherApi, settingsApi, generateBirdLinks, DEFAULT_BIRD_SOURCES } from '../api'
import { LineChart } from '../components/charts'
import { useFilters } from '../context/FilterContext'
import type { DailyDetectionCount, NewSpeciesThisWeek, DatabaseStats } from '../types/api'
import type { WeatherRecord } from '../api/weather'
import type { Data } from 'plotly.js'

// Helper to generate All About Birds URL from common name
const getAllAboutBirdsUrl = (commonName: string): string => {
  const slug = commonName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/_+$/, '')
  return `https://www.allaboutbirds.org/guide/${slug}`
}

// Helper to get bird image URL from our API
const getBirdImageUrl = (scientificName: string, commonName?: string): string => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  let url = `${baseUrl}/images/bird/${encodeURIComponent(scientificName)}`
  if (commonName) {
    url += `?common_name=${encodeURIComponent(commonName)}`
  }
  return url
}

// Species card with image component
const SpeciesCard: React.FC<{ species: NewSpeciesThisWeek }> = ({ species }) => {
  const [imageError, setImageError] = useState(false)
  const imageUrl = getBirdImageUrl(species.scientific_name, species.common_name)

  // Generate eBird URL using species code
  const getEbirdUrl = (): string => {
    if (species.ebird_code) {
      return `https://ebird.org/species/${species.ebird_code}`
    }
    // Fallback if no ebird_code (shouldn't happen for properly imported species)
    return `https://ebird.org/species/${species.common_name.toLowerCase().replace(/[^a-z0-9]+/g, '')}`
  }

  return (
    <div className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow bg-white">
      {/* Bird Image */}
      <div className="h-32 bg-gray-100 relative">
        {!imageError ? (
          <img
            src={imageUrl}
            alt={species.common_name}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-4xl">🐦</span>
          </div>
        )}
      </div>
      <div className="p-4">
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
        <div className="mt-3 flex flex-wrap gap-2">
          <a
            href={getAllAboutBirdsUrl(species.common_name)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-brilliant hover:underline text-xs font-medium"
          >
            All About Birds
          </a>
          <a
            href={getEbirdUrl()}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-brilliant hover:underline text-xs"
          >
            eBird
          </a>
          <a
            href={`https://en.wikipedia.org/wiki/${encodeURIComponent(species.scientific_name.replace(' ', '_'))}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-brilliant hover:underline text-xs"
          >
            Wikipedia
          </a>
        </div>
      </div>
    </div>
  )
}

const DailyDetections: React.FC = () => {
  const { startDate, endDate, getStationIdsParam } = useFilters()
  const [dailyData, setDailyData] = useState<DailyDetectionCount[]>([])
  const [newSpecies, setNewSpecies] = useState<NewSpeciesThisWeek[]>([])
  const [stats, setStats] = useState<DatabaseStats | null>(null)
  const [weather, setWeather] = useState<WeatherRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Display settings
  const [temperatureUnit, setTemperatureUnit] = useState<'imperial' | 'metric'>('imperial')
  const [windSpeedUnit, setWindSpeedUnit] = useState<'imperial' | 'metric'>('imperial')
  const [birdInfoSources, setBirdInfoSources] = useState<string[]>(DEFAULT_BIRD_SOURCES)

  // Temperature conversion helpers
  const toMetricTemp = (f: number) => Math.round((f - 32) * 5 / 9)
  const formatTemp = (f: number | null) => {
    if (f === null) return '--'
    return temperatureUnit === 'metric' ? `${toMetricTemp(f)}°C` : `${Math.round(f)}°F`
  }

  // Wind speed conversion helpers
  const toMetricWind = (mph: number) => Math.round(mph * 1.60934)
  const formatWind = (mph: number | null) => {
    if (mph === null) return '--'
    return windSpeedUnit === 'metric' ? `${toMetricWind(mph)} km/h` : `${Math.round(mph)} mph`
  }

  // Reload data when filters change
  useEffect(() => {
    loadData()
  }, [startDate, endDate, getStationIdsParam()])

  // Sync weather only on initial load
  useEffect(() => {
    syncWeatherInBackground()
    loadDisplaySettings()
  }, [])

  const loadDisplaySettings = async () => {
    try {
      const [tempUnit, windUnit, birdSources] = await Promise.all([
        settingsApi.getTemperatureUnit(),
        settingsApi.getWindSpeedUnit(),
        settingsApi.getBirdInfoSources()
      ])
      setTemperatureUnit(tempUnit)
      setWindSpeedUnit(windUnit)
      setBirdInfoSources(birdSources)
    } catch (err) {
      console.log('Failed to load display settings, using defaults')
    }
  }

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

      // Build filter params
      const filterParams = {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        station_ids: getStationIdsParam(),
      }

      const [daily, species, statsData] = await Promise.all([
        detectionsApi.getDailyCounts(filterParams),
        speciesApi.getThisWeek({ station_ids: filterParams.station_ids }),
        detectionsApi.getStats(filterParams),
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
          <div className="bg-white rounded-lg shadow p-6 border-t-4 border-indigo-brilliant">
            <div className="text-sm text-muted-foreground">Total Detections</div>
            <div className="text-3xl font-bold mt-2 text-indigo-dark">{stats.total_detections.toLocaleString()}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6 border-t-4 border-indigo-cerulean">
            <div className="text-sm text-muted-foreground">Unique Species</div>
            <div className="text-3xl font-bold mt-2 text-indigo-dark">{stats.unique_species}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6 border-t-4 border-indigo-deep">
            <div className="text-sm text-muted-foreground">Active Stations</div>
            <div className="text-3xl font-bold mt-2 text-indigo-dark">{stats.total_stations}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6 border-t-4 border-indigo-brown">
            <div className="text-sm text-muted-foreground">Nighttime %</div>
            <div className="text-3xl font-bold mt-2 text-indigo-dark">
              {stats.nighttime_percentage.toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      {/* Weather Card */}
      {weather && (
        <div className="bg-gradient-to-r from-indigo-deep to-indigo-brilliant rounded-lg shadow-lg p-6 text-white">
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
                {formatTemp(weather.temp_avg)}
              </div>
              <div className="text-sm opacity-80">
                {weather.temp_min !== null && weather.temp_max !== null
                  ? `${temperatureUnit === 'metric' ? toMetricTemp(weather.temp_min) : Math.round(weather.temp_min)}° / ${temperatureUnit === 'metric' ? toMetricTemp(weather.temp_max) : Math.round(weather.temp_max)}°`
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
              <div className="font-semibold">{formatWind(weather.wind_speed)}</div>
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
        <p className="text-sm text-muted-foreground mb-4">
          Species whose first-ever detection was this week
        </p>
        {newSpecies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {newSpecies.map((species) => {
              const birdLinks = generateBirdLinks(
                species.common_name,
                species.scientific_name,
                species.ebird_code,
                birdInfoSources
              )
              return (
                <div
                  key={species.species_id}
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="font-semibold text-lg">{species.common_name}</div>
                  <div className="text-sm text-muted-foreground italic">
                    {species.scientific_name}
                  </div>
                  <div className="mt-2 text-sm">
                    <span className="text-muted-foreground">First this week: </span>
                    {new Date(species.first_detection_date).toLocaleDateString()}
                  </div>
                  <div className="text-sm">
                    <span className="text-muted-foreground">Detections this week: </span>
                    {species.detection_count}
                  </div>
                  {birdLinks.length > 0 && (
                    <div className="mt-3 pt-2 border-t flex flex-wrap gap-2">
                      {birdLinks.map((link) => (
                        <a
                          key={link.source_id}
                          href={link.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 transition-colors"
                        >
                          {link.name}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
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

/**
 * Daily Detections Page
 * Displays daily detection trends and new species gallery.
 *
 * Version: 1.2.0
 */

import type { Data, Layout } from 'plotly.js'
import React, { useEffect, useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import { Link } from 'react-router-dom'
import {
  DEFAULT_BIRD_SOURCES,
  detectionsApi,
  generateBirdLinks,
  settingsApi,
  speciesApi,
  weatherApi,
} from '../api'
import type { WeatherRecord } from '../api/weather'
import { LineChart } from '../components/charts'
import { useFilters } from '../context/FilterContext'
import type {
  DailyDetectionCount,
  DatabaseStats,
  NewSpeciesThisWeek,
  OverdueSpecies,
  ReturningSpecies,
} from '../types/api'

// Threshold for switching to small multiples
const SPARKLINE_THRESHOLD = 3

// Indigo color palette for charts
const CHART_COLORS = [
  '#4169E1',
  '#1E3A8A',
  '#5B9BD5',
  '#8B7355',
  '#0F172A',
  '#6366F1',
  '#818CF8',
  '#4338CA',
  '#A5B4FC',
  '#7C3AED',
]

// Helper to get bird image URL from our API
const getBirdImageUrl = (scientificName: string, commonName?: string): string => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  let url = `${baseUrl}/images/bird/${encodeURIComponent(scientificName)}`
  if (commonName) {
    url += `?common_name=${encodeURIComponent(commonName)}`
  }
  return url
}

// Species card component with thumbnail
const SpeciesCard: React.FC<{
  species: NewSpeciesThisWeek
  birdLinks: Array<{ name: string; url: string; source_id: string }>
}> = ({ species, birdLinks }) => {
  const [imageError, setImageError] = useState(false)
  const imageUrl = getBirdImageUrl(
    species.scientific_name,
    species.english_name || species.common_name,
  )

  return (
    <div className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow bg-white">
      {/* Bird Image */}
      <div className="h-40 bg-gray-100 relative flex items-center justify-center">
        {!imageError ? (
          <img
            src={imageUrl}
            alt={species.common_name}
            className="max-w-full max-h-full object-contain"
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
        <div className="text-sm text-muted-foreground italic">{species.scientific_name}</div>
        {/* A species new to one station but long-known at another is still
            worth reporting — see issue #25 — so label which case this is. */}
        <div className="mt-2">
          {species.is_first_ever ? (
            <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-800">
              First ever record
            </span>
          ) : (
            <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">
              New to {species.stations.join(', ')}
            </span>
          )}
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
    </div>
  )
}

const DailyDetections: React.FC = () => {
  const { startDate, endDate, getStationIdsParam } = useFilters()
  const [dailyData, setDailyData] = useState<DailyDetectionCount[]>([])
  const [newSpecies, setNewSpecies] = useState<NewSpeciesThisWeek[]>([])
  const [returningSpecies, setReturningSpecies] = useState<ReturningSpecies[]>([])
  const [overdueSpecies, setOverdueSpecies] = useState<OverdueSpecies[]>([])
  // Three months of silence, matching the /species/returning default. Long
  // enough that a bird simply going quiet for a fortnight is not reported as
  // a return; short enough to catch a spring arrival.
  const [absenceMonths, setAbsenceMonths] = useState(3)
  const [stats, setStats] = useState<DatabaseStats | null>(null)
  const [weather, setWeather] = useState<WeatherRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Display settings
  const [temperatureUnit, setTemperatureUnit] = useState<'imperial' | 'metric'>('imperial')
  const [windSpeedUnit, setWindSpeedUnit] = useState<'imperial' | 'metric'>('imperial')
  const [birdInfoSources, setBirdInfoSources] = useState<string[]>(DEFAULT_BIRD_SOURCES)

  // Temperature conversion helpers
  const toMetricTemp = (f: number) => Math.round(((f - 32) * 5) / 9)
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

  // biome-ignore lint/correctness/useExhaustiveDependencies: intentional — loadData is closed over the filter values and we want to refetch when any of them change
  useEffect(() => {
    loadData()
  }, [startDate, endDate, getStationIdsParam(), absenceMonths])

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
        settingsApi.getBirdInfoSources(),
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

      const [daily, species, statsData, returning, overdue] = await Promise.all([
        detectionsApi.getDailyCounts(filterParams),
        speciesApi.getThisWeek({ station_ids: filterParams.station_ids }),
        detectionsApi.getStats(filterParams),
        // These two are informational: a failure shouldn't blank the page.
        speciesApi
          .getReturning({
            station_ids: filterParams.station_ids,
            min_absence_days: absenceMonths * 30,
          })
          .catch(() => [] as ReturningSpecies[]),
        speciesApi
          .getOverdue({ station_ids: filterParams.station_ids })
          .catch(() => [] as OverdueSpecies[]),
      ])

      setDailyData(daily)
      setNewSpecies(species)
      setStats(statsData)
      setReturningSpecies(returning)
      setOverdueSpecies(overdue)

      // Also load weather
      loadWeather()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  // Group data by station
  const stationGroups = useMemo(() => {
    const groups: Record<string, DailyDetectionCount[]> = {}
    dailyData.forEach((item) => {
      if (!groups[item.station_name]) {
        groups[item.station_name] = []
      }
      groups[item.station_name].push(item)
    })
    return groups
  }, [dailyData])

  const stationCount = Object.keys(stationGroups).length

  // Prepare chart data for combined view
  const prepareChartData = (): Data[] => {
    // Create traces for each station
    return Object.entries(stationGroups).map(([stationName, data]) => ({
      x: data.map((d) => d.detection_date),
      y: data.map((d) => d.detection_count),
      name: stationName,
      type: 'scatter' as const,
      mode: 'lines+markers' as const,
    }))
  }

  // Small multiples chart data for >3 stations
  const smallMultiplesData = useMemo((): { data: Data[]; layout: Partial<Layout> } | null => {
    if (stationCount <= SPARKLINE_THRESHOLD) return null

    const stationNames = Object.keys(stationGroups)
    const cols = Math.min(3, stationNames.length)
    const rows = Math.ceil(stationNames.length / cols)

    const traces: Data[] = []
    const annotations: Partial<import('plotly.js').Annotation>[] = []

    stationNames.forEach((stationName, idx) => {
      const data = stationGroups[stationName]
      const row = Math.floor(idx / cols)
      const col = idx % cols

      // Create trace for this station
      traces.push({
        x: data.map((d) => d.detection_date),
        y: data.map((d) => d.detection_count),
        type: 'scatter',
        mode: 'lines',
        name: stationName,
        line: { color: CHART_COLORS[idx % CHART_COLORS.length], width: 1.5 },
        fill: 'tozeroy',
        fillcolor: `${CHART_COLORS[idx % CHART_COLORS.length]}20`,
        xaxis: idx === 0 ? 'x' : `x${idx + 1}`,
        yaxis: idx === 0 ? 'y' : `y${idx + 1}`,
        showlegend: false,
        hovertemplate: `${stationName}<br>%{x}<br>%{y} detections<extra></extra>`,
      })

      // Add station name annotation - positioned at top of each subplot
      const xStart = col / cols + 0.02

      annotations.push({
        text: stationName,
        x: xStart,
        y: 1 - row / rows - 0.02,
        xref: 'paper',
        yref: 'paper',
        xanchor: 'left',
        yanchor: 'top',
        showarrow: false,
        font: { size: 11, weight: 700 },
      })
    })

    // Build layout with subplots
    const layout: Partial<Layout> = {
      grid: {
        rows,
        columns: cols,
        pattern: 'independent' as const,
        roworder: 'top to bottom' as const,
        xgap: 0.08,
        ygap: 0.22,
      },
      height: rows * 220 + 60,
      margin: { l: 50, r: 20, t: 40, b: 50 },
      showlegend: false,
      annotations,
    }

    // Configure each subplot axis
    stationNames.forEach((_, idx) => {
      const xKey = idx === 0 ? 'xaxis' : `xaxis${idx + 1}`
      const yKey = idx === 0 ? 'yaxis' : `yaxis${idx + 1}`

      // @ts-expect-error dynamic axis keys
      layout[xKey] = {
        tickfont: { size: 9 },
        tickangle: -45,
        showgrid: false,
      }
      // @ts-expect-error dynamic axis keys
      layout[yKey] = {
        tickfont: { size: 9 },
        showgrid: true,
        gridcolor: '#f0f0f0',
        rangemode: 'tozero',
      }
    })

    return { data: traces, layout }
  }, [stationGroups, stationCount])

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
            <div className="text-3xl font-bold mt-2 text-indigo-dark">
              {stats.total_detections.toLocaleString()}
            </div>
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
              <div className="text-2xl font-bold mt-1">{weather.weather_description || 'N/A'}</div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold">{formatTemp(weather.temp_avg)}</div>
              <div className="text-sm opacity-80">
                {weather.temp_min !== null && weather.temp_max !== null
                  ? `${temperatureUnit === 'metric' ? toMetricTemp(weather.temp_min) : Math.round(weather.temp_min)}° / ${temperatureUnit === 'metric' ? toMetricTemp(weather.temp_max) : Math.round(weather.temp_max)}°`
                  : ''}
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
              <div className="font-semibold">
                {weather.humidity !== null ? `${Math.round(weather.humidity)}%` : '--'}
              </div>
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
        {stationCount > SPARKLINE_THRESHOLD && (
          <p className="text-sm text-muted-foreground mb-4">
            Using small multiples view for {stationCount} stations (threshold: {SPARKLINE_THRESHOLD}
            )
          </p>
        )}
        {dailyData.length > 0 ? (
          stationCount > SPARKLINE_THRESHOLD && smallMultiplesData ? (
            <Plot
              data={smallMultiplesData.data}
              layout={smallMultiplesData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          ) : (
            <LineChart
              data={prepareChartData()}
              layout={{
                title: { text: 'Daily Detections by Station' },
                xaxis: { title: { text: 'Date' } },
                yaxis: { title: { text: 'Number of Detections' } },
                height: 500,
              }}
            />
          )
        ) : (
          <div className="text-center text-muted-foreground py-8">No detection data available</div>
        )}
      </div>

      {/* New Species This Week */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">New Species This Week</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Species whose first-ever detection was this week
        </p>
        {newSpecies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {newSpecies.map((species) => {
              const birdLinks = generateBirdLinks(
                species.common_name,
                species.scientific_name,
                species.ebird_code,
                birdInfoSources,
                undefined,
                species.english_name,
              )
              return (
                <SpeciesCard
                  key={species.species_id || species.common_name}
                  species={species}
                  birdLinks={birdLinks}
                />
              )
            })}
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-8">No new species this week</div>
        )}
      </div>

      {/* Back After an Absence.
          Three months is long enough to separate a genuine seasonal return
          from a bird that just went quiet for a fortnight, but in a temperate
          region most of what lands here is normal migration working as
          expected — which is the point of the list. */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
          <h2 className="text-xl font-semibold">Back After an Absence</h2>
          <div className="flex items-center gap-2">
            <label htmlFor="absence-threshold" className="text-sm text-muted-foreground">
              Absence of at least
            </label>
            <select
              id="absence-threshold"
              value={absenceMonths}
              onChange={(e) => setAbsenceMonths(Number(e.target.value))}
              className="px-2 py-1 border rounded text-sm"
            >
              <option value={2}>2 months</option>
              <option value={3}>3 months</option>
              <option value={4}>4 months</option>
              <option value={6}>6 months</option>
              <option value={9}>9 months</option>
            </select>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Species heard again in the last fortnight after at least {absenceMonths} months of
          silence — the returning migrants and seasonal singers.
        </p>
        {returningSpecies.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Species
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Heard again
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Previously
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Away
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Detections since
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {returningSpecies.map((species) => (
                  <tr key={species.internal_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <Link
                        to={`/species-details?id=${species.internal_id}`}
                        className="font-medium text-gray-900 hover:text-indigo-600 hover:underline"
                      >
                        {species.common_name}
                      </Link>
                      <div className="text-xs text-gray-500 italic">
                        {species.scientific_name}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {new Date(species.returned_on).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {new Date(species.previous_seen).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                      {Math.round(species.absence_days / 30)} months
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                      {species.detection_count.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No species have returned after {absenceMonths}+ months recently
          </div>
        )}
      </div>

      {/* Expected But Not Yet Heard.
          Compared against the same calendar window in previous years rather
          than a fixed threshold, so a bird that simply hasn't arrived on
          schedule is distinguishable from one that was never due. */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-1">Expected But Not Yet Heard</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Species detected around this time of year in previous years, but not in the last three
          weeks. Needs a full year of history before it can report anything.
        </p>
        {overdueSpecies.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Species
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last heard
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Days absent
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usually by
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Seen in
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {overdueSpecies.map((species) => (
                  <tr key={species.internal_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <Link
                        to={`/species-details?id=${species.internal_id}`}
                        className="font-medium text-gray-900 hover:text-indigo-600 hover:underline"
                      >
                        {species.common_name}
                      </Link>
                      <div className="text-xs text-gray-500 italic">
                        {species.scientific_name}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {species.last_seen
                        ? new Date(species.last_seen).toLocaleDateString()
                        : 'Never'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                      {species.days_absent ?? '—'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {species.typical_arrival ?? '—'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {species.prior_years.join(', ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-8">
            Nothing overdue — every species seen at this time of year in the past has been heard
            recently
          </div>
        )}
      </div>
    </div>
  )
}

export default DailyDetections

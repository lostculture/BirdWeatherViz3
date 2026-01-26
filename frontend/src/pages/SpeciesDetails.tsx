/**
 * Species Details Page
 * Individual species analysis with multiple visualizations.
 * Color palette: Male Indigo Bunting
 *
 * Version: 1.1.0
 */

import React, { useEffect, useState } from 'react'
import { speciesApi, settingsApi, generateBirdLinks, DEFAULT_BIRD_SOURCES } from '../api'
import type { SpeciesResponse } from '../types/api'
import type {
  HourlyPattern,
  MonthlyPattern,
  TimelinePoint,
  StationDistribution,
  ConfidenceByStation,
} from '../api/species'
import { BarChart, LineChart, PieChart } from '../components/charts'
import type { Data, Layout } from 'plotly.js'

// Helper to get bird image URL from our API
const getBirdImageUrl = (scientificName: string, commonName?: string): string => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  let url = `${baseUrl}/images/bird/${encodeURIComponent(scientificName)}`
  if (commonName) {
    url += `?common_name=${encodeURIComponent(commonName)}`
  }
  return url
}

// Indigo Bunting color palette
const COLORS = {
  brilliant: '#4169E1',
  deep: '#1E3A8A',
  cerulean: '#5B9BD5',
  dark: '#0F172A',
  brown: '#8B7355',
}

const STATION_COLORS = [COLORS.deep, COLORS.cerulean, COLORS.brilliant, COLORS.brown]

const SpeciesDetails: React.FC = () => {
  const [speciesList, setSpeciesList] = useState<SpeciesResponse[]>([])
  const [selectedSpeciesId, setSelectedSpeciesId] = useState<number | null>(null)
  const [selectedSpecies, setSelectedSpecies] = useState<SpeciesResponse | null>(null)
  const [hourlyData, setHourlyData] = useState<HourlyPattern[]>([])
  const [monthlyData, setMonthlyData] = useState<MonthlyPattern[]>([])
  const [timelineData, setTimelineData] = useState<TimelinePoint[]>([])
  const [stationDist, setStationDist] = useState<StationDistribution[]>([])
  const [confidenceData, setConfidenceData] = useState<ConfidenceByStation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timelineMonths, setTimelineMonths] = useState<number | null>(null)
  const [birdImageUrl, setBirdImageUrl] = useState<string | null>(null)
  const [imageError, setImageError] = useState(false)
  const [birdInfoSources, setBirdInfoSources] = useState<string[]>(DEFAULT_BIRD_SOURCES)

  // Load species list and settings on mount
  useEffect(() => {
    loadSpeciesList()
    loadDisplaySettings()
  }, [])

  const loadDisplaySettings = async () => {
    try {
      const sources = await settingsApi.getBirdInfoSources()
      setBirdInfoSources(sources)
    } catch (err) {
      console.log('Failed to load display settings, using defaults')
    }
  }

  // Load species data when selection changes
  useEffect(() => {
    if (selectedSpeciesId) {
      loadSpeciesData(selectedSpeciesId)
    }
  }, [selectedSpeciesId, timelineMonths])

  const loadSpeciesList = async () => {
    try {
      const list = await speciesApi.getList()
      setSpeciesList(list.sort((a, b) => a.common_name.localeCompare(b.common_name)))
      // Auto-select first species
      if (list.length > 0) {
        setSelectedSpeciesId(list[0].id)
      }
      setLoading(false)
    } catch (err) {
      setError('Failed to load species list')
      setLoading(false)
    }
  }

  const loadSpeciesData = async (speciesId: number) => {
    try {
      setLoading(true)
      setImageError(false)
      const [species, hourly, monthly, timeline, distribution, confidence] = await Promise.all([
        speciesApi.getById(speciesId),
        speciesApi.getHourlyPattern(speciesId),
        speciesApi.getMonthlyPattern(speciesId),
        speciesApi.getTimeline(speciesId, timelineMonths || undefined),
        speciesApi.getStationDistribution(speciesId),
        speciesApi.getConfidenceByStation(speciesId),
      ])
      setSelectedSpecies(species)
      setHourlyData(hourly)
      setMonthlyData(monthly)
      setTimelineData(timeline)
      setStationDist(distribution)
      setConfidenceData(confidence)
      // Set bird image URL (pass both scientific and common name)
      setBirdImageUrl(getBirdImageUrl(species.scientific_name, species.common_name))
      setLoading(false)
    } catch (err) {
      setError('Failed to load species data')
      setLoading(false)
    }
  }

  // Prepare rose plot data (24-hour circular)
  // Orientation: 6AM at 270° (left), 12PM at 0° (top), 6PM at 90° (right), 12AM at 180° (bottom)
  const prepareRosePlotData = (): { data: Data[]; layout: Partial<Layout> } => {
    // Convert hour to degrees: hour * 15 + 180 puts 12:00 at top (0°), 6AM at 270°, 6PM at 90°
    const theta = hourlyData.map((d) => (d.hour * 15 + 180) % 360)
    const r = hourlyData.map((d) => d.detection_count)
    const hoverText = hourlyData.map((d) => `${d.hour.toString().padStart(2, '0')}:00<br>${d.detection_count} detections`)

    return {
      data: [
        {
          type: 'barpolar',
          r: r,
          theta: theta,
          width: Array(24).fill(14),
          marker: { color: COLORS.brown },
          hovertext: hoverText,
          hoverinfo: 'text',
        } as Data,
      ],
      layout: {
        polar: {
          angularaxis: {
            tickmode: 'array',
            tickvals: [0, 45, 90, 135, 180, 225, 270, 315],
            ticktext: ['12:00', '15:00', '18:00', '21:00', '00:00', '03:00', '06:00', '09:00'],
            direction: 'clockwise',
          },
          radialaxis: {
            ticksuffix: '',
          },
        },
        showlegend: false,
        height: 400,
        margin: { t: 40, b: 40, l: 40, r: 40 },
      },
    }
  }

  // Prepare 48-hour KDE-style area chart
  const prepare48HourData = (): Data[] => {
    // Duplicate the data to show 48-hour continuity
    const extended = [...hourlyData, ...hourlyData]
    const x = extended.map((_, i) => i)
    const y = extended.map((d) => d.detection_count)

    // Simple smoothing
    const smoothed = y.map((_, i) => {
      const start = Math.max(0, i - 1)
      const end = Math.min(y.length, i + 2)
      const windowData = y.slice(start, end)
      return windowData.reduce((a, b) => a + b, 0) / windowData.length
    })

    return [
      {
        x: x,
        y: smoothed,
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: `${COLORS.brown}80`,
        line: { color: COLORS.brown, shape: 'spline' },
        hovertemplate: 'Hour %{x}: %{y:.0f} detections<extra></extra>',
      } as Data,
    ]
  }

  // Prepare hourly bar chart data
  const prepareHourlyBarData = (): Data[] => {
    return [
      {
        x: hourlyData.map((d) => d.hour),
        y: hourlyData.map((d) => d.detection_count),
        type: 'bar',
        marker: { color: COLORS.brilliant },
        hovertemplate: '%{x}:00<br>%{y} detections<extra></extra>',
      } as Data,
    ]
  }

  // Prepare monthly bar chart data
  const prepareMonthlyBarData = (): Data[] => {
    return [
      {
        x: monthlyData.map((d) => d.month_name),
        y: monthlyData.map((d) => d.detection_count),
        type: 'bar',
        marker: { color: COLORS.brilliant },
        hovertemplate: '%{x}<br>%{y} detections<extra></extra>',
      } as Data,
    ]
  }

  // Prepare timeline data (grouped by station)
  const prepareTimelineData = (): Data[] => {
    const stations = [...new Set(timelineData.map((d) => d.station_name))]
    return stations.map((station, idx) => {
      const stationData = timelineData.filter((d) => d.station_name === station)
      return {
        x: stationData.map((d) => d.date),
        y: stationData.map((d) => d.detection_count),
        name: station,
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: STATION_COLORS[idx % STATION_COLORS.length] },
        marker: { size: 6 },
      } as Data
    })
  }

  // Prepare pie chart data
  const preparePieData = (): Data[] => {
    return [
      {
        labels: stationDist.map((d) => d.station_name),
        values: stationDist.map((d) => d.detection_count),
        type: 'pie',
        marker: { colors: STATION_COLORS },
        textinfo: 'percent',
        hovertemplate: '%{label}<br>%{value} detections (%{percent})<extra></extra>',
      } as Data,
    ]
  }

  // Prepare confidence bar chart data
  const prepareConfidenceData = (): Data[] => {
    return [
      {
        x: confidenceData.map((d) => d.station_name),
        y: confidenceData.map((d) => d.avg_confidence),
        type: 'bar',
        marker: { color: COLORS.brilliant },
        hovertemplate: '%{x}<br>Avg Confidence: %{y:.2f}<extra></extra>',
      } as Data,
    ]
  }

  if (loading && speciesList.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground">Loading species list...</div>
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

  const rosePlot = prepareRosePlotData()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Individual Species Analysis</h1>
        <p className="text-muted-foreground mt-2">
          Select a species to analyze its detection patterns and statistics
        </p>
      </div>

      {/* Species Selector */}
      <div className="bg-white rounded-lg shadow p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Species to Analyze
        </label>
        <select
          value={selectedSpeciesId || ''}
          onChange={(e) => setSelectedSpeciesId(Number(e.target.value))}
          className="w-full md:w-96 p-3 border rounded-lg text-lg focus:ring-2 focus:ring-indigo-brilliant focus:border-indigo-brilliant"
        >
          {speciesList.map((species) => (
            <option key={species.id} value={species.id}>
              {species.common_name} ({species.scientific_name})
            </option>
          ))}
        </select>
      </div>

      {selectedSpecies && (
        <>
          {/* Species Info Card */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex flex-col md:flex-row gap-6">
              {/* Bird Image */}
              <div className="flex-shrink-0">
                {birdImageUrl && !imageError ? (
                  <img
                    src={birdImageUrl}
                    alt={selectedSpecies.common_name}
                    className="w-32 h-32 md:w-40 md:h-40 object-cover rounded-lg shadow"
                    onError={() => setImageError(true)}
                  />
                ) : (
                  <div className="w-32 h-32 md:w-40 md:h-40 bg-gray-100 rounded-lg flex items-center justify-center">
                    <span className="text-4xl">🐦</span>
                  </div>
                )}
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-indigo-dark">{selectedSpecies.common_name}</h2>
                <p className="text-lg text-muted-foreground italic">{selectedSpecies.scientific_name}</p>
                {selectedSpecies.family && (
                  <p className="text-sm text-muted-foreground mt-1">Family: {selectedSpecies.family}</p>
                )}
                <div className="mt-4 flex flex-wrap gap-3">
                  {generateBirdLinks(
                    selectedSpecies.common_name,
                    selectedSpecies.scientific_name,
                    selectedSpecies.ebird_code,
                    birdInfoSources,
                    selectedSpecies.inat_taxon_id
                  ).map((link) => (
                    <a
                      key={link.source_id}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-brilliant hover:underline text-sm"
                    >
                      {link.name} →
                    </a>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-indigo-dark">
                    {selectedSpecies.total_detections?.toLocaleString() || 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Total Detections</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-indigo-dark">
                    {stationDist.length}
                  </div>
                  <div className="text-sm text-muted-foreground">Stations</div>
                </div>
              </div>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Rose Plot */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">24-Hour Activity Pattern (Rose Plot)</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Circular view showing activity distribution around the clock. 12:00 noon at top.
              </p>
              <LineChart data={rosePlot.data} layout={rosePlot.layout} />
            </div>

            {/* 48-Hour KDE */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">48-Hour Activity Pattern</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Shows two complete day cycles to visualize midnight continuity.
              </p>
              <LineChart
                data={prepare48HourData()}
                layout={{
                  xaxis: {
                    title: { text: 'Hour of Day (Two 24-hour cycles)' },
                    tickmode: 'array',
                    tickvals: [0, 6, 12, 18, 24, 30, 36, 42],
                    ticktext: ['0', '6', '12', '18', '0', '6', '12', '18'],
                  },
                  yaxis: { title: { text: 'Activity Density' } },
                  height: 300,
                  showlegend: false,
                }}
              />
            </div>

            {/* Hourly Bar Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Detections by Hour of Day</h3>
              <BarChart
                data={prepareHourlyBarData()}
                layout={{
                  xaxis: { title: { text: 'Hour (24h)' } },
                  yaxis: { title: { text: 'Number of Detections' } },
                  height: 300,
                }}
              />
            </div>

            {/* Monthly Bar Chart */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Detections by Month of Year</h3>
              <BarChart
                data={prepareMonthlyBarData()}
                layout={{
                  xaxis: { title: { text: 'Month' } },
                  yaxis: { title: { text: 'Number of Detections' } },
                  height: 300,
                }}
              />
            </div>
          </div>

          {/* Timeline */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
              <h3 className="text-lg font-semibold">Detections Over Time</h3>
              <div className="flex gap-2 mt-2 md:mt-0">
                {[
                  { label: 'Last Month', value: 1 },
                  { label: '3 Months', value: 3 },
                  { label: '6 Months', value: 6 },
                  { label: '12 Months', value: 12 },
                  { label: 'All Data', value: null },
                ].map((opt) => (
                  <button
                    key={opt.label}
                    onClick={() => setTimelineMonths(opt.value)}
                    className={`px-3 py-1 text-sm rounded ${
                      timelineMonths === opt.value
                        ? 'bg-indigo-brilliant text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <LineChart
              data={prepareTimelineData()}
              layout={{
                xaxis: { title: { text: 'Date' } },
                yaxis: { title: { text: 'Number of Detections' } },
                height: 350,
                legend: { orientation: 'h', y: -0.2 },
              }}
            />
          </div>

          {/* Bottom Row: Pie and Confidence */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Station Distribution Pie */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Distribution Across Stations</h3>
              <PieChart
                data={preparePieData()}
                layout={{
                  height: 350,
                  showlegend: true,
                  legend: { orientation: 'v', x: 1, y: 0.5 },
                }}
              />
            </div>

            {/* Confidence by Station */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Detection Confidence Levels</h3>
              <BarChart
                data={prepareConfidenceData()}
                layout={{
                  xaxis: { title: { text: 'Station' } },
                  yaxis: { title: { text: 'Average Confidence' }, range: [0, 1] },
                  height: 350,
                }}
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default SpeciesDetails

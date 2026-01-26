/**
 * Advanced Analytics Page
 * Complex visualizations for deep data analysis.
 *
 * Version: 1.0.0
 */

import React, { useEffect, useState, useMemo } from 'react'
import { analyticsApi, stationsApi } from '../api'
import type {
  SpeciesHourBubble,
  PhenologyCell,
  ConfidenceScatterPoint,
  ConfidenceByHour,
  TemporalDistribution,
} from '../api/analytics'
import type { StationResponse } from '../types/api'
import type { Data, Layout } from 'plotly.js'
import Plot from 'react-plotly.js'

// Color scale for heatmaps
const HEATMAP_COLORSCALE: [number, string][] = [
  [0, '#F8FAFC'],
  [0.2, '#E0E7FF'],
  [0.4, '#A5B4FC'],
  [0.6, '#6366F1'],
  [0.8, '#4338CA'],
  [1, '#1E1B4B'],
]

const AdvancedAnalytics: React.FC = () => {
  // Data states
  const [bubbleData, setBubbleData] = useState<SpeciesHourBubble[]>([])
  const [phenologyData, setPhenologyData] = useState<PhenologyCell[]>([])
  const [scatterData, setScatterData] = useState<ConfidenceScatterPoint[]>([])
  const [confidenceHourData, setConfidenceHourData] = useState<ConfidenceByHour[]>([])
  const [temporalData, setTemporalData] = useState<TemporalDistribution[]>([])
  const [stations, setStations] = useState<StationResponse[]>([])

  // UI states
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedStations, setSelectedStations] = useState<number[]>([])
  const [bubbleLimit, setBubbleLimit] = useState(30)
  const [phenologyYear, setPhenologyYear] = useState(new Date().getFullYear())

  useEffect(() => {
    loadStations()
  }, [])

  useEffect(() => {
    loadAllData()
  }, [selectedStations, bubbleLimit, phenologyYear])

  const loadStations = async () => {
    try {
      const stationList = await stationsApi.getAll()
      setStations(stationList)
    } catch (err) {
      console.error('Failed to load stations:', err)
    }
  }

  const loadAllData = async () => {
    try {
      setLoading(true)
      setError(null)

      const stationIds = selectedStations.length > 0
        ? selectedStations.join(',')
        : undefined

      const [bubble, phenology, scatter, confHour, temporal] = await Promise.all([
        analyticsApi.getSpeciesHourBubble({
          limit: bubbleLimit,
          months: 3,
          station_ids: stationIds,
        }),
        analyticsApi.getPhenology({
          year: phenologyYear,
          station_ids: stationIds,
          limit: 40,
        }),
        analyticsApi.getConfidenceScatter({
          station_ids: stationIds,
          min_detections: 10,
        }),
        analyticsApi.getConfidenceByHour({
          station_ids: stationIds,
          months: 6,
        }),
        analyticsApi.getTemporalDistribution({
          station_ids: stationIds,
          months: 6,
          limit: 15,
        }),
      ])

      setBubbleData(bubble)
      setPhenologyData(phenology)
      setScatterData(scatter)
      setConfidenceHourData(confHour)
      setTemporalData(temporal)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }

  // Prepare bubble chart data
  const bubbleChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (bubbleData.length === 0) {
      return { data: [], layout: {} }
    }

    // Get unique species sorted by total detections
    const speciesOrder = [...new Set(bubbleData.map(d => d.common_name))]
      .map(name => {
        const item = bubbleData.find(d => d.common_name === name)
        return { name, total: item?.total_detections || 0 }
      })
      .sort((a, b) => b.total - a.total)
      .map(s => s.name)

    const maxCount = Math.max(...bubbleData.map(d => d.detection_count))

    return {
      data: [{
        type: 'scatter',
        mode: 'markers',
        x: bubbleData.map(d => d.hour),
        y: bubbleData.map(d => d.common_name),
        marker: {
          size: bubbleData.map(d => Math.sqrt(d.detection_count / maxCount) * 40 + 5),
          color: bubbleData.map(d => d.detection_count),
          colorscale: 'Blues',
          showscale: true,
          colorbar: { title: { text: 'Detections' } },
        },
        text: bubbleData.map(d => `${d.common_name}<br>Hour: ${d.hour}:00<br>Detections: ${d.detection_count}`),
        hovertemplate: '%{text}<extra></extra>',
      }],
      layout: {
        title: { text: 'Species Activity by Hour of Day', font: { size: 16 } },
        xaxis: {
          title: { text: 'Hour of Day' },
          tickmode: 'array',
          tickvals: [0, 3, 6, 9, 12, 15, 18, 21],
          ticktext: ['12am', '3am', '6am', '9am', '12pm', '3pm', '6pm', '9pm'],
          range: [-0.5, 23.5],
        },
        yaxis: {
          title: { text: '' },
          categoryorder: 'array',
          categoryarray: speciesOrder.reverse(),
          tickfont: { size: 10 },
        },
        height: Math.max(400, speciesOrder.length * 20 + 100),
        margin: { l: 150, r: 80, t: 50, b: 50 },
      },
    }
  }, [bubbleData])

  // Prepare phenology heatmap data
  const phenologyChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (phenologyData.length === 0) {
      return { data: [], layout: {} }
    }

    // Get unique species and weeks
    const speciesNames = [...new Set(phenologyData.map(d => d.common_name))]
    const weeks = [...new Set(phenologyData.map(d => d.week_number))].sort((a, b) => a - b)

    // Build matrix
    const matrix: number[][] = speciesNames.map(species => {
      return weeks.map(week => {
        const cell = phenologyData.find(d => d.common_name === species && d.week_number === week)
        return cell?.detection_count || 0
      })
    })

    // Sort species by total detections
    const speciesWithTotals = speciesNames.map((name, idx) => ({
      name,
      total: matrix[idx].reduce((a, b) => a + b, 0),
      row: matrix[idx],
    })).sort((a, b) => b.total - a.total)

    return {
      data: [{
        type: 'heatmap',
        z: speciesWithTotals.map(s => s.row),
        x: weeks.map(w => `W${w}`),
        y: speciesWithTotals.map(s => s.name),
        colorscale: HEATMAP_COLORSCALE,
        hovertemplate: '%{y}<br>Week %{x}<br>Detections: %{z}<extra></extra>',
        colorbar: { title: { text: 'Detections' } },
      }],
      layout: {
        title: { text: `Phenology Heatmap - ${phenologyYear}`, font: { size: 16 } },
        xaxis: {
          title: { text: 'Week of Year' },
          tickangle: -45,
          tickfont: { size: 9 },
        },
        yaxis: {
          title: { text: '' },
          tickfont: { size: 10 },
        },
        height: Math.max(400, speciesWithTotals.length * 18 + 120),
        margin: { l: 150, r: 80, t: 50, b: 80 },
      },
    }
  }, [phenologyData, phenologyYear])

  // Prepare confidence scatter data
  const scatterChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (scatterData.length === 0) {
      return { data: [], layout: {} }
    }

    return {
      data: [{
        type: 'scatter',
        mode: 'markers',
        x: scatterData.map(d => d.total_detections),
        y: scatterData.map(d => d.avg_confidence),
        text: scatterData.map(d => d.common_name),
        textposition: 'top center',
        textfont: { size: 9 },
        marker: {
          size: scatterData.map(d => Math.sqrt(d.detection_days) * 3 + 8),
          color: scatterData.map(d => d.avg_confidence),
          colorscale: 'RdYlGn',
          cmin: 0.5,
          cmax: 1.0,
          showscale: true,
          colorbar: { title: { text: 'Confidence' } },
        },
        hovertemplate: '%{text}<br>Detections: %{x}<br>Avg Confidence: %{y:.2f}<br>Detection Days: %{marker.size}<extra></extra>',
      }],
      layout: {
        title: { text: 'Detection Count vs Average Confidence', font: { size: 16 } },
        xaxis: {
          title: { text: 'Total Detections' },
          type: 'log',
        },
        yaxis: {
          title: { text: 'Average Confidence' },
          range: [0.5, 1.02],
        },
        height: 500,
        margin: { l: 60, r: 80, t: 50, b: 50 },
        showlegend: false,
      },
    }
  }, [scatterData])

  // Prepare confidence by hour heatmap
  const confidenceHourChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (confidenceHourData.length === 0) {
      return { data: [], layout: {} }
    }

    const hours = Array.from({ length: 24 }, (_, i) => i)
    const bins = ['0.50-0.60', '0.60-0.70', '0.70-0.80', '0.80-0.90', '0.90-1.00']

    // Build matrix
    const matrix: number[][] = bins.map(bin => {
      return hours.map(hour => {
        const cell = confidenceHourData.find(d => d.hour === hour && d.confidence_bin === bin)
        return cell?.detection_count || 0
      })
    })

    return {
      data: [{
        type: 'heatmap',
        z: matrix,
        x: hours.map(h => `${h}:00`),
        y: bins,
        colorscale: HEATMAP_COLORSCALE,
        hovertemplate: 'Hour: %{x}<br>Confidence: %{y}<br>Detections: %{z}<extra></extra>',
        colorbar: { title: { text: 'Detections' } },
      }],
      layout: {
        title: { text: 'Detection Confidence by Hour of Day', font: { size: 16 } },
        xaxis: {
          title: { text: 'Hour of Day' },
          tickangle: -45,
          tickfont: { size: 10 },
        },
        yaxis: {
          title: { text: 'Confidence Range' },
        },
        height: 350,
        margin: { l: 80, r: 80, t: 50, b: 80 },
      },
    }
  }, [confidenceHourData])

  // Prepare temporal distribution data
  const temporalChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (temporalData.length === 0) {
      return { data: [], layout: {} }
    }

    // Group by species
    const speciesGroups = new Map<string, TemporalDistribution[]>()
    temporalData.forEach(d => {
      if (!speciesGroups.has(d.common_name)) {
        speciesGroups.set(d.common_name, [])
      }
      speciesGroups.get(d.common_name)!.push(d)
    })

    // Create traces for each species
    const traces: Data[] = Array.from(speciesGroups.entries()).map(([name, data]) => ({
      type: 'scatter',
      mode: 'lines',
      name,
      x: data.map(d => d.date),
      y: data.map(d => d.detection_count),
      fill: 'tozeroy',
      opacity: 0.7,
      line: { width: 1 },
      hovertemplate: `${name}<br>%{x}<br>%{y} detections<extra></extra>`,
    }))

    return {
      data: traces,
      layout: {
        title: { text: 'Detection Distribution Over Time', font: { size: 16 } },
        xaxis: {
          title: { text: 'Date' },
          type: 'date',
        },
        yaxis: {
          title: { text: 'Daily Detections' },
        },
        height: 400,
        margin: { l: 60, r: 20, t: 50, b: 50 },
        showlegend: true,
        legend: {
          orientation: 'h',
          y: -0.2,
          font: { size: 10 },
        },
      },
    }
  }, [temporalData])

  const handleStationToggle = (stationId: number) => {
    setSelectedStations(prev =>
      prev.includes(stationId)
        ? prev.filter(id => id !== stationId)
        : [...prev, stationId]
    )
  }

  if (loading && bubbleData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground">Loading analytics...</div>
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
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Advanced Analytics</h1>
        <p className="text-muted-foreground mt-2">
          Deep analysis of detection patterns, confidence, and temporal trends
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4 items-center">
          {/* Station Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Stations</label>
            <div className="flex flex-wrap gap-2">
              {stations.map(station => (
                <button
                  key={station.id}
                  onClick={() => handleStationToggle(station.id)}
                  className={`px-3 py-1 text-sm rounded-full transition-colors ${
                    selectedStations.includes(station.id)
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {station.name}
                </button>
              ))}
              {selectedStations.length > 0 && (
                <button
                  onClick={() => setSelectedStations([])}
                  className="px-3 py-1 text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Bubble Chart Limit */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Species Limit (Bubble)
            </label>
            <select
              value={bubbleLimit}
              onChange={(e) => setBubbleLimit(Number(e.target.value))}
              className="px-3 py-1 border rounded text-sm"
            >
              <option value={20}>Top 20</option>
              <option value={30}>Top 30</option>
              <option value={50}>Top 50</option>
            </select>
          </div>

          {/* Phenology Year */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Phenology Year
            </label>
            <select
              value={phenologyYear}
              onChange={(e) => setPhenologyYear(Number(e.target.value))}
              className="px-3 py-1 border rounded text-sm"
            >
              {[2024, 2025, 2026].map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Species Activity Patterns Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Species Activity Patterns</h2>

        {/* Bubble Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-muted-foreground mb-2">
            Bubble size and color indicate detection count. Shows when each species is most active.
          </p>
          {bubbleData.length > 0 ? (
            <Plot
              data={bubbleChartData.data}
              layout={bubbleChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              No data available
            </div>
          )}
        </div>

        {/* Phenology Heatmap */}
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-muted-foreground mb-2">
            Weekly detection intensity throughout the year. Reveals seasonal patterns and migration timing.
          </p>
          {phenologyData.length > 0 ? (
            <Plot
              data={phenologyChartData.data}
              layout={phenologyChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              No data available for {phenologyYear}
            </div>
          )}
        </div>
      </div>

      {/* Data Quality Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Data Quality Analysis</h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Confidence Scatter */}
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-muted-foreground mb-2">
              Species with high detections and high confidence are the most reliably identified.
            </p>
            {scatterData.length > 0 ? (
              <Plot
                data={scatterChartData.data}
                layout={scatterChartData.layout}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%' }}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            )}
          </div>

          {/* Confidence by Hour */}
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-muted-foreground mb-2">
              Shows how detection confidence varies throughout the day.
            </p>
            {confidenceHourData.length > 0 ? (
              <Plot
                data={confidenceHourChartData.data}
                layout={confidenceHourChartData.layout}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%' }}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Temporal Distribution Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Temporal Distribution</h2>

        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-muted-foreground mb-2">
            Daily detection patterns for top species over the past 6 months.
          </p>
          {temporalData.length > 0 ? (
            <Plot
              data={temporalChartData.data}
              layout={temporalChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              No data available
            </div>
          )}
        </div>
      </div>

      {/* Loading indicator for refreshes */}
      {loading && bubbleData.length > 0 && (
        <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg px-4 py-2 text-sm">
          Refreshing data...
        </div>
      )}
    </div>
  )
}

export default AdvancedAnalytics

/**
 * Advanced Analytics Page
 * Complex visualizations for deep data analysis.
 *
 * Version: 1.0.0
 */

import type { Data, Layout } from 'plotly.js'
import React, { useEffect, useState, useMemo } from 'react'
import Plot from 'react-plotly.js'
import { analyticsApi, stationsApi } from '../api'
import type {
  CoOccurrenceCell,
  ConfidenceByHour,
  ConfidenceScatterPoint,
  DawnChorusPoint,
  MonthlyChampion,
  PhenologyCell,
  SpeciesHourBubble,
  TemporalDistribution,
  WeatherImpact,
} from '../api/analytics'
import type { StationResponse } from '../types/api'

// Color scale for heatmaps - exponential distribution to show low counts better
const HEATMAP_COLORSCALE: [number, string][] = [
  [0, '#F8FAFC'], // 0%
  [0.01, '#EEF2FF'], // 1% - very light
  [0.05, '#E0E7FF'], // 5% - light indigo
  [0.15, '#C7D2FE'], // 15%
  [0.3, '#A5B4FC'], // 30%
  [0.5, '#818CF8'], // 50%
  [0.7, '#6366F1'], // 70%
  [0.85, '#4338CA'], // 85%
  [1, '#1E1B4B'], // 100% - darkest
]

// Gaussian KDE computation — pure, hoisted so useMemo dep list stays stable
const computeKDE = (data: number[], bandwidth: number, gridPoints: number[]): number[] => {
  // Gaussian kernel: K(u) = (1/sqrt(2*pi)) * exp(-0.5 * u^2)
  return gridPoints.map((x) => {
    let sum = 0
    for (const xi of data) {
      const u = (x - xi) / bandwidth
      sum += Math.exp(-0.5 * u * u)
    }
    return sum / (data.length * bandwidth * Math.sqrt(2 * Math.PI))
  })
}

const AdvancedAnalytics: React.FC = () => {
  // Data states
  const [bubbleData, setBubbleData] = useState<SpeciesHourBubble[]>([])
  const [phenologyData, setPhenologyData] = useState<PhenologyCell[]>([])
  const [scatterData, setScatterData] = useState<ConfidenceScatterPoint[]>([])
  const [confidenceHourData, setConfidenceHourData] = useState<ConfidenceByHour[]>([])
  const [temporalData, setTemporalData] = useState<TemporalDistribution[]>([])
  const [dawnChorusData, setDawnChorusData] = useState<DawnChorusPoint[]>([])
  const [weatherData, setWeatherData] = useState<WeatherImpact[]>([])
  const [precipData, setPrecipData] = useState<WeatherImpact[]>([])
  const [coOccurrenceData, setCoOccurrenceData] = useState<CoOccurrenceCell[]>([])
  const [monthlyChampionsData, setMonthlyChampionsData] = useState<MonthlyChampion[]>([])
  const [stations, setStations] = useState<StationResponse[]>([])

  // UI states
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedStations, setSelectedStations] = useState<number[]>([])
  const [bubbleLimit, setBubbleLimit] = useState(30)
  const [phenologyYear, setPhenologyYear] = useState(0) // 0 = Rolling 12 months (default)

  useEffect(() => {
    loadStations()
  }, [])

  // biome-ignore lint/correctness/useExhaustiveDependencies: intentional — loadAllData reads the filter state from closure
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

      const stationIds = selectedStations.length > 0 ? selectedStations.join(',') : undefined

      const [
        bubble,
        phenology,
        scatter,
        confHour,
        temporal,
        dawnChorus,
        weather,
        precip,
        coOccurrence,
        champions,
      ] = await Promise.all([
        analyticsApi.getSpeciesHourBubble({
          limit: bubbleLimit >= 9999 ? 500 : bubbleLimit, // Cap at 500 for "All"
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
          limit: 200, // All species for density plot
        }),
        analyticsApi.getDawnChorus({
          station_ids: stationIds,
          months: 6,
        }),
        analyticsApi.getWeatherImpact({
          station_ids: stationIds,
          months: 6,
          analysis_type: 'temperature',
        }),
        analyticsApi.getWeatherImpact({
          station_ids: stationIds,
          months: 6,
          analysis_type: 'precipitation',
        }),
        analyticsApi.getCoOccurrence({
          station_ids: stationIds,
          months: 6,
          limit: 15,
        }),
        analyticsApi.getMonthlyChampions({
          station_ids: stationIds,
          year: phenologyYear,
        }),
      ])

      setBubbleData(bubble)
      setPhenologyData(phenology)
      setScatterData(scatter)
      setConfidenceHourData(confHour)
      setTemporalData(temporal)
      setDawnChorusData(dawnChorus)
      setWeatherData(weather)
      setPrecipData(precip)
      setCoOccurrenceData(coOccurrence)
      setMonthlyChampionsData(champions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }

  // Prepare heatmap chart data (converted from bubble)
  const bubbleChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (bubbleData.length === 0) {
      return { data: [], layout: {} }
    }

    // Get unique species sorted by total detections
    const speciesOrder = [...new Set(bubbleData.map((d) => d.common_name))]
      .map((name) => {
        const item = bubbleData.find((d) => d.common_name === name)
        return { name, total: item?.total_detections || 0 }
      })
      .sort((a, b) => b.total - a.total)
      .map((s) => s.name)

    // Build heatmap matrix: species (rows) x hours (columns)
    const hours = Array.from({ length: 24 }, (_, i) => i)
    const matrix: number[][] = speciesOrder.map((species) => {
      return hours.map((hour) => {
        const cell = bubbleData.find((d) => d.common_name === species && d.hour === hour)
        return cell?.detection_count || 0
      })
    })

    return {
      data: [
        {
          type: 'heatmap',
          z: matrix,
          x: hours,
          y: speciesOrder,
          colorscale: HEATMAP_COLORSCALE,
          hovertemplate: '%{y}<br>Hour: %{x}:00<br>Detections: %{z}<extra></extra>',
          colorbar: { title: { text: 'Detections' } },
        },
      ],
      layout: {
        title: { text: 'Species Activity by Hour of Day', font: { size: 16 } },
        xaxis: {
          title: { text: 'Hour of Day' },
          tickmode: 'array',
          tickvals: [0, 3, 6, 9, 12, 15, 18, 21],
          ticktext: ['12am', '3am', '6am', '9am', '12pm', '3pm', '6pm', '9pm'],
        },
        yaxis: {
          title: { text: '' },
          tickfont: { size: 10 },
          autorange: 'reversed',
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

    // Get unique species
    const speciesNames = [...new Set(phenologyData.map((d) => d.common_name))]

    // Use all 52 weeks instead of just weeks with data
    const allWeeks = Array.from({ length: 52 }, (_, i) => i + 1)

    // Calculate current week number
    const now = new Date()
    const startOfYear = new Date(now.getFullYear(), 0, 1)
    const dayOfYear = Math.floor((now.getTime() - startOfYear.getTime()) / 86400000) + 1
    const currentWeek = Math.ceil((dayOfYear + startOfYear.getDay()) / 7)

    // Build matrix with all 52 weeks (fill missing with 0)
    const matrix: number[][] = speciesNames.map((species) => {
      return allWeeks.map((week) => {
        const cell = phenologyData.find((d) => d.common_name === species && d.week_number === week)
        return cell?.detection_count || 0
      })
    })

    // Sort species by total detections
    const speciesWithTotals = speciesNames
      .map((name, idx) => ({
        name,
        total: matrix[idx].reduce((a, b) => a + b, 0),
        row: matrix[idx],
      }))
      .sort((a, b) => b.total - a.total)

    // Find the x-axis index for the current week
    const currentWeekIndex = currentWeek - 1 // 0-indexed

    return {
      data: [
        {
          type: 'heatmap',
          z: speciesWithTotals.map((s) => s.row),
          x: allWeeks.map((w) => `W${w}`),
          y: speciesWithTotals.map((s) => s.name),
          colorscale: HEATMAP_COLORSCALE,
          hovertemplate: '%{y}<br>Week %{x}<br>Detections: %{z}<extra></extra>',
          colorbar: { title: { text: 'Detections' } },
        },
      ],
      layout: {
        title: {
          text: `Phenology Heatmap - ${phenologyYear === 0 ? 'Rolling 12 Months' : phenologyYear}`,
          font: { size: 16 },
        },
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
        // Current week indicator line
        shapes: [
          {
            type: 'line',
            x0: currentWeekIndex,
            x1: currentWeekIndex,
            y0: -0.5,
            y1: speciesWithTotals.length - 0.5,
            line: { color: '#FF6B00', width: 3 },
          },
        ],
        annotations: [
          {
            x: currentWeekIndex,
            y: -0.08,
            yref: 'paper',
            text: 'Now',
            showarrow: false,
            font: { color: '#FF6B00', size: 11, weight: 700 },
          },
        ],
      },
    }
  }, [phenologyData, phenologyYear])

  // Prepare confidence scatter data - distinct colors per species
  const scatterChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (scatterData.length === 0) {
      return { data: [], layout: {} }
    }

    // Create a color for each species
    const colors = [
      '#4338CA',
      '#10B981',
      '#F59E0B',
      '#EF4444',
      '#8B5CF6',
      '#EC4899',
      '#14B8A6',
      '#F97316',
      '#6366F1',
      '#84CC16',
      '#06B6D4',
      '#E11D48',
      '#7C3AED',
      '#059669',
      '#D97706',
      '#DC2626',
      '#9333EA',
      '#DB2777',
      '#0D9488',
      '#EA580C',
      '#4F46E5',
      '#65A30D',
      '#0891B2',
      '#BE123C',
      '#6D28D9',
      '#047857',
      '#B45309',
      '#B91C1C',
      '#7E22CE',
      '#BE185D',
    ]

    return {
      data: [
        {
          type: 'scatter',
          mode: 'markers',
          x: scatterData.map((d) => d.total_detections),
          y: scatterData.map((d) => d.avg_confidence),
          text: scatterData.map((d) => d.common_name),
          marker: {
            size: 10,
            color: scatterData.map((_, idx) => colors[idx % colors.length]),
          },
          hovertemplate: '%{text}<br>Detections: %{x:,}<br>Avg Confidence: %{y:.2f}<extra></extra>',
        },
      ],
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
        margin: { l: 60, r: 20, t: 50, b: 50 },
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
    const matrix: number[][] = bins.map((bin) => {
      return hours.map((hour) => {
        const cell = confidenceHourData.find((d) => d.hour === hour && d.confidence_bin === bin)
        return cell?.detection_count || 0
      })
    })

    return {
      data: [
        {
          type: 'heatmap',
          z: matrix,
          x: hours.map((h) => `${h}:00`),
          y: bins,
          colorscale: HEATMAP_COLORSCALE,
          hovertemplate: 'Hour: %{x}<br>Confidence: %{y}<br>Detections: %{z}<extra></extra>',
          colorbar: { title: { text: 'Detections' } },
        },
      ],
      layout: {
        title: { text: 'Detection Confidence by Hour of Day', font: { size: 16 } },
        xaxis: {
          title: { text: 'Hour of Day' },
          tickangle: -45,
          tickfont: { size: 10 },
        },
        yaxis: {
          title: { text: 'Confidence Range', standoff: 15 },
        },
        height: 350,
        margin: { l: 100, r: 80, t: 50, b: 80 },
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
    temporalData.forEach((d) => {
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
      x: data.map((d) => d.date),
      y: data.map((d) => d.detection_count),
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

  // Prepare dawn chorus chart data
  const dawnChorusChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (dawnChorusData.length === 0) {
      return { data: [], layout: {} }
    }

    return {
      data: [
        {
          type: 'bar',
          x: dawnChorusData.map((d) => d.minutes_from_sunrise),
          y: dawnChorusData.map((d) => d.detection_count),
          marker: {
            color: dawnChorusData.map((d) => d.species_count),
            colorscale: 'YlOrRd',
            showscale: true,
            colorbar: { title: { text: 'Species' } },
          },
          hovertemplate:
            '%{x} min from sunrise<br>%{y} detections<br>%{marker.color} species<extra></extra>',
        },
      ],
      layout: {
        title: { text: 'Dawn Chorus Analysis', font: { size: 16 } },
        xaxis: {
          title: { text: 'Minutes from Sunrise' },
          zeroline: true,
          zerolinecolor: '#FF6B00',
          zerolinewidth: 2,
        },
        yaxis: {
          title: { text: 'Detection Count' },
        },
        height: 400,
        margin: { l: 60, r: 80, t: 50, b: 50 },
        shapes: [
          {
            type: 'line',
            x0: 0,
            x1: 0,
            y0: 0,
            y1: 1,
            yref: 'paper',
            line: { color: '#FF6B00', width: 2, dash: 'dash' },
          },
        ],
        annotations: [
          {
            x: 0,
            y: 1.05,
            yref: 'paper',
            text: 'Sunrise',
            showarrow: false,
            font: { color: '#FF6B00', size: 12 },
          },
        ],
      },
    }
  }, [dawnChorusData])

  // Prepare weather impact chart data
  const weatherChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (weatherData.length === 0) {
      return { data: [], layout: {} }
    }

    const labels = weatherData.map((d) => d.temperature_bin || d.condition || 'Unknown')
    const avgDetections = weatherData.map((d) => d.avg_detections)
    const observationCounts = weatherData.map((d) => d.observation_count)

    return {
      data: [
        {
          type: 'bar',
          x: labels,
          y: avgDetections,
          marker: {
            color: avgDetections,
            colorscale: 'Blues',
          },
          text: avgDetections.map(
            (avg, i) => `${avg.toFixed(0)}<br>(${observationCounts[i]} days)`,
          ),
          textposition: 'inside',
          textangle: 0,
          textfont: { color: 'white', size: 10 },
          hovertemplate: '%{x}<br>Avg: %{y:.1f} detections<br>%{customdata} days<extra></extra>',
          customdata: observationCounts,
        },
      ],
      layout: {
        title: { text: 'Average Daily Detections by Temperature Range', font: { size: 14 } },
        xaxis: {
          title: { text: 'Temperature Range' },
          tickangle: -45,
        },
        yaxis: {
          title: { text: 'Average Daily Detections' },
          rangemode: 'tozero',
        },
        height: 450,
        margin: { l: 60, r: 20, t: 50, b: 100 },
        bargap: 0.2,
      },
    }
  }, [weatherData])

  // Prepare precipitation impact chart data
  const precipChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (precipData.length === 0) {
      return { data: [], layout: {} }
    }

    const labels = precipData.map((d) => d.temperature_bin || d.condition || 'Unknown')
    const avgDetections = precipData.map((d) => d.avg_detections)
    const observationCounts = precipData.map((d) => d.observation_count)

    // Color map for precipitation categories
    const colorMap: { [key: string]: string } = {
      'No Precip': '#FCD34D', // Yellow/sunny
      'Light Rain': '#93C5FD', // Light blue
      'Moderate Rain': '#3B82F6', // Medium blue
      'Heavy Rain': '#1D4ED8', // Dark blue
      Snow: '#E5E7EB', // Light gray/white
    }

    return {
      data: [
        {
          type: 'bar',
          x: labels,
          y: avgDetections,
          marker: {
            color: labels.map((l) => colorMap[l] || '#6B7280'),
          },
          text: avgDetections.map(
            (avg, i) => `${avg.toFixed(0)}<br>(${observationCounts[i]} days)`,
          ),
          textposition: 'inside',
          textangle: 0,
          textfont: { color: 'white', size: 10 },
          hovertemplate: '%{x}<br>Avg: %{y:.1f} detections<br>%{customdata} days<extra></extra>',
          customdata: observationCounts,
        },
      ],
      layout: {
        title: { text: 'Average Daily Detections by Precipitation Level', font: { size: 14 } },
        xaxis: {
          title: { text: 'Weather Condition' },
          tickangle: -45,
        },
        yaxis: {
          title: { text: 'Average Daily Detections' },
          rangemode: 'tozero',
        },
        height: 450,
        margin: { l: 60, r: 20, t: 50, b: 100 },
        bargap: 0.2,
      },
    }
  }, [precipData])

  // Prepare co-occurrence matrix data
  const coOccurrenceChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (coOccurrenceData.length === 0) {
      return { data: [], layout: {} }
    }

    // Get unique species names
    const speciesNames = [...new Set(coOccurrenceData.map((d) => d.species_1))]

    // Build matrix
    const matrix: number[][] = speciesNames.map((sp1) => {
      return speciesNames.map((sp2) => {
        const cell = coOccurrenceData.find((d) => d.species_1 === sp1 && d.species_2 === sp2)
        return cell?.jaccard_index || 0
      })
    })

    return {
      data: [
        {
          type: 'heatmap',
          z: matrix,
          x: speciesNames,
          y: speciesNames,
          colorscale: [
            [0, '#FFFFFF'],
            [0.25, '#E0E7FF'],
            [0.5, '#818CF8'],
            [0.75, '#4338CA'],
            [1, '#1E1B4B'],
          ],
          hovertemplate: '%{y} & %{x}<br>Jaccard Index: %{z:.3f}<extra></extra>',
          colorbar: { title: { text: 'Jaccard' } },
        },
      ],
      layout: {
        title: { text: 'Species Co-occurrence Matrix', font: { size: 16 } },
        xaxis: {
          tickangle: -45,
          tickfont: { size: 9 },
        },
        yaxis: {
          tickfont: { size: 9 },
        },
        height: Math.max(500, speciesNames.length * 25 + 150),
        margin: { l: 120, r: 80, t: 50, b: 120 },
      },
    }
  }, [coOccurrenceData])
  // Prepare mirrored probability density plot for seasonality
  const seasonalityChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (temporalData.length === 0) {
      return { data: [], layout: {} }
    }

    // Group temporal data by species
    const speciesGroups = new Map<string, TemporalDistribution[]>()
    temporalData.forEach((d) => {
      if (!speciesGroups.has(d.common_name)) {
        speciesGroups.set(d.common_name, [])
      }
      speciesGroups.get(d.common_name)!.push(d)
    })

    // Sort species by total detections (most detected at top)
    const speciesOrdered = Array.from(speciesGroups.entries())
      .map(([name, data]) => ({
        name,
        data,
        total: data.reduce((sum, d) => sum + d.detection_count, 0),
      }))
      .sort((a, b) => b.total - a.total)

    if (speciesOrdered.length === 0) {
      return { data: [], layout: {} }
    }

    // Determine date range
    const allDates = temporalData.map((d) => new Date(d.date).getTime())
    const minDate = Math.min(...allDates)
    const maxDate = Math.max(...allDates)
    const dateRange = maxDate - minDate
    const bandwidth = dateRange / 30 // Bandwidth: ~1 month

    // Create grid of dates for KDE
    const gridSize = 100
    const gridDates: number[] = []
    for (let i = 0; i < gridSize; i++) {
      gridDates.push(minDate + (i / (gridSize - 1)) * dateRange)
    }
    const gridDatesStr = gridDates.map((d) => new Date(d).toISOString().split('T')[0])

    // Color palette for species
    const colors = [
      '#4338CA',
      '#10B981',
      '#F59E0B',
      '#EF4444',
      '#8B5CF6',
      '#EC4899',
      '#14B8A6',
      '#F97316',
      '#6366F1',
      '#84CC16',
      '#06B6D4',
      '#E11D48',
      '#7C3AED',
      '#059669',
      '#D97706',
    ]

    const traces: Data[] = []
    const verticalSpacing = 1 // Spacing between species

    speciesOrdered.forEach((species, idx) => {
      // Expand dates by detection count (each detection contributes to the density)
      const expandedDates: number[] = []
      species.data.forEach((d) => {
        const dateMs = new Date(d.date).getTime()
        for (let i = 0; i < Math.min(d.detection_count, 100); i++) {
          expandedDates.push(dateMs)
        }
      })

      if (expandedDates.length === 0) return

      // Compute KDE
      const density = computeKDE(expandedDates, bandwidth, gridDates)
      const maxDensity = Math.max(...density)

      // Normalize density to fit within spacing (max height = 0.4 of spacing)
      const normalizedDensity = density.map((d) => (d / maxDensity) * 0.4)
      const yBaseline = idx * verticalSpacing
      const color = colors[idx % colors.length]

      // Lower trace (mirrored - negative) - must come first as base for fill
      traces.push({
        type: 'scatter',
        mode: 'lines',
        x: gridDatesStr,
        y: normalizedDensity.map((d) => yBaseline - d),
        line: { color, width: 1 },
        name: species.name,
        showlegend: false,
        hovertemplate: `${species.name}<br>%{x}<extra></extra>`,
      })

      // Upper trace (positive) - fills down to previous trace (lower)
      traces.push({
        type: 'scatter',
        mode: 'lines',
        x: gridDatesStr,
        y: normalizedDensity.map((d) => yBaseline + d),
        line: { color, width: 1 },
        fill: 'tonexty',
        fillcolor: `${color}40`,
        showlegend: false,
        hoverinfo: 'skip',
      })
    })

    return {
      data: traces,
      layout: {
        title: { text: 'Species Detection Density (Mirrored)', font: { size: 16 } },
        xaxis: {
          title: { text: 'Date' },
          type: 'date',
        },
        yaxis: {
          tickmode: 'array',
          tickvals: speciesOrdered.map((_, idx) => idx * verticalSpacing),
          ticktext: speciesOrdered.map((s) => s.name),
          tickfont: { size: 10 },
          showgrid: false,
          zeroline: false,
          autorange: 'reversed', // Most detected at top
        },
        height: Math.max(400, speciesOrdered.length * 60 + 100),
        margin: { l: 150, r: 20, t: 50, b: 50 },
        showlegend: false,
        hovermode: 'closest',
      },
    }
  }, [temporalData])

  const handleStationToggle = (stationId: number) => {
    setSelectedStations((prev) =>
      prev.includes(stationId) ? prev.filter((id) => id !== stationId) : [...prev, stationId],
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
          {/* Station Filter — group of buttons, not a form control */}
          <div>
            <span className="block text-sm font-medium text-gray-700 mb-1">Stations</span>
            <div className="flex flex-wrap gap-2">
              {stations.map((station) => (
                <button type="button"
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
                <button type="button"
                  onClick={() => setSelectedStations([])}
                  className="px-3 py-1 text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Heatmap Species Limit */}
          <div>
            <label htmlFor="analytics-species-limit" className="block text-sm font-medium text-gray-700 mb-1">
              Species Limit (Heatmap)
            </label>
            <select
              id="analytics-species-limit"
              value={bubbleLimit}
              onChange={(e) => setBubbleLimit(Number(e.target.value))}
              className="px-3 py-1 border rounded text-sm"
            >
              <option value={20}>Top 20</option>
              <option value={30}>Top 30</option>
              <option value={50}>Top 50</option>
              <option value={100}>Top 100</option>
              <option value={9999}>All</option>
            </select>
          </div>

          {/* Phenology Period */}
          <div>
            <label htmlFor="analytics-phenology-period" className="block text-sm font-medium text-gray-700 mb-1">Phenology Period</label>
            <select
              id="analytics-phenology-period"
              value={phenologyYear}
              onChange={(e) => setPhenologyYear(Number(e.target.value))}
              className="px-3 py-1 border rounded text-sm"
            >
              <option value={0}>Rolling 12 Months</option>
              {[2024, 2025, 2026].map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
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
            Weekly detection intensity throughout the year. Reveals seasonal patterns and migration
            timing.
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

      {/* Dawn Chorus & Weather Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Environmental Factors</h2>

        {/* Dawn Chorus - Full Width */}
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-muted-foreground mb-2">
            Detection activity relative to sunrise. The dawn chorus phenomenon peaks just before and
            after sunrise.
          </p>
          {dawnChorusData.length > 0 ? (
            <Plot
              data={dawnChorusChartData.data}
              layout={dawnChorusChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              No sunrise data available
            </div>
          )}
        </div>

        {/* Weather Charts Side by Side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Temperature Impact */}
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-muted-foreground mb-2">
              Average daily detections by temperature range.
            </p>
            {weatherData.length > 0 ? (
              <Plot
                data={weatherChartData.data}
                layout={weatherChartData.layout}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%' }}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No weather data available
              </div>
            )}
          </div>

          {/* Precipitation Impact */}
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-muted-foreground mb-2">
              Average daily detections by precipitation level.
            </p>
            {precipData.length > 0 ? (
              <Plot
                data={precipChartData.data}
                layout={precipChartData.layout}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%' }}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No precipitation data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Species Relationships Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Species Relationships</h2>

        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-muted-foreground mb-2">
            Species co-occurrence based on Jaccard similarity index. Higher values (darker) indicate
            species frequently detected on the same days.
          </p>
          {coOccurrenceData.length > 0 ? (
            <Plot
              data={coOccurrenceChartData.data}
              layout={coOccurrenceChartData.layout}
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

      {/* Seasonality & Champions Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Seasonality & Champions</h2>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Species Detection Density */}
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-muted-foreground mb-2">
              Mirrored probability density plot showing detection patterns over time. Species
              ordered by total detections (highest at top). Wider areas indicate more frequent
              detections.
            </p>
            {temporalData.length > 0 ? (
              <div className="overflow-y-auto max-h-[600px]">
                <Plot
                  data={seasonalityChartData.data}
                  layout={seasonalityChartData.layout}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%' }}
                />
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            )}
          </div>

          {/* Monthly Champions Table */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold mb-2">
              Monthly Detection Champions (Rolling 12 Months)
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              The most detected species each month over the past 12 months. Shows which birds
              dominate each season.
            </p>
            {monthlyChampionsData.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Month
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Top Species
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Detections
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        % of Month
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {monthlyChampionsData.map((champion, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                          {champion.month_name}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                          {champion.common_name}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                          {champion.detection_count.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 text-right">
                          {champion.percentage_of_month.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="h-32 flex items-center justify-center text-muted-foreground">
                No data available for {phenologyYear}
              </div>
            )}
          </div>
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

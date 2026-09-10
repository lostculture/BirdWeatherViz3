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
import ChartPanel from '../components/ChartPanel'
import { useAsyncData } from '../hooks/useAsyncData'
import {
  buildSeasonalityAxes,
  RIDGE_HALF_HEIGHT,
  seasonalityHeight,
  seasonalityPosition,
} from './seasonalityLayout'
import type {
  CoOccurrenceCell,
  ConfidenceByHour,
  ConfidenceScatterPoint,
  DawnChorusPoint,
  DuskChorusPoint,
  MonthlyChampion,
  PhenologyCell,
  RollupStatus,
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

// Build the hover text listing the species behind one chorus bar. Plotly
// renders <br> inside a hovertemplate, so the list is a preformatted string
// passed through customdata.
const chorusHoverText = (
  species: Array<{ common_name: string; detection_count: number }>,
): string => {
  if (species.length === 0) return ''
  const width = Math.max(...species.map((sp) => sp.detection_count.toLocaleString().length))
  const lines = species.map(
    (sp) => `${sp.detection_count.toLocaleString().padStart(width)} · ${sp.common_name}`,
  )
  return `<br><br><b>Top species</b><br>${lines.join('<br>')}`
}

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
  const [stations, setStations] = useState<StationResponse[]>([])

  // UI states
  const [selectedStations, setSelectedStations] = useState<number[]>([])
  const [bubbleLimit, setBubbleLimit] = useState(30)
  const [phenologyYear, setPhenologyYear] = useState(0) // 0 = Rolling 12 months (default)
  const [rollups, setRollups] = useState<RollupStatus | null>(null)
  // 'date' pooling saturates at 1.00 for every common species once more than a
  // couple of stations report, so same-station-same-hour is the default.
  const [coOccurrenceGrain, setCoOccurrenceGrain] = useState<'hour' | 'day' | 'date'>('hour')

  const stationIds = selectedStations.length > 0 ? selectedStations.join(',') : undefined

  useEffect(() => {
    loadStations()
  }, [])

  const loadStations = async () => {
    try {
      const stationList = await stationsApi.getAll()
      setStations(stationList)
    } catch (err) {
      console.error('Failed to load stations:', err)
    }
  }

  // Poll the rollup builder while it is catching up, so a first build on a
  // large database explains itself instead of showing empty charts.
  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    const poll = async () => {
      try {
        const status = await analyticsApi.getRollupStatus()
        if (cancelled) return
        setRollups(status)
        if (status.building || status.detections_pending > 0) {
          timer = setTimeout(poll, 5000)
        }
      } catch (err) {
        // Older backends have no rollup endpoint; the charts still work.
        console.debug('Rollup status unavailable:', err)
      }
    }

    poll()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [])

  // Each chart loads on its own request. Previously all ten went out in a
  // single Promise.all, so one slow query rejected the lot and the page showed
  // nothing but "Error: timeout of 30000ms exceeded".
  const bubble = useAsyncData<SpeciesHourBubble[]>(
    () =>
      analyticsApi.getSpeciesHourBubble({
        limit: bubbleLimit >= 9999 ? 500 : bubbleLimit, // Cap at 500 for "All"
        months: 3,
        station_ids: stationIds,
      }),
    [stationIds, bubbleLimit],
    [],
  )

  const phenology = useAsyncData<PhenologyCell[]>(
    () =>
      analyticsApi.getPhenology({
        year: phenologyYear,
        station_ids: stationIds,
        limit: 40,
      }),
    [stationIds, phenologyYear],
    [],
  )

  const scatter = useAsyncData<ConfidenceScatterPoint[]>(
    () => analyticsApi.getConfidenceScatter({ station_ids: stationIds, min_detections: 10 }),
    [stationIds],
    [],
  )

  const confidenceHour = useAsyncData<ConfidenceByHour[]>(
    () => analyticsApi.getConfidenceByHour({ station_ids: stationIds, months: 6 }),
    [stationIds],
    [],
  )

  const temporal = useAsyncData<TemporalDistribution[]>(
    () =>
      analyticsApi.getTemporalDistribution({
        station_ids: stationIds,
        months: 6,
        limit: 200, // All species for density plot
      }),
    [stationIds],
    [],
  )

  const seasonality = useAsyncData<TemporalDistribution[]>(
    () =>
      analyticsApi.getTemporalDistribution({
        station_ids: stationIds,
        limit: 200,
        mode: 'calendar',
      }),
    [stationIds],
    [],
  )

  const dawnChorus = useAsyncData<DawnChorusPoint[]>(
    () => analyticsApi.getDawnChorus({ station_ids: stationIds, months: 6 }),
    [stationIds],
    [],
  )

  const duskChorus = useAsyncData<DuskChorusPoint[]>(
    () => analyticsApi.getDuskChorus({ station_ids: stationIds, months: 6 }),
    [stationIds],
    [],
  )

  const weather = useAsyncData<WeatherImpact[]>(
    () =>
      analyticsApi.getWeatherImpact({
        station_ids: stationIds,
        months: 6,
        analysis_type: 'temperature',
      }),
    [stationIds],
    [],
  )

  const precip = useAsyncData<WeatherImpact[]>(
    () =>
      analyticsApi.getWeatherImpact({
        station_ids: stationIds,
        months: 6,
        analysis_type: 'precipitation',
      }),
    [stationIds],
    [],
  )

  const coOccurrence = useAsyncData<CoOccurrenceCell[]>(
    () =>
      analyticsApi.getCoOccurrence({
        station_ids: stationIds,
        months: 6,
        limit: 15,
        granularity: coOccurrenceGrain,
      }),
    [stationIds, coOccurrenceGrain],
    [],
  )

  const champions = useAsyncData<MonthlyChampion[]>(
    () => analyticsApi.getMonthlyChampions({ station_ids: stationIds, year: phenologyYear }),
    [stationIds, phenologyYear],
    [],
  )

  const bubbleData = bubble.data
  const phenologyData = phenology.data
  const scatterData = scatter.data
  const confidenceHourData = confidenceHour.data
  const temporalData = temporal.data
  const seasonalityData = seasonality.data
  const dawnChorusData = dawnChorus.data
  const duskChorusData = duskChorus.data
  const weatherData = weather.data
  const precipData = precip.data
  const coOccurrenceData = coOccurrence.data
  const monthlyChampionsData = champions.data

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
          customdata: dawnChorusData.map((d) => chorusHoverText(d.top_species ?? [])),
          marker: {
            color: dawnChorusData.map((d) => d.species_count),
            colorscale: 'YlOrRd',
            showscale: true,
            colorbar: { title: { text: 'Species' } },
          },
          hovertemplate:
            '%{x} min from sunrise<br>%{y} detections<br>%{marker.color} species%{customdata}<extra></extra>',
        },
      ],
      layout: {
        title: { text: 'Dawn Chorus Analysis', font: { size: 16 } },
        hoverlabel: { align: 'left', namelength: -1 },
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

  // Dusk chorus — the sunset counterpart to the dawn chorus. Bat emergence and
  // the start of owl activity both cluster in the half hour after sunset, so
  // this is the chart to read for a station running a bat detector.
  const duskChorusChartData = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (duskChorusData.length === 0) {
      return { data: [], layout: {} }
    }

    return {
      data: [
        {
          type: 'bar',
          x: duskChorusData.map((d) => d.minutes_from_sunset),
          y: duskChorusData.map((d) => d.detection_count),
          customdata: duskChorusData.map((d) => chorusHoverText(d.top_species ?? [])),
          marker: {
            color: duskChorusData.map((d) => d.species_count),
            colorscale: 'Purples',
            showscale: true,
            colorbar: { title: { text: 'Species' } },
          },
          hovertemplate:
            '%{x} min from sunset<br>%{y} detections<br>%{marker.color} species%{customdata}<extra></extra>',
        },
      ],
      layout: {
        title: { text: 'Dusk Chorus Analysis', font: { size: 16 } },
        hoverlabel: { align: 'left', namelength: -1 },
        xaxis: {
          title: { text: 'Minutes from Sunset' },
          zeroline: true,
          zerolinecolor: '#7C3AED',
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
            line: { color: '#7C3AED', width: 2, dash: 'dash' },
          },
        ],
        annotations: [
          {
            x: 0,
            y: 1.05,
            yref: 'paper',
            text: 'Sunset',
            showarrow: false,
            font: { color: '#7C3AED', size: 12 },
          },
        ],
      },
    }
  }, [duskChorusData])

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
  // Ridgeline ("joyplot") of detection density per species.
  //
  // Species are laid out in rows of SEASONALITY_ROW_SIZE stacked subplots, each
  // with its own x-axis, so scrolling a tall chart always keeps a date axis in
  // view. A single tall subplot put the only axis at the very bottom, hundreds
  // of pixels below whatever you were looking at.
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

    const layout: Partial<Layout> & Record<string, unknown> = {
      height: seasonalityHeight(speciesOrdered.length),
      margin: { l: 150, r: 20, t: 40, b: 20 },
      showlegend: false,
      hovermode: 'closest',
      title: { text: 'Species Detection Density (Mirrored)', font: { size: 16 } },
    }

    speciesOrdered.forEach((species, idx) => {
      const { positionInRow, axisSuffix } = seasonalityPosition(idx)

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

      const normalizedDensity = density.map((d) => (d / maxDensity) * RIDGE_HALF_HEIGHT)
      const yBaseline = positionInRow
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
        xaxis: `x${axisSuffix}`,
        yaxis: `y${axisSuffix}`,
        hovertemplate: `${species.name}<br>%{x}<extra></extra>`,
      } as Data)

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
        xaxis: `x${axisSuffix}`,
        yaxis: `y${axisSuffix}`,
        hoverinfo: 'skip',
      } as Data)
    })

    const axes = buildSeasonalityAxes(
      speciesOrdered.map((sp) => sp.name),
      [gridDatesStr[0], gridDatesStr[gridDatesStr.length - 1]],
    )
    axes.forEach(({ suffix, xaxis, yaxis }) => {
      layout[`xaxis${suffix}`] = xaxis
      layout[`yaxis${suffix}`] = yaxis
    })

    return { data: traces, layout: layout as Partial<Layout> }
  }, [seasonalityData])


  const handleStationToggle = (stationId: number) => {
    setSelectedStations((prev) =>
      prev.includes(stationId) ? prev.filter((id) => id !== stationId) : [...prev, stationId],
    )
  }

  // Every panel owns its loading and error state, so there is no page-wide
  // gate any more: one slow or failing chart no longer blanks the page.
  const anyLoading = [
    bubble,
    phenology,
    scatter,
    confidenceHour,
    temporal,
    dawnChorus,
    duskChorus,
    weather,
    precip,
    coOccurrence,
    champions,
    seasonality,
  ].some((panel) => panel.loading)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Advanced Analytics</h1>
        <p className="text-muted-foreground mt-2">
          Deep analysis of detection patterns, confidence, and temporal trends
        </p>
      </div>

      {/* Rollup build progress. The charts read pre-aggregated summaries; while
          a first build catches up they show a growing subset rather than
          nothing, so say so instead of leaving the user guessing. */}
      {rollups && (rollups.building || rollups.detections_pending > 0) && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-900 flex items-center gap-3">
          <span className="inline-block w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span>
            Building analytics summaries —{' '}
            <strong>{rollups.detections_pending.toLocaleString()}</strong> detections still to
            process. Charts fill in as this completes.
          </span>
        </div>
      )}
      {rollups?.detection.status === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-900">
          Analytics summaries failed to build: {rollups.detection.message}
        </div>
      )}

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
        <ChartPanel
          description="Bubble size and color indicate detection count. Shows when each species is most active."
          loading={bubble.loading}
          error={bubble.error}
          isEmpty={bubbleData.length === 0}
          onRetry={bubble.reload}
        >
          <Plot
            data={bubbleChartData.data}
            layout={bubbleChartData.layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </ChartPanel>

        {/* Phenology Heatmap */}
        <ChartPanel
          description="Weekly detection intensity throughout the year. Reveals seasonal patterns and migration timing."
          loading={phenology.loading}
          error={phenology.error}
          isEmpty={phenologyData.length === 0}
          emptyMessage={`No data available for ${phenologyYear || 'the last 12 months'}`}
          onRetry={phenology.reload}
        >
          <Plot
            data={phenologyChartData.data}
            layout={phenologyChartData.layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </ChartPanel>
      </div>

      {/* Data Quality Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Data Quality Analysis</h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Confidence Scatter */}
          <ChartPanel
            description="Species with high detections and high confidence are the most reliably identified."
            loading={scatter.loading}
            error={scatter.error}
            isEmpty={scatterData.length === 0}
            onRetry={scatter.reload}
          >
            <Plot
              data={scatterChartData.data}
              layout={scatterChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </ChartPanel>

          {/* Confidence by Hour */}
          <ChartPanel
            description="Shows how detection confidence varies throughout the day."
            loading={confidenceHour.loading}
            error={confidenceHour.error}
            isEmpty={confidenceHourData.length === 0}
            onRetry={confidenceHour.reload}
          >
            <Plot
              data={confidenceHourChartData.data}
              layout={confidenceHourChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </ChartPanel>
        </div>
      </div>

      {/* Temporal Distribution Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Temporal Distribution</h2>

        <ChartPanel
          description="Daily detection patterns for top species over the past 6 months."
          loading={temporal.loading}
          error={temporal.error}
          isEmpty={temporalData.length === 0}
          onRetry={temporal.reload}
        >
          <Plot
            data={temporalChartData.data}
            layout={temporalChartData.layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </ChartPanel>
      </div>

      {/* Dawn Chorus & Weather Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Environmental Factors</h2>

        {/* Dawn and dusk chorus, side by side so the two ends of the day can
            be compared directly. */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <ChartPanel
            description="Detection activity relative to sunrise. The dawn chorus peaks just before and after sunrise."
            loading={dawnChorus.loading}
            error={dawnChorus.error}
            isEmpty={dawnChorusData.length === 0}
            emptyMessage="No sunrise data available — sync weather to populate sunrise times"
            onRetry={dawnChorus.reload}
          >
            <Plot
              data={dawnChorusChartData.data}
              layout={dawnChorusChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </ChartPanel>

          <ChartPanel
            description="Detection activity relative to sunset. Bats emerging and owls starting up both show in the half hour after sunset."
            loading={duskChorus.loading}
            error={duskChorus.error}
            isEmpty={duskChorusData.length === 0}
            emptyMessage="No sunset data available — sync weather to populate sunset times"
            onRetry={duskChorus.reload}
          >
            <Plot
              data={duskChorusChartData.data}
              layout={duskChorusChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </ChartPanel>
        </div>

        {/* Weather Charts Side by Side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Temperature Impact */}
          <ChartPanel
            description="Average daily detections by temperature range."
            loading={weather.loading}
            error={weather.error}
            isEmpty={weatherData.length === 0}
            emptyMessage="No weather data available"
            onRetry={weather.reload}
          >
            <Plot
              data={weatherChartData.data}
              layout={weatherChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </ChartPanel>

          {/* Precipitation Impact */}
          <ChartPanel
            description="Average daily detections by precipitation level."
            loading={precip.loading}
            error={precip.error}
            isEmpty={precipData.length === 0}
            emptyMessage="No precipitation data available"
            onRetry={precip.reload}
          >
            <Plot
              data={precipChartData.data}
              layout={precipChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </ChartPanel>
        </div>
      </div>

      {/* Species Relationships Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Species Relationships</h2>

        <div className="flex items-center gap-2 flex-wrap">
          <label htmlFor="cooccurrence-grain" className="text-sm font-medium text-gray-700">
            Count species as together when detected in the same
          </label>
          <select
            id="cooccurrence-grain"
            value={coOccurrenceGrain}
            onChange={(e) => setCoOccurrenceGrain(e.target.value as 'hour' | 'day' | 'date')}
            className="px-3 py-1 border rounded text-sm"
          >
            <option value="hour">hour, at the same station</option>
            <option value="day">day, at the same station</option>
            <option value="date">day, anywhere</option>
          </select>
        </div>

        <ChartPanel
          description="Species co-occurrence based on the Jaccard similarity index; darker means more often detected together. Pooling by day across every station saturates at 1.00 for common species, which is why the default is the same station in the same hour."
          loading={coOccurrence.loading}
          error={coOccurrence.error}
          isEmpty={coOccurrenceData.length === 0}
          onRetry={coOccurrence.reload}
        >
          <Plot
            data={coOccurrenceChartData.data}
            layout={coOccurrenceChartData.layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </ChartPanel>
      </div>

      {/* Seasonality & Champions Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Seasonality & Champions</h2>

        {/* Species Detection Density */}
        <ChartPanel
          description="Every year of history folded onto one calendar year, so the shape reads as seasonality rather than as recent history. Species ordered by total detections (highest at top); wider areas mean more frequent detections. A month axis repeats every three species so one stays in view while scrolling."
          loading={seasonality.loading}
          error={seasonality.error}
          isEmpty={seasonalityData.length === 0}
          onRetry={seasonality.reload}
        >
          <div className="overflow-y-auto max-h-[600px]">
            <Plot
              data={seasonalityChartData.data}
              layout={seasonalityChartData.layout}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </div>
        </ChartPanel>

        <div className="grid grid-cols-1 gap-4">
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
                No data available for {phenologyYear || 'the last 12 months'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Loading indicator for refreshes */}
      {anyLoading && (
        <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg px-4 py-2 text-sm flex items-center gap-2">
          <span className="inline-block w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
          Refreshing data…
        </div>
      )}
    </div>
  )
}

export default AdvancedAnalytics

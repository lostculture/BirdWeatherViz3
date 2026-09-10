/**
 * Nocturnal Page
 * Bats, owls, nightjars and allies — the species a station picks up after dark.
 *
 * Group membership comes from eBird order/family taxonomy on the species
 * record, so nothing needs configuring per station beyond loading the taxonomy
 * once. Where a database has no taxonomy at all the page says so rather than
 * showing empty charts.
 *
 * Version: 1.0.0
 */

import type { Data, Layout } from 'plotly.js'
import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Plot from 'react-plotly.js'
import { nocturnalApi, stationsApi } from '../api'
import type { DawnChorusPoint, DuskChorusPoint } from '../api/analytics'
import type {
  NocturnalGroupKey,
  NocturnalHourPoint,
  NocturnalNightPoint,
  NocturnalSummary,
} from '../api/nocturnal'
import ChartPanel from '../components/ChartPanel'
import { useAsyncData } from '../hooks/useAsyncData'
import type { StationResponse } from '../types/api'

const ALL_GROUPS: NocturnalGroupKey[] = ['bats', 'owls', 'nightjars']

// One colour per group, reused across every chart on the page so a colour
// always means the same group.
const GROUP_COLORS: Record<string, string> = {
  bats: '#7C3AED',
  owls: '#0891B2',
  nightjars: '#D97706',
  other: '#64748B',
}

// Species list behind one chorus bar. Plotly renders <br> in a hovertemplate,
// so the list travels as a preformatted string in customdata.
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

const EMPTY_SUMMARY: NocturnalSummary = {
  taxonomy_available: true,
  groups: [],
  species: [],
}

const Nocturnal: React.FC = () => {
  const [stations, setStations] = useState<StationResponse[]>([])
  const [selectedStations, setSelectedStations] = useState<number[]>([])
  const [selectedGroups, setSelectedGroups] = useState<NocturnalGroupKey[]>(ALL_GROUPS)
  const [months, setMonths] = useState(12)

  const stationIds = selectedStations.length > 0 ? selectedStations.join(',') : undefined
  // Sending every group is the same as sending none; omit it so the request
  // URL stays stable and cacheable in the default case.
  const groupsParam =
    selectedGroups.length === ALL_GROUPS.length ? undefined : selectedGroups.join(',')

  useEffect(() => {
    stationsApi
      .getAll()
      .then(setStations)
      .catch((err) => console.error('Failed to load stations:', err))
  }, [])

  const params = { groups: groupsParam, station_ids: stationIds, months }

  const summary = useAsyncData<NocturnalSummary>(
    () => nocturnalApi.getSummary(params),
    [groupsParam, stationIds, months],
    EMPTY_SUMMARY,
  )

  const dusk = useAsyncData<DuskChorusPoint[]>(
    () => nocturnalApi.getDuskChorus(params),
    [groupsParam, stationIds, months],
    [],
  )

  const dawn = useAsyncData<DawnChorusPoint[]>(
    () => nocturnalApi.getDawnChorus(params),
    [groupsParam, stationIds, months],
    [],
  )

  const hourly = useAsyncData<NocturnalHourPoint[]>(
    () => nocturnalApi.getHourly(params),
    [groupsParam, stationIds, months],
    [],
  )

  const nightly = useAsyncData<NocturnalNightPoint[]>(
    () => nocturnalApi.getNightly(params),
    [groupsParam, stationIds, months],
    [],
  )

  const toggleGroup = (group: NocturnalGroupKey) => {
    setSelectedGroups((prev) => {
      const next = prev.includes(group) ? prev.filter((g) => g !== group) : [...prev, group]
      // Never leave every group off — that would just empty the page.
      return next.length === 0 ? ALL_GROUPS : next
    })
  }

  const toggleStation = (stationId: number) => {
    setSelectedStations((prev) =>
      prev.includes(stationId) ? prev.filter((id) => id !== stationId) : [...prev, stationId],
    )
  }

  /** Sunset- and sunrise-relative activity, overlaid on one axis. */
  const chorusChart = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    const traces: Data[] = []

    if (dusk.data.length > 0) {
      traces.push({
        type: 'bar',
        name: 'From sunset',
        x: dusk.data.map((d) => d.minutes_from_sunset),
        y: dusk.data.map((d) => d.detection_count),
        customdata: dusk.data.map((d) => chorusHoverText(d.top_species ?? [])),
        marker: { color: '#7C3AED' },
        hovertemplate: '%{x} min from sunset<br>%{y} detections%{customdata}<extra></extra>',
      })
    }

    if (dawn.data.length > 0) {
      traces.push({
        type: 'bar',
        name: 'From sunrise',
        x: dawn.data.map((d) => d.minutes_from_sunrise),
        y: dawn.data.map((d) => d.detection_count),
        customdata: dawn.data.map((d) => chorusHoverText(d.top_species ?? [])),
        marker: { color: '#F59E0B' },
        visible: 'legendonly',
        hovertemplate: '%{x} min from sunrise<br>%{y} detections%{customdata}<extra></extra>',
      })
    }

    return {
      data: traces,
      layout: {
        title: { text: 'Night Shift — activity around sunset', font: { size: 16 } },
        hoverlabel: { align: 'left', namelength: -1 },
        xaxis: {
          title: { text: 'Minutes from the solar event' },
          zeroline: true,
          zerolinecolor: '#7C3AED',
          zerolinewidth: 2,
        },
        yaxis: { title: { text: 'Detection Count' } },
        height: 420,
        margin: { l: 60, r: 20, t: 50, b: 50 },
        legend: { orientation: 'h', y: -0.2 },
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
      },
    }
  }, [dusk.data, dawn.data])

  /** Hour-of-day heatmap: species down the side, midday-centred night hours across. */
  const hourlyChart = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (hourly.data.length === 0) return { data: [], layout: {} }

    // Order the x axis noon -> noon so a night reads left to right without
    // being split across the two ends of the axis.
    const hourOrder = Array.from({ length: 24 }, (_, i) => (i + 12) % 24)

    const totals = new Map<string, number>()
    const bySpecies = new Map<string, Map<number, number>>()
    hourly.data.forEach((row) => {
      totals.set(row.common_name, (totals.get(row.common_name) ?? 0) + row.detection_count)
      if (!bySpecies.has(row.common_name)) bySpecies.set(row.common_name, new Map())
      const hours = bySpecies.get(row.common_name)!
      hours.set(row.hour, (hours.get(row.hour) ?? 0) + row.detection_count)
    })

    const speciesNames = Array.from(totals.entries())
      .sort((a, b) => a[1] - b[1]) // Plotly draws the first row at the bottom
      .map(([name]) => name)

    const z = speciesNames.map((name) => {
      const hours = bySpecies.get(name)!
      const row = hourOrder.map((hour) => hours.get(hour) ?? 0)
      // Normalise per species so a quiet owl is still readable next to a
      // colony of bats.
      const max = Math.max(...row, 1)
      return row.map((value) => value / max)
    })

    const counts = speciesNames.map((name) => {
      const hours = bySpecies.get(name)!
      return hourOrder.map((hour) => hours.get(hour) ?? 0)
    })

    return {
      data: [
        {
          type: 'heatmap',
          z,
          customdata: counts,
          x: hourOrder.map((h) => `${String(h).padStart(2, '0')}:00`),
          y: speciesNames,
          colorscale: 'Purples',
          showscale: false,
          hovertemplate: '%{y}<br>%{x}<br>%{customdata} detections<extra></extra>',
        },
      ],
      layout: {
        title: { text: 'Activity by hour (each species scaled to its own peak)', font: { size: 16 } },
        xaxis: { title: { text: 'Hour of day (noon to noon)' }, tickangle: -45 },
        yaxis: { automargin: true, tickfont: { size: 10 } },
        height: Math.max(300, speciesNames.length * 28 + 140),
        margin: { l: 20, r: 20, t: 50, b: 80 },
      },
    }
  }, [hourly.data])

  /** Detections per night, one line per group. */
  const nightlyChart = useMemo((): { data: Data[]; layout: Partial<Layout> } => {
    if (nightly.data.length === 0) return { data: [], layout: {} }

    const byGroup = new Map<string, NocturnalNightPoint[]>()
    nightly.data.forEach((row) => {
      if (!byGroup.has(row.group)) byGroup.set(row.group, [])
      byGroup.get(row.group)!.push(row)
    })

    const traces: Data[] = Array.from(byGroup.entries()).map(([group, rows]) => ({
      type: 'scatter',
      mode: 'lines',
      name: group.charAt(0).toUpperCase() + group.slice(1),
      x: rows.map((r) => r.date),
      y: rows.map((r) => r.detection_count),
      line: { color: GROUP_COLORS[group] ?? GROUP_COLORS.other, width: 1.5 },
      hovertemplate: '%{x}<br>%{y} detections<extra></extra>',
    }))

    return {
      data: traces,
      layout: {
        title: { text: 'Detections per night', font: { size: 16 } },
        xaxis: { title: { text: 'Night' }, type: 'date' },
        yaxis: { title: { text: 'Detections' } },
        height: 380,
        margin: { l: 60, r: 20, t: 50, b: 50 },
        legend: { orientation: 'h', y: -0.2 },
      },
    }
  }, [nightly.data])

  const { taxonomy_available: taxonomyAvailable, groups, species } = summary.data
  const noTaxonomy = !summary.loading && !taxonomyAvailable

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Nocturnal</h1>
        <p className="text-muted-foreground mt-2">
          Bats, owls and nightjars — what the station hears after dark. Species are grouped by
          taxonomy, so a station running a bat detector gets its Chiroptera records separated from
          the birds automatically.
        </p>
      </div>

      {/* Taxonomy is what makes this page work; say so plainly when it's absent. */}
      {noTaxonomy && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-900">
          No taxonomy is loaded, so species cannot be sorted into bats, owls and nightjars. Upload
          the eBird taxonomy under{' '}
          <Link to="/config" className="underline hover:no-underline font-medium">
            Config → Taxonomy
          </Link>{' '}
          and this page will populate itself.
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-6 items-start">
          <div>
            <span className="block text-sm font-medium text-gray-700 mb-1">Groups</span>
            <div className="flex flex-wrap gap-2">
              {ALL_GROUPS.map((group) => (
                <button
                  type="button"
                  key={group}
                  onClick={() => toggleGroup(group)}
                  className={`px-3 py-1 text-sm rounded-full transition-colors capitalize ${
                    selectedGroups.includes(group)
                      ? 'text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  style={
                    selectedGroups.includes(group)
                      ? { backgroundColor: GROUP_COLORS[group] }
                      : undefined
                  }
                >
                  {group}
                </button>
              ))}
            </div>
          </div>

          {stations.length > 1 && (
            <div>
              <span className="block text-sm font-medium text-gray-700 mb-1">Stations</span>
              <div className="flex flex-wrap gap-2">
                {stations.map((station) => (
                  <button
                    type="button"
                    key={station.id}
                    onClick={() => toggleStation(station.id)}
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
                    type="button"
                    onClick={() => setSelectedStations([])}
                    className="px-3 py-1 text-sm text-gray-500 hover:text-gray-700"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          )}

          <div>
            <label
              htmlFor="nocturnal-period"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Period
            </label>
            <select
              id="nocturnal-period"
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="px-3 py-1 border rounded text-sm"
            >
              <option value={3}>Last 3 months</option>
              <option value={6}>Last 6 months</option>
              <option value={12}>Last 12 months</option>
              <option value={24}>Last 2 years</option>
              <option value={60}>Last 5 years</option>
            </select>
          </div>
        </div>
      </div>

      {/* Group summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {groups.map((group) => (
          <div
            key={group.group}
            className="bg-white rounded-lg shadow p-4 border-l-4"
            style={{ borderLeftColor: GROUP_COLORS[group.group] ?? GROUP_COLORS.other }}
          >
            <h3 className="text-lg font-semibold">{group.label}</h3>
            <p className="text-xs text-muted-foreground mt-1">{group.description}</p>
            <div className="mt-3 flex items-baseline gap-4">
              <div>
                <span className="text-2xl font-bold">
                  {group.detection_count.toLocaleString()}
                </span>
                <span className="text-xs text-muted-foreground ml-1">detections</span>
              </div>
              <div>
                <span className="text-lg font-semibold">{group.species_count}</span>
                <span className="text-xs text-muted-foreground ml-1">species</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <ChartPanel
          description="Activity relative to sunset — the emergence peak. Turn on the sunrise series in the legend to compare the other end of the night."
          loading={dusk.loading}
          error={dusk.error}
          isEmpty={dusk.data.length === 0 && dawn.data.length === 0}
          emptyMessage="No sunset data available — sync weather to populate sunrise and sunset times"
          onRetry={dusk.reload}
        >
          <Plot
            data={chorusChart.data}
            layout={chorusChart.layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </ChartPanel>

        <ChartPanel
          description="Detections per night. Bats and nightjars drop out over winter; owls carry on."
          loading={nightly.loading}
          error={nightly.error}
          isEmpty={nightly.data.length === 0}
          onRetry={nightly.reload}
        >
          <Plot
            data={nightlyChart.data}
            layout={nightlyChart.layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%' }}
          />
        </ChartPanel>
      </div>

      <ChartPanel
        description="When each species is heard. Rows run noon to noon so a single night reads left to right, and each species is scaled to its own peak."
        loading={hourly.loading}
        error={hourly.error}
        isEmpty={hourly.data.length === 0}
        onRetry={hourly.reload}
      >
        <Plot
          data={hourlyChart.data}
          layout={hourlyChart.layout}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      </ChartPanel>

      {/* Species table */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-2">Nocturnal species</h3>
        {summary.error ? (
          <div className="h-32 flex flex-col items-center justify-center gap-3">
            <p className="text-sm text-red-600">{summary.error}</p>
            <button
              type="button"
              onClick={summary.reload}
              className="px-3 py-1 text-sm rounded border border-red-300 text-red-700 hover:bg-red-50"
            >
              Retry
            </button>
          </div>
        ) : species.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {['Species', 'Group', 'Family', 'Detections', 'Nights', 'First', 'Last'].map(
                    (heading, idx) => (
                      <th
                        key={heading}
                        className={`px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                          idx >= 3 && idx <= 4 ? 'text-right' : 'text-left'
                        }`}
                      >
                        {heading}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {species.map((sp) => (
                  <tr key={sp.species_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                      <Link
                        to={`/species-details?id=${sp.species_id}`}
                        className="hover:text-indigo-600 hover:underline"
                      >
                        {sp.common_name}
                      </Link>
                      <div className="text-xs text-gray-500 italic">{sp.scientific_name}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span
                        className="px-2 py-0.5 rounded-full text-xs text-white"
                        style={{
                          backgroundColor: GROUP_COLORS[sp.group ?? 'other'] ?? GROUP_COLORS.other,
                        }}
                      >
                        {sp.group_label}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {sp.family ?? '—'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                      {sp.detection_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                      {sp.active_nights.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {sp.first_seen ?? '—'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {sp.last_seen ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-32 flex items-center justify-center text-sm text-muted-foreground">
            {summary.loading
              ? 'Loading…'
              : noTaxonomy
                ? 'Load the eBird taxonomy to populate this page.'
                : 'No nocturnal species detected in this period.'}
          </div>
        )}
      </div>
    </div>
  )
}

export default Nocturnal

/**
 * Station Comparison Page
 * Compare statistics across multiple stations with UpSet plot.
 *
 * Version: 1.2.0
 */

import React, { useEffect, useState, useMemo } from 'react'
import { stationsApi, settingsApi, generateBirdLinks, DEFAULT_BIRD_SOURCES } from '../api'
import { BarChart } from '../components/charts'
import type { StationStats } from '../types/api'
import type { Data } from 'plotly.js'

// Indigo Bunting color palette
const COLORS = {
  brilliant: '#4169E1',
  deep: '#1E3A8A',
  cerulean: '#5B9BD5',
  brown: '#8B7355',
  midnight: '#0F172A',
}

// Type for species info from API
interface SpeciesInfo {
  common_name: string
  scientific_name: string
  ebird_code?: string
  inat_taxon_id?: number | null
}

// Expandable species list component
const ExpandableSpeciesList: React.FC<{
  title: string
  subtitle: string
  species: SpeciesInfo[]
  birdInfoSources: string[]
  defaultExpanded?: boolean
}> = ({ title, subtitle, species, birdInfoSources, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div className="bg-white rounded-lg shadow">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 text-left flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div>
          <h3 className="font-semibold text-lg">{title}</h3>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold text-indigo-brilliant">{species.length}</span>
          <span className={`transform transition-transform ${expanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </button>
      {expanded && (
        <div className="border-t px-4 pb-4">
          {species.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-1 mt-3">
              {species.map((sp) => {
                const links = generateBirdLinks(
                  sp.common_name,
                  sp.scientific_name,
                  sp.ebird_code,
                  birdInfoSources,
                  sp.inat_taxon_id
                )
                return (
                  <div
                    key={sp.common_name}
                    className="flex items-center justify-between py-1.5 px-2 hover:bg-gray-50 rounded text-sm"
                  >
                    <span className="truncate">{sp.common_name}</span>
                    <div className="flex gap-2 ml-2 flex-shrink-0">
                      {links.map((link) => (
                        <a
                          key={link.source_id}
                          href={link.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-brilliant hover:underline"
                        >
                          {link.name}
                        </a>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">No species in this category</p>
          )}
        </div>
      )}
    </div>
  )
}

interface UpSetIntersection {
  label: string
  stations: string[]
  species: SpeciesInfo[]
  count: number
}

const StationComparison: React.FC = () => {
  const [stations, setStations] = useState<StationStats[]>([])
  const [speciesByStation, setSpeciesByStation] = useState<Record<string, SpeciesInfo[]>>({})
  const [birdInfoSources, setBirdInfoSources] = useState<string[]>(DEFAULT_BIRD_SOURCES)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
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

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [statsData, speciesData] = await Promise.all([
        stationsApi.getComparison(),
        stationsApi.getSpeciesByStation(),
      ])
      setStations(statsData)
      setSpeciesByStation(speciesData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  // Compute UpSet data
  const upsetData = useMemo((): {
    intersections: UpSetIntersection[]
    uniqueByStation: Record<string, SpeciesInfo[]>
    sharedByAll: SpeciesInfo[]
    stationNames?: string[]
  } => {
    const stationNames = Object.keys(speciesByStation)
    if (stationNames.length === 0) return { intersections: [], uniqueByStation: {}, sharedByAll: [] }

    // Build a map from common_name to SpeciesInfo for quick lookup
    const speciesInfoMap = new Map<string, SpeciesInfo>()
    for (const speciesList of Object.values(speciesByStation)) {
      for (const sp of speciesList) {
        speciesInfoMap.set(sp.common_name, sp)
      }
    }

    // Get all unique species names across all stations
    const allSpeciesNames = new Set<string>()
    for (const speciesList of Object.values(speciesByStation)) {
      speciesList.forEach((sp) => allSpeciesNames.add(sp.common_name))
    }

    // For each species, determine which stations have it
    const speciesStationMap = new Map<string, Set<string>>()
    for (const speciesName of allSpeciesNames) {
      const stationsWithSpecies = new Set<string>()
      for (const [stationName, speciesList] of Object.entries(speciesByStation)) {
        if (speciesList.some(sp => sp.common_name === speciesName)) {
          stationsWithSpecies.add(stationName)
        }
      }
      speciesStationMap.set(speciesName, stationsWithSpecies)
    }

    // Group species by their station combination
    const intersectionMap = new Map<string, string[]>()
    for (const [speciesName, stationsSet] of speciesStationMap) {
      const key = Array.from(stationsSet).sort().join('|')
      if (!intersectionMap.has(key)) {
        intersectionMap.set(key, [])
      }
      intersectionMap.get(key)!.push(speciesName)
    }

    // Build intersection list
    const intersections: UpSetIntersection[] = []
    for (const [key, speciesNames] of intersectionMap) {
      const stationsInKey = key.split('|')
      let label: string
      if (stationsInKey.length === stationNames.length) {
        label = 'All Stations'
      } else if (stationsInKey.length === 1) {
        label = `Only ${stationsInKey[0]}`
      } else {
        label = stationsInKey.join(' + ')
      }
      // Convert species names to SpeciesInfo objects
      const speciesInfoList = speciesNames
        .sort()
        .map(name => speciesInfoMap.get(name)!)
        .filter(Boolean)
      intersections.push({
        label,
        stations: stationsInKey,
        species: speciesInfoList,
        count: speciesInfoList.length,
      })
    }

    // Sort by count descending
    intersections.sort((a, b) => b.count - a.count)

    // Extract unique per station and shared by all
    const uniqueByStation: Record<string, SpeciesInfo[]> = {}
    let sharedByAll: SpeciesInfo[] = []

    for (const intersection of intersections) {
      if (intersection.stations.length === 1) {
        uniqueByStation[intersection.stations[0]] = intersection.species
      } else if (intersection.stations.length === stationNames.length) {
        sharedByAll = intersection.species
      }
    }

    return { intersections, uniqueByStation, sharedByAll, stationNames }
  }, [speciesByStation])

  // Prepare UpSet bar chart data
  const prepareUpsetChart = (): Data[] => {
    if (upsetData.intersections.length === 0) return []

    // Take top 15 intersections for visibility
    const topIntersections = upsetData.intersections.slice(0, 15)

    return [
      {
        x: topIntersections.map((i) => i.label),
        y: topIntersections.map((i) => i.count),
        type: 'bar' as const,
        marker: {
          color: topIntersections.map((i) => {
            if (i.stations.length === upsetData.stationNames?.length) return COLORS.brilliant
            if (i.stations.length === 1) return COLORS.cerulean
            return COLORS.brown
          }),
        },
        hovertemplate: '%{x}<br>%{y} species<extra></extra>',
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

  const stationNames = Object.keys(speciesByStation)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Station Comparison</h1>
        <p className="text-muted-foreground mt-2">
          Compare statistics and species overlap across all stations
        </p>
      </div>

      {/* Station Comparison Table */}
      {stations.length > 0 && (
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
      )}

      {/* UpSet Plot Section */}
      {stationNames.length > 0 && (
        <>
          {/* UpSet Plot */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Species Overlap (UpSet Plot)</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Shows how many species are shared between different station combinations.
              <span className="inline-block ml-2 px-2 py-0.5 text-xs rounded" style={{ backgroundColor: COLORS.brilliant, color: 'white' }}>All Stations</span>
              <span className="inline-block ml-2 px-2 py-0.5 text-xs rounded" style={{ backgroundColor: COLORS.cerulean, color: 'white' }}>Unique to One</span>
              <span className="inline-block ml-2 px-2 py-0.5 text-xs rounded" style={{ backgroundColor: COLORS.brown, color: 'white' }}>Some Stations</span>
            </p>
            <BarChart
              data={prepareUpsetChart()}
              layout={{
                xaxis: {
                  tickangle: -45,
                  automargin: true,
                  tickfont: { size: 10 },
                },
                yaxis: { title: { text: 'Number of Species' } },
                height: 500,
                margin: { l: 60, r: 20, t: 20, b: 220 },
              }}
            />
          </div>

          {/* Species Lists - Expandable */}
          <div className="space-y-3">
            <h2 className="text-xl font-semibold">Species by Category</h2>

            {/* Shared by All Stations */}
            <ExpandableSpeciesList
              title="Shared by All Stations"
              subtitle={`Species detected at every station`}
              species={upsetData.sharedByAll}
              birdInfoSources={birdInfoSources}
              defaultExpanded={true}
            />

            {/* Unique to Each Station */}
            {stationNames.map((stationName) => {
              const uniqueSpecies = upsetData.uniqueByStation[stationName] || []
              return (
                <ExpandableSpeciesList
                  key={stationName}
                  title={`Unique to ${stationName}`}
                  subtitle={`Species only detected at this station`}
                  species={uniqueSpecies}
                  birdInfoSources={birdInfoSources}
                />
              )
            })}
          </div>
        </>
      )}

      {stations.length === 0 && stationNames.length === 0 && (
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

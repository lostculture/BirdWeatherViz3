/**
 * Species List Page
 * Family analysis with horizontal bar charts and species details.
 *
 * Version: 1.4.0
 */

import React, { useEffect, useState } from 'react'
import { speciesApi } from '../api'
import { BarChart } from '../components/charts'
import { useFilters } from '../context/FilterContext'
import type { FamilyStats, SpeciesResponse } from '../types/api'
import type { Data } from 'plotly.js'

import { Link } from 'react-router-dom'

// Helper to get bird image URL
const getBirdImageUrl = (scientificName: string, commonName?: string): string => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  let url = `${baseUrl}/images/bird/${encodeURIComponent(scientificName)}`
  if (commonName) {
    url += `?common_name=${encodeURIComponent(commonName)}`
  }
  return url
}

// Species card component
const SpeciesCard: React.FC<{ species: SpeciesResponse }> = ({ species }) => {
  const [imageError, setImageError] = useState(false)
  const imageUrl = getBirdImageUrl(species.scientific_name, species.common_name)

  return (
    <div className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow bg-white">
      <div className="h-24 bg-gray-100 relative">
        {!imageError ? (
          <img
            src={imageUrl}
            alt={species.common_name}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-3xl">🐦</span>
          </div>
        )}
      </div>
      <div className="p-3">
        <div className="font-semibold text-sm">{species.common_name}</div>
        <div className="text-xs text-muted-foreground italic truncate">
          {species.scientific_name}
        </div>
        <div className="text-xs text-muted-foreground mt-1">
          {species.total_detections?.toLocaleString() || 0} detections
        </div>
        <div className="mt-2">
          <Link
            to={`/species-details?id=${species.id}`}
            className="text-indigo-brilliant hover:underline text-xs font-medium"
          >
            Details
          </Link>
        </div>
      </div>
    </div>
  )
}

const SpeciesList: React.FC = () => {
  const { startDate, endDate, getStationIdsParam } = useFilters()
  const [familyData, setFamilyData] = useState<FamilyStats[]>([])
  const [selectedFamily, setSelectedFamily] = useState<string | null>(null)
  const [familySpecies, setFamilySpecies] = useState<SpeciesResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingSpecies, setLoadingSpecies] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reload when filters change
  useEffect(() => {
    loadData()
    setSelectedFamily(null)
    setFamilySpecies([])
  }, [startDate, endDate, getStationIdsParam()])

  // Load species when family is selected
  useEffect(() => {
    if (selectedFamily) {
      loadFamilySpecies(selectedFamily)
    }
  }, [selectedFamily])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const filterParams = {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        station_ids: getStationIdsParam(),
      }
      const data = await speciesApi.getFamilyStats(filterParams)
      setFamilyData(data.sort((a, b) => b.total_detections - a.total_detections))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const loadFamilySpecies = async (familyName: string) => {
    try {
      setLoadingSpecies(true)
      const species = await speciesApi.getByFamily(familyName, {
        station_ids: getStationIdsParam(),
      })
      setFamilySpecies(species.sort((a, b) => (b.total_detections || 0) - (a.total_detections || 0)))
    } catch (err) {
      console.error('Failed to load family species:', err)
    } finally {
      setLoadingSpecies(false)
    }
  }

  // Prepare horizontal bar chart for detections (sorted ascending so highest at top)
  const prepareDetectionsChart = (): Data[] => {
    const sortedData = [...familyData].sort((a, b) => a.total_detections - b.total_detections)
    return [
      {
        y: sortedData.map((f) => f.family),
        x: sortedData.map((f) => f.total_detections),
        type: 'bar' as const,
        orientation: 'h' as const,
        marker: {
          color: sortedData.map((f) => f.total_detections),
          colorscale: 'Viridis',
        },
        hovertemplate: '%{y}<br>%{x:,} detections<extra></extra>',
      },
    ]
  }

  // Prepare horizontal bar chart for species count (sorted ascending so highest at top)
  const prepareSpeciesCountChart = (): Data[] => {
    const sortedData = [...familyData].sort((a, b) => a.species_count - b.species_count)
    return [
      {
        y: sortedData.map((f) => f.family),
        x: sortedData.map((f) => f.species_count),
        type: 'bar' as const,
        orientation: 'h' as const,
        marker: {
          color: sortedData.map((f) => f.species_count),
          colorscale: 'Viridis',
        },
        hovertemplate: '%{y}<br>%{x} species<extra></extra>',
      },
    ]
  }

  const handleFamilyClick = (family: string) => {
    if (selectedFamily === family) {
      setSelectedFamily(null)
      setFamilySpecies([])
    } else {
      setSelectedFamily(family)
    }
  }

  const selectedFamilyStats = familyData.find((f) => f.family === selectedFamily)

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

  const chartHeight = Math.max(500, familyData.length * 28)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Species List</h1>
        <p className="text-muted-foreground mt-2">
          Family analysis and species patterns. Select a family below to see its species.
        </p>
      </div>

      {/* Charts - Stacked Vertically */}
      <div className="space-y-6">
        {/* Detections by Family - Horizontal Bars */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Detections by Family</h2>
          {familyData.length > 0 ? (
            <BarChart
              data={prepareDetectionsChart()}
              orientation="h"
              layout={{
                xaxis: { title: { text: 'Total Detections' } },
                yaxis: { automargin: true, tickfont: { size: 11 } },
                height: chartHeight,
                margin: { l: 200, r: 40, t: 20, b: 50 },
              }}
            />
          ) : (
            <div className="text-center text-muted-foreground py-8">
              No family data available
            </div>
          )}
        </div>

        {/* Species Count by Family - Horizontal Bars */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Species Count by Family</h2>
          {familyData.length > 0 ? (
            <BarChart
              data={prepareSpeciesCountChart()}
              orientation="h"
              layout={{
                xaxis: { title: { text: 'Number of Species' } },
                yaxis: { automargin: true, tickfont: { size: 11 } },
                height: chartHeight,
                margin: { l: 200, r: 40, t: 20, b: 50 },
              }}
            />
          ) : (
            <div className="text-center text-muted-foreground py-8">
              No family data available
            </div>
          )}
        </div>
      </div>

      {/* Family Selection - Below the graphs */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Family Explorer</h2>
        <p className="text-sm text-muted-foreground mb-4">Select a family to view its species</p>
        <select
          value={selectedFamily || ''}
          onChange={(e) => handleFamilyClick(e.target.value)}
          className="w-full md:w-96 p-3 border rounded-lg text-sm bg-white"
        >
          <option value="">-- Select a family --</option>
          {familyData.map((family) => (
            <option key={family.family} value={family.family}>
              {family.family} ({family.species_count} species, {family.total_detections.toLocaleString()} detections)
            </option>
          ))}
        </select>
      </div>

      {/* Selected Family Details */}
      {selectedFamily && selectedFamilyStats && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">{selectedFamily}</h2>
            <button
              onClick={() => {
                setSelectedFamily(null)
                setFamilySpecies([])
              }}
              className="text-gray-500 hover:text-gray-700 text-xl"
            >
              ×
            </button>
          </div>

          {/* Family Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-indigo-dark">
                {selectedFamilyStats.species_count}
              </div>
              <div className="text-sm text-muted-foreground">Species</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-indigo-dark">
                {selectedFamilyStats.total_detections.toLocaleString()}
              </div>
              <div className="text-sm text-muted-foreground">Total Detections</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-indigo-dark">
                {Math.round(selectedFamilyStats.total_detections / selectedFamilyStats.species_count).toLocaleString()}
              </div>
              <div className="text-sm text-muted-foreground">Avg per Species</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-indigo-dark">
                {((selectedFamilyStats.total_detections / familyData.reduce((sum, f) => sum + f.total_detections, 0)) * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-muted-foreground">of All Detections</div>
            </div>
          </div>

          {/* Species Grid */}
          <h3 className="text-lg font-semibold mb-4">Species in {selectedFamily}</h3>
          {loadingSpecies ? (
            <div className="text-center text-muted-foreground py-8">
              Loading species...
            </div>
          ) : familySpecies.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {familySpecies.map((species) => (
                <SpeciesCard key={species.id} species={species} />
              ))}
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              No species found in this family
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SpeciesList

/**
 * Species List Page
 * Family analysis, ridge plots, and top species patterns.
 *
 * Version: 1.0.0
 */

import React, { useEffect, useState } from 'react'
import { speciesApi } from '../api'
import { BarChart } from '../components/charts'
import type { FamilyStats } from '../types/api'
import type { Data } from 'plotly.js'

const SpeciesList: React.FC = () => {
  const [familyData, setFamilyData] = useState<FamilyStats[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await speciesApi.getFamilyStats()
      setFamilyData(data.sort((a, b) => b.detection_count - a.detection_count))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const prepareFamilyChart = (): Data[] => {
    return [
      {
        x: familyData.map((f) => f.family),
        y: familyData.map((f) => f.detection_count),
        name: 'Detections',
        type: 'bar' as const,
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Species List</h1>
        <p className="text-muted-foreground mt-2">
          Family analysis and species patterns
        </p>
      </div>

      {/* Family Statistics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Bird Family Statistics</h2>
        {familyData.length > 0 ? (
          <BarChart
            data={prepareFamilyChart()}
            layout={{
              title: { text: 'Detections by Bird Family' },
              xaxis: { title: { text: 'Family' } },
              yaxis: { title: { text: 'Total Detections' } },
              height: 500,
            }}
          />
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No family data available
          </div>
        )}
      </div>

      {/* Family Table */}
      {familyData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Family Details</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Family
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Species Count
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Total Detections
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Avg Confidence
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {familyData.map((family) => (
                  <tr key={family.family}>
                    <td className="px-6 py-4 whitespace-nowrap font-medium">
                      {family.family}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {family.species_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {family.detection_count.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {family.avg_confidence.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default SpeciesList

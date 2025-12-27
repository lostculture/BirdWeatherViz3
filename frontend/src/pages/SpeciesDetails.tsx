/**
 * Species Details Page
 * Individual species analysis with rose plots and KDE.
 *
 * Version: 1.0.0
 */

import React from 'react'

const SpeciesDetails: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Species Details</h1>
        <p className="text-muted-foreground mt-2">
          Detailed analysis for individual species (Coming soon in Phase 5)
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Features</h2>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li>Rose plots (hourly detection patterns)</li>
          <li>KDE plots (density estimation)</li>
          <li>Monthly patterns</li>
          <li>Confidence distribution</li>
          <li>Species-specific statistics</li>
        </ul>
      </div>
    </div>
  )
}

export default SpeciesDetails

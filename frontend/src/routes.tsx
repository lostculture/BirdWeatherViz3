/**
 * Application Routes
 * React Router configuration for all pages.
 *
 * Version: 1.0.0
 */

import { Routes, Route } from 'react-router-dom'
import DailyDetections from './pages/DailyDetections'
import SpeciesAnalysis from './pages/SpeciesAnalysis'
import SpeciesDetails from './pages/SpeciesDetails'
import SpeciesList from './pages/SpeciesList'
import StationComparison from './pages/StationComparison'
import Configuration from './pages/Configuration'

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<DailyDetections />} />
      <Route path="/species-analysis" element={<SpeciesAnalysis />} />
      <Route path="/species-details" element={<SpeciesDetails />} />
      <Route path="/species-list" element={<SpeciesList />} />
      <Route path="/stations" element={<StationComparison />} />
      <Route path="/config" element={<Configuration />} />
    </Routes>
  )
}

export default AppRoutes

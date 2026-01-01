/**
 * Configuration Page
 * Application settings and station management.
 *
 * Version: 1.0.0
 */

import React, { useState, useEffect, useRef } from 'react'
import { stationsApi, settingsApi, weatherApi } from '../api'
import type { StationResponse, StationCreate, StationUpdate } from '../types/api'
import type { TaxonomyStats } from '../api/settings'
import type { WeatherStats, WeatherStationSetting } from '../api/weather'

interface StationFormData {
  station_id: string
  name: string
  timezone: string
  active: boolean
}

const Configuration: React.FC = () => {
  // Station state
  const [stations, setStations] = useState<StationResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingStation, setEditingStation] = useState<StationResponse | null>(null)
  const [syncing, setSyncing] = useState<{ [key: number]: boolean }>({})
  const [syncingAll, setSyncingAll] = useState(false)
  const [formData, setFormData] = useState<StationFormData>({
    station_id: '',
    name: '',
    timezone: 'America/New_York',
    active: true,
  })

  // Settings state
  const [taxonomyStats, setTaxonomyStats] = useState<TaxonomyStats | null>(null)
  const [uploadingTaxonomy, setUploadingTaxonomy] = useState(false)
  const [uploadingDetections, setUploadingDetections] = useState(false)

  // Weather state
  const [weatherStats, setWeatherStats] = useState<WeatherStats | null>(null)
  const [weatherStation, setWeatherStation] = useState<WeatherStationSetting | null>(null)
  const [syncingWeather, setSyncingWeather] = useState(false)
  const [settingWeatherStation, setSettingWeatherStation] = useState(false)

  const taxonomyFileRef = useRef<HTMLInputElement>(null)
  const detectionsFileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadStations()
    loadSettings()
    loadWeatherData()
  }, [])

  const loadStations = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await stationsApi.getAll()
      setStations(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load stations')
    } finally {
      setLoading(false)
    }
  }

  const loadSettings = async () => {
    try {
      const stats = await settingsApi.getTaxonomyStats()
      setTaxonomyStats(stats)
    } catch (err) {
      console.error('Failed to load settings:', err)
    }
  }

  const loadWeatherData = async () => {
    try {
      const [stats, station] = await Promise.all([
        weatherApi.getStats(),
        weatherApi.getStationSetting()
      ])
      setWeatherStats(stats)
      setWeatherStation(station)
    } catch (err) {
      console.error('Failed to load weather data:', err)
    }
  }

  const handleSetWeatherStation = async (stationId: number) => {
    try {
      setSettingWeatherStation(true)
      const result = await weatherApi.setStation(stationId)
      setWeatherStation(result)
      await loadWeatherData()
    } catch (err: any) {
      alert('Failed to set weather station: ' + (err.message || 'Unknown error'))
    } finally {
      setSettingWeatherStation(false)
    }
  }

  const handleSyncWeather = async () => {
    if (!weatherStation?.station_id) {
      alert('Please select a weather station first')
      return
    }
    try {
      setSyncingWeather(true)
      const result = await weatherApi.sync()
      alert(result.message)
      await loadWeatherData()
    } catch (err: any) {
      alert('Failed to sync weather: ' + (err.message || 'Unknown error'))
    } finally {
      setSyncingWeather(false)
    }
  }

  const handleAddStation = () => {
    setEditingStation(null)
    setFormData({
      station_id: '',
      name: '',
      timezone: 'America/New_York',
      active: true,
    })
    setShowForm(true)
  }

  const handleEditStation = (station: StationResponse) => {
    setEditingStation(station)
    setFormData({
      station_id: String(station.station_id),
      name: station.name,
      timezone: station.timezone || 'America/New_York',
      active: station.active,
    })
    setShowForm(true)
  }

  const handleDeleteStation = async (id: number) => {
    if (!confirm('Are you sure you want to delete this station? All associated detections will be deleted.')) {
      return
    }

    try {
      await stationsApi.delete(id)
      await loadStations()
    } catch (err: any) {
      alert('Failed to delete station: ' + (err.message || 'Unknown error'))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    try {
      if (editingStation) {
        const updateData: StationUpdate = {
          name: formData.name,
          timezone: formData.timezone,
          active: formData.active,
        }
        await stationsApi.update(editingStation.id, updateData)
      } else {
        const createData: StationCreate = {
          station_id: parseInt(formData.station_id),
          name: formData.name,
          timezone: formData.timezone,
          active: formData.active,
        }
        await stationsApi.create(createData)
      }
      setShowForm(false)
      await loadStations()
    } catch (err: any) {
      console.error('Station save error:', err)
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          const errors = err.response.data.detail
            .map((e: any) => `${e.loc.join('.')}: ${e.msg}`)
            .join(', ')
          setError(`Validation error: ${errors}`)
        } else {
          setError(err.response.data.detail)
        }
      } else {
        setError(err.message || 'Failed to save station')
      }
    }
  }

  const handleSyncStation = async (stationId: number) => {
    setSyncing((prev) => ({ ...prev, [stationId]: true }))
    try {
      const result = await stationsApi.sync(stationId)
      alert(`Success! ${result.message}`)
      await loadStations()
    } catch (err: any) {
      alert('Failed to sync: ' + (err.message || 'Unknown error'))
    } finally {
      setSyncing((prev) => ({ ...prev, [stationId]: false }))
    }
  }

  const handleSyncAllStations = async () => {
    setSyncingAll(true)
    try {
      const result = await stationsApi.syncAll()
      const messages = result.details.map(
        (d) => `${d.station_name}: ${d.detections_added} detections (${d.status})`
      ).join('\n')

      let weatherMsg = ''
      if (result.weather_synced && result.weather_days_fetched > 0) {
        weatherMsg = `\n\nWeather: ${result.weather_days_fetched} days synced`
      } else if (result.weather_synced) {
        weatherMsg = '\n\nWeather: Already up to date'
      }

      alert(`Sync complete!\n\nTotal: ${result.total_detections_added} new detections${weatherMsg}\n\n${messages}`)
      await loadStations()
      await loadWeatherData()
    } catch (err: any) {
      alert('Failed to sync all stations: ' + (err.message || 'Unknown error'))
    } finally {
      setSyncingAll(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    const checked = (e.target as HTMLInputElement).checked

    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseFloat(value) : value,
    }))
  }

  const handleTaxonomyUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadingTaxonomy(true)
    try {
      const result = await settingsApi.uploadTaxonomy(file)
      alert(result.message)
      await loadSettings()
    } catch (err: any) {
      alert('Failed to upload taxonomy: ' + (err.message || 'Unknown error'))
    } finally {
      setUploadingTaxonomy(false)
      if (taxonomyFileRef.current) {
        taxonomyFileRef.current.value = ''
      }
    }
  }

  const handleDetectionsUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadingDetections(true)
    try {
      const result = await settingsApi.uploadDetections(file)
      alert(result.message)
      await loadStations() // Refresh to show updated stats
    } catch (err: any) {
      alert('Failed to upload detections: ' + (err.message || 'Unknown error'))
    } finally {
      setUploadingDetections(false)
      if (detectionsFileRef.current) {
        detectionsFileRef.current.value = ''
      }
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-lg">Loading configuration...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Configuration</h1>
          <p className="text-gray-600 mt-2">Manage stations, sync data, and configure settings</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={handleSyncAllStations}
            disabled={syncingAll || stations.length === 0}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
          >
            {syncingAll ? 'Syncing All...' : 'Sync All Stations'}
          </button>
          <button
            onClick={handleAddStation}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium"
          >
            Add Station
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>
      )}

      {/* Station Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold mb-4">
                {editingStation ? 'Edit Station' : 'Add New Station'}
              </h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">BirdWeather Station ID *</label>
                  <input
                    type="text"
                    name="station_id"
                    value={formData.station_id}
                    onChange={handleInputChange}
                    required
                    disabled={!!editingStation}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    placeholder="12345"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Station Name *</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="My BirdWeather Station"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Timezone *</label>
                  <input
                    type="text"
                    name="timezone"
                    value={formData.timezone}
                    onChange={handleInputChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="America/New_York"
                  />
                </div>

                <div className="flex items-center">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      name="active"
                      checked={formData.active}
                      onChange={handleInputChange}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <span className="ml-2 text-sm font-medium">Active (include in analysis)</span>
                  </label>
                </div>

                <div className="flex justify-end space-x-3 pt-4 border-t">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
                  >
                    {editingStation ? 'Update Station' : 'Add Station'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Stations Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Stations</h2>
          {stations.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg mb-2">No stations configured</p>
              <p className="text-sm">Click "Add Station" to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-semibold">Station ID</th>
                    <th className="text-left py-3 px-4 font-semibold">Name</th>
                    <th className="text-left py-3 px-4 font-semibold">Location</th>
                    <th className="text-center py-3 px-4 font-semibold">Status</th>
                    <th className="text-center py-3 px-4 font-semibold">Last Update</th>
                    <th className="text-right py-3 px-4 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {stations.map((station) => (
                    <tr key={station.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-mono text-sm">{station.station_id}</td>
                      <td className="py-3 px-4">{station.name}</td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {station.latitude && station.longitude
                          ? `${station.latitude.toFixed(4)}, ${station.longitude.toFixed(4)}`
                          : <span className="text-gray-400 italic">Pending sync</span>
                        }
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-block px-2 py-1 text-xs font-semibold rounded ${
                            station.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {station.active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center text-sm text-gray-600">
                        {station.last_update ? new Date(station.last_update).toLocaleString() : 'Never'}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => handleSyncStation(station.id)}
                            disabled={syncing[station.id]}
                            className="px-3 py-1 text-sm bg-green-100 hover:bg-green-200 text-green-800 rounded font-medium disabled:opacity-50"
                          >
                            {syncing[station.id] ? 'Syncing...' : 'Sync'}
                          </button>
                          <button
                            onClick={() => handleEditStation(station)}
                            className="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 text-blue-800 rounded font-medium"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteStation(station.id)}
                            className="px-3 py-1 text-sm bg-red-100 hover:bg-red-200 text-red-800 rounded font-medium"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* eBird Taxonomy Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">eBird Taxonomy</h2>
          <p className="text-gray-600 mb-4">
            Upload eBird taxonomy CSV to enable species codes for eBird links and additional taxonomy data.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium mb-2">Upload Taxonomy CSV</h3>
              <div className="flex items-center space-x-4">
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleTaxonomyUpload}
                  ref={taxonomyFileRef}
                  disabled={uploadingTaxonomy}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Download from{' '}
                <a
                  href="https://www.birds.cornell.edu/clementschecklist/download/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  Cornell Lab Clements Checklist
                </a>
              </p>
            </div>

            <div>
              <h3 className="font-medium mb-2">Taxonomy Statistics</h3>
              {taxonomyStats ? (
                <div className="space-y-1 text-sm">
                  {taxonomyStats.ebird_entries > 0 && (
                    <p>
                      eBird taxonomy entries:{' '}
                      <span className="font-semibold">{taxonomyStats.ebird_entries.toLocaleString()}</span>
                    </p>
                  )}
                  <p>
                    Species in database:{' '}
                    <span className="font-semibold">{taxonomyStats.total_species.toLocaleString()}</span>
                  </p>
                  <p>
                    With eBird codes:{' '}
                    <span className="font-semibold">{taxonomyStats.species_with_codes.toLocaleString()}</span>
                    {' '}({taxonomyStats.coverage_percent}%)
                  </p>
                  <p>
                    With family data:{' '}
                    <span className="font-semibold">{taxonomyStats.species_with_families.toLocaleString()}</span>
                  </p>
                  {taxonomyStats.unique_families > 0 && (
                    <p>
                      Unique families:{' '}
                      <span className="font-semibold">{taxonomyStats.unique_families}</span>
                    </p>
                  )}
                  {taxonomyStats.last_updated && (
                    <p className="text-gray-500">
                      Last updated:{' '}
                      {new Date(taxonomyStats.last_updated).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No taxonomy data loaded</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Manual Detection Upload */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Manual Detection Upload</h2>
          <p className="text-gray-600 mb-4">
            Upload detection data from a CSV file. The CSV should contain columns for: Timestamp, Common Name,
            Scientific Name, Latitude, Longitude, Station, and Confidence.
          </p>

          <div className="flex items-center space-x-4">
            <input
              type="file"
              accept=".csv"
              onChange={handleDetectionsUpload}
              ref={detectionsFileRef}
              disabled={uploadingDetections || stations.length === 0}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100 disabled:opacity-50"
            />
            {uploadingDetections && (
              <span className="text-sm text-gray-600">Uploading...</span>
            )}
          </div>

          {stations.length === 0 && (
            <p className="text-sm text-amber-600 mt-2">
              Add at least one station before uploading detections.
            </p>
          )}

          <p className="text-xs text-gray-500 mt-2">
            Station names in the CSV must match (or partially match) station names configured above.
            New species will be created automatically.
          </p>
        </div>
      </div>

      {/* Weather Settings */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Weather Data</h2>
          <p className="text-gray-600 mb-4">
            Weather data is fetched from Open-Meteo using the selected station's GPS coordinates.
            Sync downloads historical weather for all days with bird detections.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Station Selection */}
            <div>
              <h3 className="font-medium mb-2">Weather Location</h3>
              <div className="space-y-2">
                <select
                  value={weatherStation?.station_id || ''}
                  onChange={(e) => {
                    const stationId = parseInt(e.target.value)
                    if (stationId) handleSetWeatherStation(stationId)
                  }}
                  disabled={settingWeatherStation || stations.length === 0}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50"
                >
                  <option value="">Select a station...</option>
                  {stations
                    .filter(s => s.latitude && s.longitude && s.latitude !== 0)
                    .map(s => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.latitude?.toFixed(4)}, {s.longitude?.toFixed(4)})
                      </option>
                    ))
                  }
                </select>
                {stations.filter(s => s.latitude && s.latitude !== 0).length === 0 && (
                  <p className="text-sm text-amber-600">
                    No stations have GPS coordinates. Sync detections first.
                  </p>
                )}
              </div>

              <div className="mt-4">
                <button
                  onClick={handleSyncWeather}
                  disabled={syncingWeather || !weatherStation?.station_id}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
                >
                  {syncingWeather ? 'Syncing Weather...' : 'Sync Weather Data'}
                </button>
              </div>
            </div>

            {/* Weather Stats */}
            <div>
              <h3 className="font-medium mb-2">Weather Statistics</h3>
              {weatherStats ? (
                <div className="space-y-1 text-sm">
                  <p>
                    Weather records:{' '}
                    <span className="font-semibold">{weatherStats.total_weather_records}</span>
                  </p>
                  <p>
                    Detection days:{' '}
                    <span className="font-semibold">{weatherStats.detection_days}</span>
                  </p>
                  <p>
                    Days with weather:{' '}
                    <span className="font-semibold">{weatherStats.weather_days}</span>
                    {weatherStats.missing_days > 0 && (
                      <span className="text-amber-600 ml-2">
                        ({weatherStats.missing_days} missing)
                      </span>
                    )}
                  </p>
                  {weatherStats.first_date && weatherStats.last_date && (
                    <p>
                      Date range:{' '}
                      <span className="font-semibold">
                        {weatherStats.first_date} to {weatherStats.last_date}
                      </span>
                    </p>
                  )}
                  {weatherStats.weather_station && (
                    <p className="text-gray-500">
                      Location: {weatherStats.weather_station}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No weather data</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Help Section */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">How Syncing Works</h3>
        <ul className="list-disc list-inside space-y-1 text-sm text-blue-800">
          <li>Intelligent sync fetches new detections from today back to your last synced date</li>
          <li>First sync may take longer as it fetches historical data</li>
          <li>Subsequent syncs are fast - only new detections are fetched</li>
          <li>Click "Sync All Stations" to update all active stations at once</li>
        </ul>
      </div>
    </div>
  )
}

export default Configuration

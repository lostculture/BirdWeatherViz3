/**
 * Configuration Page
 * Application settings and station management.
 *
 * Version: 1.0.0
 */

import React, { useState, useEffect, useRef } from 'react'
import {
  BIRD_INFO_SOURCES,
  BIRD_SOURCE_REGIONS,
  DEFAULT_BIRD_SOURCES,
  authApi,
  settingsApi,
  stationsApi,
  weatherApi,
} from '../api'
import type { DetectionUploadProgressEvent, TaxonomyStats } from '../api/settings'
import type { WeatherStationSetting, WeatherStats } from '../api/weather'
import SyncAllButton from '../components/SyncAllButton'
import ChangePasswordModal from '../components/auth/ChangePasswordModal'
import PasswordModal from '../components/auth/PasswordModal'
import { useSync } from '../context/SyncContext'
import type { StationCreate, StationResponse, StationUpdate } from '../types/api'

interface StationFormData {
  station_id: string
  name: string
  timezone: string
  active: boolean
}

const Configuration: React.FC = () => {
  // Shared sync state
  const {
    syncing: syncingAll,
    progress: syncProgress,
    details: syncDetails,
    syncAll,
  } = useSync()

  const handleForceFullResync = () => {
    const ok = window.confirm(
      'Re-sync the full BirdWeather history for every station?\n\n' +
        'This pulls every detection upstream — useful to recover detections ' +
        'missed by earlier (buggy) syncs. May take several minutes for stations ' +
        'with long histories.',
    )
    if (!ok) return
    syncAll({ forceFull: true })
  }

  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false)

  // Station state
  const [stations, setStations] = useState<StationResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingStation, setEditingStation] = useState<StationResponse | null>(null)
  const [syncing, setSyncing] = useState<{ [key: number]: boolean }>({})
  const [syncDismissed, setSyncDismissed] = useState(false)
  const showSyncProgress = !syncDismissed && (syncingAll || syncDetails.length > 0)
  // Reset dismiss when a new sync starts
  useEffect(() => {
    if (syncingAll) setSyncDismissed(false)
  }, [syncingAll])
  const [formData, setFormData] = useState<StationFormData>({
    station_id: '',
    name: '',
    timezone: 'America/New_York',
    active: true,
  })

  // Settings state
  const [taxonomyStats, setTaxonomyStats] = useState<TaxonomyStats | null>(null)
  const [uploadingTaxonomy, setUploadingTaxonomy] = useState(false)
  const [taxonomyLanguage, setTaxonomyLanguageState] = useState<string>('en')
  const [savingTaxonomyLanguage, setSavingTaxonomyLanguage] = useState(false)

  // DB backup/restore state
  const [dbInfo, setDbInfo] = useState<{
    supported: boolean
    engine: string
    path?: string
    exists?: boolean
    size_bytes?: number
  } | null>(null)
  const [exportingDb, setExportingDb] = useState(false)
  const [importingDb, setImportingDb] = useState(false)
  const dbImportFileRef = useRef<HTMLInputElement>(null)
  const [uploadingDetections, setUploadingDetections] = useState(false)
  const [detectionProgress, setDetectionProgress] = useState<DetectionUploadProgressEvent | null>(
    null,
  )
  const [detectionError, setDetectionError] = useState<string | null>(null)

  // Weather state
  const [weatherStats, setWeatherStats] = useState<WeatherStats | null>(null)
  const [weatherStation, setWeatherStation] = useState<WeatherStationSetting | null>(null)
  const [syncingWeather, setSyncingWeather] = useState(false)
  const [settingWeatherStation, setSettingWeatherStation] = useState(false)

  // Auto-update state
  const [autoUpdateOnStart, setAutoUpdateOnStart] = useState(true)
  const [savingAutoUpdate, setSavingAutoUpdate] = useState(false)

  // Update-check state (notification banner for new releases)
  const [updateCheckEnabled, setUpdateCheckEnabled] = useState(true)
  const [savingUpdateCheck, setSavingUpdateCheck] = useState(false)

  // Display units state
  const [temperatureUnit, setTemperatureUnit] = useState<'imperial' | 'metric'>('imperial')
  const [windSpeedUnit, setWindSpeedUnit] = useState<'imperial' | 'metric'>('imperial')
  const [savingUnits, setSavingUnits] = useState(false)

  // Bird info sources state
  const [birdInfoSources, setBirdInfoSources] = useState<string[]>(DEFAULT_BIRD_SOURCES)
  const [savingBirdSources, setSavingBirdSources] = useState(false)

  const taxonomyFileRef = useRef<HTMLInputElement>(null)
  const detectionsFileRef = useRef<HTMLInputElement>(null)

  // App mode (web vs desktop)
  const [isDesktop, setIsDesktop] = useState(false)

  // Check mode and authentication on mount
  useEffect(() => {
    const init = async () => {
      // Check if we're in desktop mode (no auth needed)
      try {
        const info = await settingsApi.getAppInfo()
        if (info.mode === 'desktop') {
          setIsDesktop(true)
          setIsAuthenticated(true)
          loadStations()
          loadSettings()
          loadWeatherData()
          loadDisplaySettings()
          return
        }
      } catch {
        // Fall through to normal auth check
      }

      if (authApi.isAuthenticated()) {
        setIsAuthenticated(true)
        loadStations()
        loadSettings()
        loadWeatherData()
        loadDisplaySettings()
      } else {
        setIsAuthenticated(false)
        setShowPasswordModal(true)
        setLoading(false)
      }
    }
    init()
  }, [])

  const handleAuthSuccess = () => {
    setIsAuthenticated(true)
    setShowPasswordModal(false)
    setLoading(true)
    loadStations()
    loadSettings()
    loadWeatherData()
    loadDisplaySettings()
  }

  const handleLogout = () => {
    authApi.logout()
    setIsAuthenticated(false)
    setShowPasswordModal(true)
  }

  const handlePasswordChangeSuccess = () => {
    setShowChangePasswordModal(false)
    alert('Password changed successfully! Please use the new password next time you log in.')
  }

  const loadDisplaySettings = async () => {
    try {
      const [tempUnit, windUnit, birdSources, autoUpdate] = await Promise.all([
        settingsApi.getTemperatureUnit(),
        settingsApi.getWindSpeedUnit(),
        settingsApi.getBirdInfoSources(),
        settingsApi.getAutoUpdateOnStart(),
      ])
      setTemperatureUnit(tempUnit)
      setWindSpeedUnit(windUnit)
      setBirdInfoSources(birdSources)
      setAutoUpdateOnStart(autoUpdate)

      // Update-check toggle is a generic key in the setting table.
      try {
        const setting = await settingsApi.get('update_check_enabled')
        setUpdateCheckEnabled(
          (setting.value || '').toLowerCase() !== 'false',
        )
      } catch {
        // Default True when the setting doesn't exist yet.
        setUpdateCheckEnabled(true)
      }
    } catch (err) {
      console.error('Failed to load display settings:', err)
    }
  }

  const handleToggleUpdateCheck = async () => {
    const newValue = !updateCheckEnabled
    setUpdateCheckEnabled(newValue)
    setSavingUpdateCheck(true)
    try {
      await settingsApi.update(
        'update_check_enabled',
        String(newValue),
        'bool',
        'Show a banner when a newer release is available on GitHub',
      )
    } catch (err: any) {
      setUpdateCheckEnabled(!newValue)
      alert(`Failed to save: ${err.message || 'Unknown error'}`)
    } finally {
      setSavingUpdateCheck(false)
    }
  }

  const handleToggleAutoUpdate = async () => {
    const newValue = !autoUpdateOnStart
    setAutoUpdateOnStart(newValue)
    setSavingAutoUpdate(true)
    try {
      await settingsApi.setAutoUpdateOnStart(newValue)
    } catch (err: any) {
      setAutoUpdateOnStart(!newValue) // revert on failure
      alert(`Failed to save: ${err.message || 'Unknown error'}`)
    } finally {
      setSavingAutoUpdate(false)
    }
  }

  const handleSaveUnits = async () => {
    try {
      setSavingUnits(true)
      await Promise.all([
        settingsApi.setTemperatureUnit(temperatureUnit),
        settingsApi.setWindSpeedUnit(windSpeedUnit),
      ])
      alert('Display units saved!')
    } catch (err: any) {
      alert(`Failed to save units: ${err.message || 'Unknown error'}`)
    } finally {
      setSavingUnits(false)
    }
  }

  const handleToggleBirdSource = (sourceId: string) => {
    setBirdInfoSources((prev) => {
      if (prev.includes(sourceId)) {
        return prev.filter((s) => s !== sourceId)
      }
      return [...prev, sourceId]
    })
  }

  const handleSaveBirdSources = async () => {
    if (birdInfoSources.length === 0) {
      alert('Please select at least one source.')
      return
    }
    try {
      setSavingBirdSources(true)
      await settingsApi.setBirdInfoSources(birdInfoSources)
      alert('Bird info sources saved!')
    } catch (err: any) {
      alert(`Failed to save bird sources: ${err.message || 'Unknown error'}`)
    } finally {
      setSavingBirdSources(false)
    }
  }

  const handleBirdSourcePreset = async (preset: 'north_america' | 'uk' | 'global') => {
    const presets: Record<string, string[]> = {
      north_america: ['ebird', 'allaboutbirds'],
      uk: ['rspb', 'bto', 'ebird'],
      global: ['ebird', 'wikipedia', 'xenocanto'],
    }
    const sources = presets[preset]
    setBirdInfoSources(sources)
    try {
      setSavingBirdSources(true)
      await settingsApi.setBirdInfoSources(sources)
      alert('Preset applied and saved!')
    } catch (err: any) {
      alert(`Failed to save preset: ${err.message || 'Unknown error'}`)
    } finally {
      setSavingBirdSources(false)
    }
  }

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
      const [stats, dbinfo] = await Promise.all([
        settingsApi.getTaxonomyStats(),
        settingsApi.getDbInfo().catch(() => null),
      ])
      setTaxonomyStats(stats)
      if (stats.current_language) {
        setTaxonomyLanguageState(stats.current_language)
      }
      if (dbinfo) setDbInfo(dbinfo)
    } catch (err) {
      console.error('Failed to load settings:', err)
    }
  }

  const handleExportDatabase = async () => {
    setExportingDb(true)
    try {
      await settingsApi.exportDatabase()
    } catch (err: any) {
      alert(`Export failed: ${err.message || 'Unknown error'}`)
    } finally {
      setExportingDb(false)
    }
  }

  const handleImportDatabase = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const confirmed = window.confirm(
      `This will REPLACE the current database with the contents of "${file.name}". ` +
        `The existing database will be saved as a "pre-restore" backup on the server, ` +
        `but any in-flight changes may be lost. Continue?`,
    )
    if (!confirmed) {
      if (dbImportFileRef.current) dbImportFileRef.current.value = ''
      return
    }
    setImportingDb(true)
    try {
      const result = await settingsApi.importDatabase(file)
      alert(result.message)
      // Reload so the UI pulls everything from the restored DB.
      window.location.reload()
    } catch (err: any) {
      alert(`Import failed: ${err.message || 'Unknown error'}`)
    } finally {
      setImportingDb(false)
      if (dbImportFileRef.current) dbImportFileRef.current.value = ''
    }
  }

  const handleTaxonomyLanguageChange = async (code: string) => {
    const previous = taxonomyLanguage
    setTaxonomyLanguageState(code)
    setSavingTaxonomyLanguage(true)
    try {
      await settingsApi.setTaxonomyLanguage(code)
      // Reload the whole app so every cached API response re-fetches with the new language.
      window.location.reload()
    } catch (err: any) {
      setTaxonomyLanguageState(previous)
      alert(`Failed to change language: ${err.message || 'Unknown error'}`)
    } finally {
      setSavingTaxonomyLanguage(false)
    }
  }

  const loadWeatherData = async () => {
    try {
      const [stats, station] = await Promise.all([
        weatherApi.getStats(),
        weatherApi.getStationSetting(),
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
      alert(`Failed to set weather station: ${err.message || 'Unknown error'}`)
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
      alert(`Failed to sync weather: ${err.message || 'Unknown error'}`)
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
    if (
      !confirm(
        'Are you sure you want to delete this station? All associated detections will be deleted.',
      )
    ) {
      return
    }

    try {
      await stationsApi.delete(id)
      await loadStations()
    } catch (err: any) {
      alert(`Failed to delete station: ${err.message || 'Unknown error'}`)
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
      alert(`Failed to sync: ${err.message || 'Unknown error'}`)
    } finally {
      setSyncing((prev) => ({ ...prev, [stationId]: false }))
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
      alert(`Failed to upload taxonomy: ${err.message || 'Unknown error'}`)
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
    setDetectionProgress(null)
    setDetectionError(null)
    try {
      let lastEvent: DetectionUploadProgressEvent | null = null
      for await (const event of settingsApi.uploadDetectionsStream(file)) {
        if (event.type === 'error') {
          setDetectionError(event.message || 'Upload failed')
          break
        }
        setDetectionProgress(event)
        lastEvent = event
      }
      if (lastEvent?.type === 'complete') {
        await loadStations()
      }
    } catch (err: any) {
      const msg = err.message || 'Unknown error'
      // Convert ms timeouts to seconds for display
      const displayMsg = msg.replace(
        /(\d+)ms/g,
        (_: string, ms: string) => `${Math.round(Number(ms) / 1000)}s`,
      )
      setDetectionError(`Upload failed: ${displayMsg}`)
    } finally {
      setUploadingDetections(false)
      if (detectionsFileRef.current) {
        detectionsFileRef.current.value = ''
      }
    }
  }

  const handleRetryDetections = () => {
    setDetectionProgress(null)
    setDetectionError(null)
    detectionsFileRef.current?.click()
  }

  // Show password modal if not authenticated
  if (showPasswordModal) {
    return <PasswordModal onSuccess={handleAuthSuccess} />
  }

  // Show loading while checking auth or loading data
  if (isAuthenticated === null || loading) {
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
          <SyncAllButton variant="page" disabled={stations.length === 0} />
          <button
            type="button"
            onClick={handleForceFullResync}
            disabled={syncingAll || stations.length === 0}
            title="Walk every station's full BirdWeather history. Use this once to recover detections missed by earlier syncs."
            className="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
          >
            Re-sync full history
          </button>
          <button
            type="button"
            onClick={handleAddStation}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium"
          >
            Add Station
          </button>
          {!isDesktop && (
            <>
              <button
                type="button"
                onClick={() => setShowChangePasswordModal(true)}
                className="bg-amber-100 hover:bg-amber-200 text-amber-800 px-4 py-2 rounded-lg font-medium"
              >
                Change Password
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded-lg font-medium"
              >
                Logout
              </button>
            </>
          )}
        </div>
      </div>

      {/* Change Password Modal */}
      {showChangePasswordModal && (
        <ChangePasswordModal
          onClose={() => setShowChangePasswordModal(false)}
          onSuccess={handlePasswordChangeSuccess}
        />
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Sync Progress Display */}
      {showSyncProgress && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            {syncingAll && (
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent" />
            )}
            <div className="flex-1">
              <p className="font-medium text-blue-900">{syncProgress}</p>
              {syncDetails.length > 0 && (
                <div className="mt-2 text-sm text-blue-800 max-h-40 overflow-y-auto">
                  {syncDetails.map((d, i) => (
                    <div key={i} className="py-1 border-b border-blue-100 last:border-0">
                      {d.station_name}: +{d.detections_added} ({d.status})
                    </div>
                  ))}
                </div>
              )}
            </div>
            {!syncingAll && (
              <button
                type="button"
                onClick={() => setSyncDismissed(true)}
                className="text-blue-600 hover:text-blue-800"
              >
                Close
              </button>
            )}
          </div>
        </div>
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
                  <label htmlFor="station-form-id" className="block text-sm font-medium mb-1">
                    BirdWeather Station ID *
                  </label>
                  <input
                    id="station-form-id"
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
                  <label htmlFor="station-form-name" className="block text-sm font-medium mb-1">
                    Station Name *
                  </label>
                  <input
                    id="station-form-name"
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
                  <label htmlFor="station-form-timezone" className="block text-sm font-medium mb-1">
                    Timezone *
                  </label>
                  <select
                    id="station-form-timezone"
                    name="timezone"
                    value={formData.timezone}
                    onChange={handleInputChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {Intl.supportedValuesOf('timeZone').map((tz) => (
                      <option key={tz} value={tz}>
                        {tz.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
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
                        {station.latitude && station.longitude ? (
                          `${station.latitude.toFixed(4)}, ${station.longitude.toFixed(4)}`
                        ) : (
                          <span className="text-gray-400 italic">Pending sync</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-block px-2 py-1 text-xs font-semibold rounded ${
                            station.active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {station.active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center text-sm text-gray-600">
                        {station.last_update
                          ? new Date(station.last_update).toLocaleString()
                          : 'Never'}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex justify-end space-x-2">
                          <button
                            type="button"
                            onClick={() => handleSyncStation(station.id)}
                            disabled={syncing[station.id]}
                            className="px-3 py-1 text-sm bg-green-100 hover:bg-green-200 text-green-800 rounded font-medium disabled:opacity-50"
                          >
                            {syncing[station.id] ? 'Syncing...' : 'Sync'}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleEditStation(station)}
                            className="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 text-blue-800 rounded font-medium"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
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
            Upload an eBird taxonomy file to enable eBird species codes, family data, and{' '}
            <strong>common names in your language</strong>. The multilingual eBird taxonomy
            (XLSX) includes translations for dozens of languages — once uploaded, choose a
            language below and all plots will use those names.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium mb-2">Upload Taxonomy File</h3>
              <div className="flex items-center space-x-3">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xlsm"
                  onChange={handleTaxonomyUpload}
                  ref={taxonomyFileRef}
                  disabled={uploadingTaxonomy}
                  className="hidden"
                  id="taxonomy-file-input"
                />
                <button
                  type="button"
                  onClick={() => taxonomyFileRef.current?.click()}
                  disabled={uploadingTaxonomy}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
                >
                  {uploadingTaxonomy ? 'Uploading...' : 'Choose CSV or XLSX'}
                </button>
                <span className="text-sm text-gray-500">
                  {taxonomyFileRef.current?.files?.[0]?.name || 'No file selected'}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Download the latest file from the{' '}
                <a
                  href="https://support.ebird.org/en/support/solutions/articles/48000804865#download-common-names"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  eBird taxonomy & common names page
                </a>
                . For localized names, choose the multi-language <code>.xlsx</code>; the plain
                taxonomy <code>.csv</code> only adds species codes.
              </p>

              {/* Language selector */}
              <div className="mt-4">
                <label htmlFor="taxonomy-language" className="block text-sm font-medium mb-1">
                  Common name language
                </label>
                <select
                  id="taxonomy-language"
                  value={taxonomyLanguage}
                  onChange={(e) => handleTaxonomyLanguageChange(e.target.value)}
                  disabled={savingTaxonomyLanguage}
                  className="border rounded-lg px-3 py-2 text-sm w-full max-w-xs"
                >
                  <option value="en">English (default)</option>
                  {(taxonomyStats?.available_languages || []).map((code) => (
                    <option key={code} value={code}>
                      {code}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {taxonomyStats?.available_languages && taxonomyStats.available_languages.length
                    ? `${taxonomyStats.available_languages.length} language(s) available. Changing the selection reloads the app.`
                    : 'Upload the multi-language XLSX file to unlock language choices.'}
                </p>
              </div>
            </div>

            <div>
              <h3 className="font-medium mb-2">Taxonomy Statistics</h3>
              {taxonomyStats ? (
                <div className="space-y-1 text-sm">
                  {taxonomyStats.ebird_entries > 0 && (
                    <p>
                      eBird taxonomy entries:{' '}
                      <span className="font-semibold">
                        {taxonomyStats.ebird_entries.toLocaleString()}
                      </span>
                    </p>
                  )}
                  <p>
                    Species in database:{' '}
                    <span className="font-semibold">
                      {taxonomyStats.total_species.toLocaleString()}
                    </span>
                  </p>
                  <p>
                    With eBird codes:{' '}
                    <span className="font-semibold">
                      {taxonomyStats.species_with_codes.toLocaleString()}
                    </span>{' '}
                    ({taxonomyStats.coverage_percent}%)
                  </p>
                  <p>
                    With family data:{' '}
                    <span className="font-semibold">
                      {taxonomyStats.species_with_families.toLocaleString()}
                    </span>
                  </p>
                  {taxonomyStats.unique_families > 0 && (
                    <p>
                      Unique families:{' '}
                      <span className="font-semibold">{taxonomyStats.unique_families}</span>
                    </p>
                  )}
                  {taxonomyStats.translations_imported !== undefined &&
                    taxonomyStats.translations_imported > 0 && (
                      <p>
                        Localized names:{' '}
                        <span className="font-semibold">
                          {taxonomyStats.translations_imported.toLocaleString()}
                        </span>{' '}
                        across{' '}
                        <span className="font-semibold">
                          {(taxonomyStats.available_languages || []).length}
                        </span>{' '}
                        language(s)
                      </p>
                    )}
                  {taxonomyStats.last_updated && (
                    <p className="text-gray-500">
                      Last updated: {new Date(taxonomyStats.last_updated).toLocaleDateString()}
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

      {/* Database Backup & Restore */}
      {dbInfo?.supported && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4">Database Backup & Restore</h2>
            <p className="text-gray-600 mb-4">
              Download a full copy of your database, or replace the current database with a
              previously downloaded backup. Useful before upgrading, or to move your data to a
              different machine.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-medium mb-2">Download backup</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Save a single <code>.sqlite</code> file containing every station, detection,
                  species, setting, and translation. Keep it somewhere safe — that's your
                  full backup.
                </p>
                <button
                  type="button"
                  onClick={handleExportDatabase}
                  disabled={exportingDb}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
                >
                  {exportingDb ? 'Preparing download…' : 'Download backup'}
                </button>
                {dbInfo.size_bytes ? (
                  <p className="text-xs text-gray-500 mt-2">
                    Current database size: {(dbInfo.size_bytes / (1024 * 1024)).toFixed(1)} MB
                  </p>
                ) : null}
              </div>

              <div>
                <h3 className="font-medium mb-2">Restore from backup</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Replace the <strong>entire</strong> current database with an uploaded{' '}
                  <code>.sqlite</code> file. The previous database is renamed to a
                  <code>.pre-restore-…</code> file on disk as an emergency rollback.
                </p>
                <input
                  type="file"
                  accept=".sqlite,.sqlite3,.db"
                  onChange={handleImportDatabase}
                  ref={dbImportFileRef}
                  disabled={importingDb}
                  className="hidden"
                  id="db-import-file-input"
                />
                <button
                  type="button"
                  onClick={() => dbImportFileRef.current?.click()}
                  disabled={importingDb}
                  className="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
                >
                  {importingDb ? 'Restoring…' : 'Choose backup file to restore'}
                </button>
                <p className="text-xs text-amber-700 mt-2">
                  Warning: the current database is replaced. Make sure you've downloaded a fresh
                  backup first.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manual Detection Upload */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Manual Detection Upload</h2>
          <p className="text-gray-600 mb-4">
            Upload detection data from a CSV file. The CSV should contain columns for: Timestamp,
            Common Name, Scientific Name, Latitude, Longitude, Station, and Confidence.
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
          </div>

          {/* Progress bar */}
          {uploadingDetections && detectionProgress && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>
                  {detectionProgress.type === 'start'
                    ? `Starting... ${detectionProgress.total_lines?.toLocaleString()} lines to process`
                    : `Processing: ${detectionProgress.lines_processed?.toLocaleString()} / ${detectionProgress.total_lines?.toLocaleString()} lines`}
                </span>
                <span>
                  {detectionProgress.detections_added != null &&
                    `${detectionProgress.detections_added.toLocaleString()} added, ${detectionProgress.detections_skipped?.toLocaleString()} skipped`}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-green-600 h-3 rounded-full transition-all duration-300"
                  style={{
                    width: `${detectionProgress.total_lines ? Math.round(((detectionProgress.lines_processed || 0) / detectionProgress.total_lines) * 100) : 0}%`,
                  }}
                />
              </div>
            </div>
          )}

          {/* Completion message */}
          {!uploadingDetections && detectionProgress?.type === 'complete' && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
              {detectionProgress.message}
            </div>
          )}

          {/* Error with retry */}
          {detectionError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{detectionError}</p>
              <button
                type="button"
                onClick={handleRetryDetections}
                className="mt-2 text-sm font-medium text-red-700 hover:text-red-900 underline"
              >
                Try again
              </button>
            </div>
          )}

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
                    .filter((s) => s.latitude && s.longitude && s.latitude !== 0)
                    .map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.latitude?.toFixed(4)}, {s.longitude?.toFixed(4)})
                      </option>
                    ))}
                </select>
                {stations.filter((s) => s.latitude && s.latitude !== 0).length === 0 && (
                  <p className="text-sm text-amber-600">
                    No stations have GPS coordinates. Sync detections first.
                  </p>
                )}
              </div>

              <div className="mt-4">
                <button
                  type="button"
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
                    <p className="text-gray-500">Location: {weatherStats.weather_station}</p>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No weather data</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Sync Settings */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Sync Settings</h2>
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={autoUpdateOnStart}
              onChange={handleToggleAutoUpdate}
              disabled={savingAutoUpdate}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="ml-2 font-medium">Auto-sync stations when app starts</span>
          </label>
          <p className="text-sm text-gray-500 mt-1 ml-6">
            When enabled, all active stations will be synced automatically each time you open the
            app.
          </p>

          <label className="flex items-center cursor-pointer mt-4">
            <input
              type="checkbox"
              checked={updateCheckEnabled}
              onChange={handleToggleUpdateCheck}
              disabled={savingUpdateCheck}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="ml-2 font-medium">Check for app updates</span>
          </label>
          <p className="text-sm text-gray-500 mt-1 ml-6">
            When enabled, the app checks GitHub on startup and shows a banner if a newer
            release is available. Sends one anonymous request to{' '}
            <code>api.github.com</code> every 6 hours; no other tracking.
          </p>
        </div>
      </div>

      {/* Display Units Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Display Units</h2>
          <p className="text-gray-600 mb-4">
            Configure how temperature and wind speed are displayed throughout the application.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium mb-3">Temperature</h3>
              <div className="flex space-x-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="temperatureUnit"
                    checked={temperatureUnit === 'imperial'}
                    onChange={() => setTemperatureUnit('imperial')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="ml-2">°F (Fahrenheit)</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="temperatureUnit"
                    checked={temperatureUnit === 'metric'}
                    onChange={() => setTemperatureUnit('metric')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="ml-2">°C (Celsius)</span>
                </label>
              </div>
            </div>

            <div>
              <h3 className="font-medium mb-3">Wind Speed</h3>
              <div className="flex space-x-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="windSpeedUnit"
                    checked={windSpeedUnit === 'imperial'}
                    onChange={() => setWindSpeedUnit('imperial')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="ml-2">mph</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="windSpeedUnit"
                    checked={windSpeedUnit === 'metric'}
                    onChange={() => setWindSpeedUnit('metric')}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="ml-2">km/h</span>
                </label>
              </div>
            </div>
          </div>

          <div className="mt-4">
            <button
              type="button"
              onClick={handleSaveUnits}
              disabled={savingUnits}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
            >
              {savingUnits ? 'Saving...' : 'Save Unit Preferences'}
            </button>
          </div>
        </div>
      </div>

      {/* Bird Information Sources Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Bird Information Sources</h2>
          <p className="text-gray-600 mb-4">
            Select which bird reference websites to show links for in species displays.
          </p>

          {/* Region groups */}
          {Object.entries(BIRD_SOURCE_REGIONS).map(([region, sourceIds]) => (
            <div key={region} className="mb-4">
              <h3 className="font-medium mb-2 text-gray-700">{region}</h3>
              <div className="flex flex-wrap gap-3">
                {sourceIds.map((sourceId) => {
                  const source = BIRD_INFO_SOURCES[sourceId]
                  if (!source) return null
                  return (
                    <label
                      key={sourceId}
                      className="flex items-center bg-gray-50 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-100"
                      title={source.description}
                    >
                      <input
                        type="checkbox"
                        checked={birdInfoSources.includes(sourceId)}
                        onChange={() => handleToggleBirdSource(sourceId)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <span className="ml-2 text-sm">{source.name}</span>
                    </label>
                  )
                })}
              </div>
            </div>
          ))}

          <div className="flex items-center space-x-3 mt-4">
            <button
              type="button"
              onClick={handleSaveBirdSources}
              disabled={savingBirdSources}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
            >
              {savingBirdSources ? 'Saving...' : 'Save Bird Info Sources'}
            </button>
          </div>

          {/* Quick Presets */}
          <div className="mt-4 pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-600 mb-2">Quick Presets</h4>
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={() => handleBirdSourcePreset('north_america')}
                disabled={savingBirdSources}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-800 rounded font-medium disabled:opacity-50"
              >
                North America
              </button>
              <button
                type="button"
                onClick={() => handleBirdSourcePreset('uk')}
                disabled={savingBirdSources}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-800 rounded font-medium disabled:opacity-50"
              >
                United Kingdom
              </button>
              <button
                type="button"
                onClick={() => handleBirdSourcePreset('global')}
                disabled={savingBirdSources}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-800 rounded font-medium disabled:opacity-50"
              >
                Global
              </button>
            </div>
          </div>

          {/* Currently enabled */}
          <div className="mt-4 text-sm text-gray-500">
            <span className="font-medium">Currently enabled: </span>
            {birdInfoSources.length > 0
              ? birdInfoSources
                  .map((id) => BIRD_INFO_SOURCES[id]?.name)
                  .filter(Boolean)
                  .join(', ')
              : 'None selected'}
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

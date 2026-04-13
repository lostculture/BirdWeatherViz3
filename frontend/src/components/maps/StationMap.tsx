/**
 * Station Map Component
 * Interactive map displaying station locations with auto-fit bounds.
 *
 * Version: 1.0.0
 */

import L from 'leaflet'
import React, { useEffect } from 'react'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { StationStats } from '../../types/api'

// Fix for default marker icons in webpack/vite
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

interface StationWithCoords extends StationStats {
  latitude?: number
  longitude?: number
}

interface StationMapProps {
  stations: StationWithCoords[]
}

// Component to auto-fit bounds to show all stations
const FitBounds: React.FC<{ stations: StationWithCoords[] }> = ({ stations }) => {
  const map = useMap()

  useEffect(() => {
    const stationsWithCoords = stations.filter((s) => s.latitude != null && s.longitude != null)

    if (stationsWithCoords.length > 0) {
      const bounds = L.latLngBounds(
        stationsWithCoords.map((s) => [s.latitude!, s.longitude!] as [number, number]),
      )
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 })
    }
  }, [stations, map])

  return null
}

const StationMap: React.FC<StationMapProps> = ({ stations }) => {
  // Filter stations with valid coordinates
  const stationsWithCoords = stations.filter((s) => s.latitude != null && s.longitude != null)

  if (stationsWithCoords.length === 0) {
    return (
      <div className="h-80 flex items-center justify-center bg-gray-100 rounded-lg">
        <p className="text-muted-foreground">No stations with location data available</p>
      </div>
    )
  }

  // Default center (will be overridden by FitBounds)
  const defaultCenter: [number, number] = [
    stationsWithCoords[0].latitude!,
    stationsWithCoords[0].longitude!,
  ]

  return (
    <div className="h-80 rounded-lg overflow-hidden border">
      <MapContainer
        center={defaultCenter}
        zoom={8}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds stations={stationsWithCoords} />
        {stationsWithCoords.map((station) => (
          <Marker key={station.station_id} position={[station.latitude!, station.longitude!]}>
            <Popup>
              <div className="text-sm">
                <a
                  href={`https://app.birdweather.com/stations/${station.station_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-indigo-600 hover:underline"
                >
                  {station.station_name}
                </a>
                <div className="mt-1 text-gray-600">
                  <div>{station.total_detections.toLocaleString()} detections</div>
                  <div>{station.unique_species} species</div>
                  {station.days_active && <div>{station.days_active} days active</div>}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}

export default StationMap

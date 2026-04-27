/**
 * Navigation Component
 * Top navigation bar with page links.
 * Color palette: Male Indigo Bunting
 *
 * Version: 1.1.0
 */

import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { systemApi } from '../../api'
import SyncAllButton from '../SyncAllButton'

const Navigation: React.FC = () => {
  const location = useLocation()
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    systemApi
      .getInfo()
      .then((info) => setVersion(info.version))
      .catch((err) => console.debug('System info fetch failed:', err))
  }, [])

  const navItems = [
    { path: '/', label: 'Daily Detections' },
    { path: '/species-analysis', label: 'Species Analysis' },
    { path: '/species-details', label: 'Species Details' },
    { path: '/species-list', label: 'Species List' },
    { path: '/stations', label: 'Stations' },
    { path: '/advanced-analytics', label: 'Analytics' },
    { path: '/config', label: 'Config' },
  ]

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <nav className="bg-gradient-to-r from-indigo-deep to-indigo-brilliant text-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-2">
            <span className="text-xl font-bold">BirdWeatherViz3</span>
            {version && <span className="text-sm opacity-80">v{version}</span>}
          </div>
          <div className="flex items-center space-x-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-md transition-colors ${
                  isActive(item.path)
                    ? 'bg-white text-indigo-deep font-medium'
                    : 'hover:bg-white/20'
                }`}
              >
                {item.label}
              </Link>
            ))}
            <div className="ml-2 pl-2 border-l border-white/30">
              <SyncAllButton variant="header" />
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navigation

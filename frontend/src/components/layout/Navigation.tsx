/**
 * Navigation Component
 * Top navigation bar with page links.
 *
 * Version: 1.0.0
 */

import React from 'react'
import { Link, useLocation } from 'react-router-dom'

const Navigation: React.FC = () => {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Daily Detections' },
    { path: '/species-analysis', label: 'Species Analysis' },
    { path: '/species-details', label: 'Species Details' },
    { path: '/species-list', label: 'Species List' },
    { path: '/stations', label: 'Station Comparison' },
    { path: '/config', label: 'Configuration' },
  ]

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <nav className="bg-primary text-primary-foreground shadow-md">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-2">
            <span className="text-xl font-bold">BirdWeatherViz3</span>
            <span className="text-sm opacity-80">v1.0.0</span>
          </div>
          <div className="flex space-x-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-md transition-colors ${
                  isActive(item.path)
                    ? 'bg-primary-foreground text-primary font-medium'
                    : 'hover:bg-primary-foreground/10'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navigation

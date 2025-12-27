/**
 * Layout Component
 * Main application layout with navigation and content area.
 *
 * Version: 1.0.0
 */

import React, { ReactNode } from 'react'
import Navigation from './Navigation'

interface LayoutProps {
  children: ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navigation />
      <main className="flex-1 container mx-auto px-4 py-6">
        {children}
      </main>
      <footer className="bg-muted text-muted-foreground py-4 mt-auto">
        <div className="container mx-auto px-4 text-center text-sm">
          <p>
            BirdWeatherViz3 - Next Generation Bird Detection Visualization
            Platform
          </p>
          <p className="mt-1 opacity-75">
            Powered by BirdWeather API | Version 1.0.0
          </p>
        </div>
      </footer>
    </div>
  )
}

export default Layout

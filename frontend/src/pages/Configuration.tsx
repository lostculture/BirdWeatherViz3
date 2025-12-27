/**
 * Configuration Page
 * Application settings and station management.
 *
 * Version: 1.0.0
 */

import React from 'react'

const Configuration: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Configuration</h1>
        <p className="text-muted-foreground mt-2">
          Manage stations, settings, and notifications
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Settings</h2>
        <p className="text-muted-foreground">
          Configuration interface coming soon in Phase 5. Features will include:
        </p>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground mt-4">
          <li>Station management (add, edit, delete)</li>
          <li>Auto-update settings</li>
          <li>Notification configuration (Apprise)</li>
          <li>Data export options</li>
          <li>Taxonomy upload</li>
          <li>Password-protected access</li>
        </ul>
      </div>
    </div>
  )
}

export default Configuration

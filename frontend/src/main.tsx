/**
 * Frontend Application Entry Point
 * Main entry point for the React application.
 *
 * Version: 1.0.0
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

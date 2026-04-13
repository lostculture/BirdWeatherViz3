/**
 * Vite Configuration
 * Build configuration for the frontend application.
 *
 * Version: 1.0.0
 */

import path from 'path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Ports default to less-conflict-prone values; override with FRONTEND_PORT /
// BACKEND_PORT when 8000/3000 are taken on your machine.
const FRONTEND_PORT = Number(process.env.FRONTEND_PORT) || 5173
const BACKEND_PORT = Number(process.env.BACKEND_PORT) || 8765

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: FRONTEND_PORT,
    host: true,
    proxy: {
      '/api': {
        target: `http://localhost:${BACKEND_PORT}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})

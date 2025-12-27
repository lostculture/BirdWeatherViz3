/**
 * Main Application Component
 * Root component with routing and layout.
 *
 * Version: 1.0.0
 */

import { BrowserRouter } from 'react-router-dom'
import AppRoutes from './routes'
import Layout from './components/layout/Layout'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <AppRoutes />
      </Layout>
    </BrowserRouter>
  )
}

export default App

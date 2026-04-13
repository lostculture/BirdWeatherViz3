/**
 * Main Application Component
 * Root component with routing and layout.
 *
 * Version: 1.1.0
 */

import { BrowserRouter } from 'react-router-dom'
import Layout from './components/layout/Layout'
import { FilterProvider } from './context/FilterContext'
import AppRoutes from './routes'

function App() {
  return (
    <FilterProvider>
      <BrowserRouter>
        <Layout>
          <AppRoutes />
        </Layout>
      </BrowserRouter>
    </FilterProvider>
  )
}

export default App

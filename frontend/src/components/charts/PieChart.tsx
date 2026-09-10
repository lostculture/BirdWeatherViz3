/**
 * Pie Chart Component
 * Wrapper around Plotly.js for pie charts.
 * Color palette: Male Indigo Bunting
 *
 * Version: 1.1.0
 */

import type { Config, Data, Layout } from 'plotly.js'
import React from 'react'
import Plot from 'react-plotly.js'

interface PieChartProps {
  data: Data[]
  layout?: Partial<Layout>
  config?: Partial<Config>
  className?: string
}

const PieChart: React.FC<PieChartProps> = ({ data, layout = {}, config = {}, className = '' }) => {
  const defaultLayout: Partial<Layout> = {
    autosize: true,
    margin: { l: 30, r: 30, t: 30, b: 30 },
    showlegend: true,
    ...layout,
  }

  const defaultConfig: Partial<Config> = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    ...config,
  }

  return (
    <div className={`w-full ${className}`}>
      <Plot
        data={data}
        layout={defaultLayout}
        config={defaultConfig}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
      />
    </div>
  )
}

export default PieChart

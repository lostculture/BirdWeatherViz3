/**
 * Bar Chart Component
 * Wrapper around Plotly.js for bar charts.
 *
 * Version: 1.0.0
 */

import type { Config, Data, Layout } from 'plotly.js'
import React from 'react'
import Plot from 'react-plotly.js'

interface BarChartProps {
  data: Data[]
  layout?: Partial<Layout>
  config?: Partial<Config>
  orientation?: 'v' | 'h'
  className?: string
}

const BarChart: React.FC<BarChartProps> = ({
  data,
  layout = {},
  config = {},
  orientation = 'v',
  className = '',
}) => {
  // Apply orientation to all traces
  const orientedData: Data[] = data.map(
    (trace) =>
      ({
        ...trace,
        type: 'bar' as const,
        orientation,
      }) as Data,
  )

  const defaultLayout: Partial<Layout> = {
    autosize: true,
    margin: { l: 50, r: 30, t: 40, b: 50 },
    hovermode: 'closest',
    showlegend: true,
    barmode: 'group',
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
        data={orientedData}
        layout={defaultLayout}
        config={defaultConfig}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
      />
    </div>
  )
}

export default BarChart

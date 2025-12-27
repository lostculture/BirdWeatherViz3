/**
 * Line Chart Component
 * Wrapper around Plotly.js for line charts.
 *
 * Version: 1.0.0
 */

import React from 'react'
import Plot from 'react-plotly.js'
import type { PlotParams } from 'react-plotly.js'

interface LineChartProps {
  data: PlotParams['data']
  layout?: Partial<PlotParams['layout']>
  config?: Partial<PlotParams['config']>
  className?: string
}

const LineChart: React.FC<LineChartProps> = ({
  data,
  layout = {},
  config = {},
  className = '',
}) => {
  const defaultLayout: Partial<PlotParams['layout']> = {
    autosize: true,
    margin: { l: 50, r: 30, t: 40, b: 50 },
    hovermode: 'closest',
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.2,
    },
    ...layout,
  }

  const defaultConfig: Partial<PlotParams['config']> = {
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

export default LineChart

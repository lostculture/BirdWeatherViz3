/**
 * Bar Chart Component
 * Wrapper around Plotly.js for bar charts.
 *
 * Version: 1.0.0
 */

import React from 'react'
import Plot from 'react-plotly.js'
import type { PlotParams } from 'react-plotly.js'
import type { Data } from 'plotly.js'

interface BarChartProps {
  data: PlotParams['data']
  layout?: Partial<PlotParams['layout']>
  config?: Partial<PlotParams['config']>
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
  const orientedData: Data[] = data.map((trace) => ({
    ...trace,
    type: 'bar' as const,
    orientation,
  }) as Data)

  const defaultLayout: Partial<PlotParams['layout']> = {
    autosize: true,
    margin: { l: 50, r: 30, t: 40, b: 50 },
    hovermode: 'closest',
    showlegend: true,
    barmode: 'group',
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

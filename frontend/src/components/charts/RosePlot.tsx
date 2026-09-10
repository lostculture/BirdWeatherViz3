/**
 * Rose Plot Component
 * Polar bar chart for circular data (e.g., hourly patterns).
 *
 * Version: 1.0.0
 */

import type { Config, Data, Layout } from 'plotly.js'
import React from 'react'
import Plot from 'react-plotly.js'

interface RosePlotProps {
  data: Data[]
  layout?: Partial<Layout>
  config?: Partial<Config>
  className?: string
}

const RosePlot: React.FC<RosePlotProps> = ({ data, layout = {}, config = {}, className = '' }) => {
  // Convert data to polar bar plot format
  const polarData: Data[] = data.map(
    (trace) =>
      ({
        ...trace,
        type: 'barpolar' as const,
      }) as Data,
  )

  const defaultLayout = {
    autosize: true,
    polar: {
      radialaxis: {
        showticklabels: true,
        showline: false,
      },
      angularaxis: {
        showticklabels: true,
        direction: 'clockwise',
        period: 24,
      },
    },
    showlegend: false,
    ...layout,
  } as Partial<Layout>

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
        data={polarData}
        layout={defaultLayout}
        config={defaultConfig}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
      />
    </div>
  )
}

export default RosePlot

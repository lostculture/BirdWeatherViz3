/**
 * Seasonality ridgeline layout
 * Builds the Plotly axis layout for the mirrored-density ("joyplot") chart.
 *
 * Extracted from AdvancedAnalytics so the geometry — which is fiddly and was
 * the source of two reported problems — can be unit tested:
 *
 *  - The chart used `autorange: 'reversed'`, which pads a half band of empty
 *    space above the first species and below the last. The ranges here are
 *    explicit and tight, reversed by ordering the bounds high-to-low.
 *  - A single tall subplot put the only date axis at the very bottom, far off
 *    screen. Species are now laid out in rows of ROW_SIZE, each row carrying
 *    its own x-axis, so one is always in view while scrolling.
 *
 * Version: 1.0.0
 */

/** Species per stacked subplot row. */
export const SEASONALITY_ROW_SIZE = 3
/** Pixel height of one row: its ridgelines plus room for the axis beneath. */
export const SEASONALITY_ROW_HEIGHT = 210
/** Half-height of one species' density band, in y units. */
export const RIDGE_HALF_HEIGHT = 0.4
/** Padding beyond the outermost band. Deliberately small. */
export const RIDGE_PADDING = 0.08

export interface AxisPair {
  /** '' for the first pair, '2', '3', ... for later ones — Plotly's convention. */
  suffix: string
  xaxis: Record<string, unknown>
  yaxis: Record<string, unknown>
}

/**
 * Build the per-row axis definitions for a ridgeline of `speciesNames`.
 *
 * @param speciesNames Species in display order, most detected first.
 * @param xRange       [start, end] of the shared date axis.
 * @param rowSize      Species per row.
 */
export function buildSeasonalityAxes(
  speciesNames: string[],
  xRange: [string, string],
  rowSize: number = SEASONALITY_ROW_SIZE,
): AxisPair[] {
  const rowCount = Math.ceil(speciesNames.length / rowSize)
  if (rowCount === 0) return []

  // Vertical share of a row given over to its x-axis labels, so one row's tick
  // text does not collide with the next row's lowest band.
  const axisGutter = 0.32 / rowCount
  const rowSpan = 1 / rowCount

  const axes: AxisPair[] = []

  for (let row = 0; row < rowCount; row++) {
    const suffix = row === 0 ? '' : String(row + 1)
    const rowSpecies = speciesNames.slice(row * rowSize, (row + 1) * rowSize)

    // Row 0 sits at the top of the figure.
    const domainTop = 1 - row * rowSpan
    const domainBottom = domainTop - rowSpan + axisGutter

    axes.push({
      suffix,
      xaxis: {
        title: { text: 'Time of year', standoff: 6 },
        type: 'date',
        anchor: `y${suffix}`,
        domain: [0, 1],
        tickfont: { size: 10 },
        // Month names only — the data is folded onto one reference year, so
        // showing that year would be actively misleading.
        dtick: 'M1',
        tickformat: '%b',
        // Same window on every row, so the rows read as one chart.
        range: xRange,
      },
      yaxis: {
        tickmode: 'array',
        tickvals: rowSpecies.map((_, i) => i),
        ticktext: rowSpecies,
        tickfont: { size: 10 },
        showgrid: false,
        zeroline: false,
        anchor: `x${suffix}`,
        domain: [Math.max(0, domainBottom), domainTop],
        // Bounds ordered high-to-low keep "most detected at top" while
        // trimming the empty half-band that autorange added at each end.
        range: [
          rowSpecies.length - 1 + RIDGE_HALF_HEIGHT + RIDGE_PADDING,
          -(RIDGE_HALF_HEIGHT + RIDGE_PADDING),
        ],
      },
    })
  }

  return axes
}

/** Which row and in-row slot a species at `index` occupies. */
export function seasonalityPosition(
  index: number,
  rowSize: number = SEASONALITY_ROW_SIZE,
): { rowIndex: number; positionInRow: number; axisSuffix: string } {
  const rowIndex = Math.floor(index / rowSize)
  return {
    rowIndex,
    positionInRow: index % rowSize,
    axisSuffix: rowIndex === 0 ? '' : String(rowIndex + 1),
  }
}

/** Total figure height for a ridgeline of `speciesCount` species. */
export function seasonalityHeight(
  speciesCount: number,
  rowSize: number = SEASONALITY_ROW_SIZE,
): number {
  return Math.ceil(speciesCount / rowSize) * SEASONALITY_ROW_HEIGHT + 60
}

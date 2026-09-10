/**
 * Tests for the seasonality ridgeline layout.
 *
 * Covers the two reported problems directly: the empty bands at the top and
 * bottom of the plot, and the missing repeated x-axis.
 */

import { describe, expect, it } from 'vitest'
import {
  buildSeasonalityAxes,
  RIDGE_HALF_HEIGHT,
  RIDGE_PADDING,
  SEASONALITY_ROW_SIZE,
  seasonalityHeight,
  seasonalityPosition,
} from './seasonalityLayout'

const X_RANGE: [string, string] = ['2026-01-01', '2026-12-31']

const names = (count: number) =>
  Array.from({ length: count }, (_, i) => `Species ${i + 1}`)

describe('buildSeasonalityAxes', () => {
  it('gives every group of three species its own x-axis', () => {
    const axes = buildSeasonalityAxes(names(7), X_RANGE)

    // 7 species at 3 per row = 3 rows, so 3 date axes rather than a single one
    // stranded at the bottom of a tall plot.
    expect(axes).toHaveLength(3)
    expect(axes.map((a) => a.suffix)).toEqual(['', '2', '3'])
    for (const axis of axes) {
      expect(axis.xaxis.type).toBe('date')
      expect(axis.xaxis.range).toEqual(X_RANGE)
    }
  })

  it('uses the same date window on every row', () => {
    const ranges = buildSeasonalityAxes(names(9), X_RANGE).map((a) => a.xaxis.range)
    expect(new Set(ranges.map((r) => JSON.stringify(r))).size).toBe(1)
  })

  it('trims the empty band above the first and below the last species', () => {
    const [axis] = buildSeasonalityAxes(names(3), X_RANGE)
    const range = axis.yaxis.range as [number, number]

    // Bands span baseline +/- RIDGE_HALF_HEIGHT for baselines 0, 1, 2. The
    // range should hug that, not add the half-band autorange used to.
    const expectedSlack = RIDGE_HALF_HEIGHT + RIDGE_PADDING
    expect(range[0]).toBeCloseTo(2 + expectedSlack)
    expect(range[1]).toBeCloseTo(-expectedSlack)

    // The padding beyond the outermost band is a small fraction of a band, not
    // a whole one — that is the gap the report was about.
    expect(RIDGE_PADDING).toBeLessThan(RIDGE_HALF_HEIGHT / 2)
  })

  it('keeps the most-detected species at the top by reversing the bounds', () => {
    const [axis] = buildSeasonalityAxes(names(3), X_RANGE)
    const [low, high] = axis.yaxis.range as [number, number]
    // Descending bounds are how Plotly reverses an axis with an explicit range.
    expect(low).toBeGreaterThan(high)
  })

  it('sizes a short final row to its own species count', () => {
    // 4 species: a full row of 3, then a row holding just one.
    const axes = buildSeasonalityAxes(names(4), X_RANGE)
    expect(axes).toHaveLength(2)

    const lastRange = axes[1].yaxis.range as [number, number]
    const slack = RIDGE_HALF_HEIGHT + RIDGE_PADDING
    // One species means baseline 0 only — no dead space for the two absent rows.
    expect(lastRange[0]).toBeCloseTo(slack)
    expect(lastRange[1]).toBeCloseTo(-slack)
    expect(axes[1].yaxis.ticktext).toEqual(['Species 4'])
  })

  it('stacks rows top-down without overlapping domains', () => {
    const axes = buildSeasonalityAxes(names(9), X_RANGE)
    const domains = axes.map((a) => a.yaxis.domain as [number, number])

    // Row 0 is highest on the figure, and each row sits fully below the last.
    for (let i = 0; i < domains.length; i++) {
      const [bottom, top] = domains[i]
      expect(bottom).toBeGreaterThanOrEqual(0)
      expect(top).toBeLessThanOrEqual(1)
      expect(bottom).toBeLessThan(top)
      if (i > 0) {
        expect(top).toBeLessThanOrEqual(domains[i - 1][0])
      }
    }
  })

  it('anchors each axis to its partner', () => {
    for (const { suffix, xaxis, yaxis } of buildSeasonalityAxes(names(6), X_RANGE)) {
      expect(xaxis.anchor).toBe(`y${suffix}`)
      expect(yaxis.anchor).toBe(`x${suffix}`)
    }
  })

  it('returns nothing for an empty species list', () => {
    expect(buildSeasonalityAxes([], X_RANGE)).toEqual([])
  })
})

describe('seasonalityPosition', () => {
  it('maps indices onto rows of three, using Plotly axis suffixes', () => {
    expect(seasonalityPosition(0)).toEqual({
      rowIndex: 0,
      positionInRow: 0,
      axisSuffix: '',
    })
    expect(seasonalityPosition(2)).toEqual({
      rowIndex: 0,
      positionInRow: 2,
      axisSuffix: '',
    })
    // The first axis pair is "x"/"y"; the second is "x2"/"y2", not "x1"/"y1".
    expect(seasonalityPosition(3)).toEqual({
      rowIndex: 1,
      positionInRow: 0,
      axisSuffix: '2',
    })
    expect(seasonalityPosition(7)).toEqual({
      rowIndex: 2,
      positionInRow: 1,
      axisSuffix: '3',
    })
  })

  it('agrees with the axis list about which row a species belongs to', () => {
    const speciesNames = names(8)
    const axes = buildSeasonalityAxes(speciesNames, X_RANGE)
    speciesNames.forEach((name, idx) => {
      const { rowIndex, positionInRow } = seasonalityPosition(idx)
      expect((axes[rowIndex].yaxis.ticktext as string[])[positionInRow]).toBe(name)
    })
  })
})

describe('seasonalityHeight', () => {
  it('grows a row at a time, not a pixel per species', () => {
    // Three species fit one row, so 1-3 species are the same height.
    expect(seasonalityHeight(1)).toBe(seasonalityHeight(SEASONALITY_ROW_SIZE))
    expect(seasonalityHeight(SEASONALITY_ROW_SIZE + 1)).toBeGreaterThan(
      seasonalityHeight(SEASONALITY_ROW_SIZE),
    )
  })
})

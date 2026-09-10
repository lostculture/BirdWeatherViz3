/**
 * SpeciesCombobox
 * Type-to-filter species picker.
 *
 * A plain <select> is unusable once a station has a few hundred species: you
 * either scroll the whole list or rely on the browser's one-keystroke jump,
 * which only matches the start of the common name. This box filters on both
 * common and scientific name, matches anywhere in the string, and is
 * keyboard-navigable.
 *
 * Version: 1.0.0
 */

import React, { useEffect, useMemo, useRef, useState } from 'react'
import type { SpeciesResponse } from '../types/api'

interface SpeciesComboboxProps {
  species: SpeciesResponse[]
  selectedId: number | null
  onSelect: (speciesId: number) => void
  /** Visible label; also wired up for screen readers. */
  label?: string
  placeholder?: string
  /** Cap on rendered options. Keeps the dropdown quick on very large lists. */
  maxResults?: number
  className?: string
}

const SpeciesCombobox: React.FC<SpeciesComboboxProps> = ({
  species,
  selectedId,
  onSelect,
  label = 'Select Species to Analyze',
  placeholder = 'Type to search by common or scientific name…',
  maxResults = 100,
  className = 'w-full md:w-96',
}) => {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  const selected = useMemo(
    () => species.find((sp) => sp.id === selectedId) ?? null,
    [species, selectedId],
  )

  const matches = useMemo(() => {
    const trimmed = query.trim().toLowerCase()
    const pool = trimmed
      ? species.filter(
          (sp) =>
            sp.common_name.toLowerCase().includes(trimmed) ||
            sp.scientific_name.toLowerCase().includes(trimmed),
        )
      : species
    return pool.slice(0, maxResults)
  }, [species, query, maxResults])

  const truncated = useMemo(() => {
    const trimmed = query.trim().toLowerCase()
    const total = trimmed
      ? species.filter(
          (sp) =>
            sp.common_name.toLowerCase().includes(trimmed) ||
            sp.scientific_name.toLowerCase().includes(trimmed),
        ).length
      : species.length
    return total - matches.length
  }, [species, query, matches.length])

  // Close on an outside click, the usual combobox behaviour.
  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [open])

  // Keep the highlighted option in view while arrowing through a long list.
  useEffect(() => {
    if (!open || !listRef.current) return
    const node = listRef.current.children[highlighted] as HTMLElement | undefined
    node?.scrollIntoView({ block: 'nearest' })
  }, [highlighted, open])

  const commit = (speciesId: number) => {
    onSelect(speciesId)
    setOpen(false)
    setQuery('')
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (!open) {
        setOpen(true)
        setHighlighted(0)
        return
      }
      setHighlighted((i) => Math.min(i + 1, matches.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlighted((i) => Math.max(i - 1, 0))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const choice = matches[highlighted]
      if (choice) commit(choice.id)
    } else if (event.key === 'Escape') {
      setOpen(false)
      setQuery('')
    }
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <label htmlFor="species-combobox" className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>

      <input
        id="species-combobox"
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls="species-combobox-list"
        aria-autocomplete="list"
        autoComplete="off"
        // Show the current selection when idle; swap to the live query as soon
        // as the user starts typing.
        value={open ? query : (selected?.common_name ?? '')}
        placeholder={selected ? placeholder : 'Search species…'}
        onFocus={() => {
          setOpen(true)
          setQuery('')
          setHighlighted(0)
        }}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setHighlighted(0)
        }}
        onKeyDown={handleKeyDown}
        className="w-full p-3 border rounded-lg text-lg focus:ring-2 focus:ring-indigo-brilliant focus:border-indigo-brilliant"
      />

      {selected && !open && (
        <p className="mt-1 text-sm text-gray-500 italic">{selected.scientific_name}</p>
      )}

      {open && (
        <ul
          id="species-combobox-list"
          ref={listRef}
          role="listbox"
          className="absolute z-20 mt-1 w-full max-h-80 overflow-y-auto bg-white border rounded-lg shadow-lg"
        >
          {matches.length === 0 ? (
            <li className="px-4 py-3 text-sm text-gray-500">No species match “{query}”</li>
          ) : (
            matches.map((sp, index) => (
              <li
                key={sp.id}
                role="option"
                aria-selected={sp.id === selectedId}
                onMouseEnter={() => setHighlighted(index)}
                onMouseDown={(e) => {
                  // mousedown, not click: the input's blur would otherwise
                  // close the list before the click lands.
                  e.preventDefault()
                  commit(sp.id)
                }}
                className={`px-4 py-2 cursor-pointer ${
                  index === highlighted ? 'bg-indigo-50' : ''
                } ${sp.id === selectedId ? 'font-semibold' : ''}`}
              >
                <div className="text-sm text-gray-900">{sp.common_name}</div>
                <div className="text-xs text-gray-500 italic">{sp.scientific_name}</div>
              </li>
            ))
          )}
          {truncated > 0 && (
            <li className="px-4 py-2 text-xs text-gray-500 border-t bg-gray-50">
              {truncated.toLocaleString()} more — keep typing to narrow the list
            </li>
          )}
        </ul>
      )}
    </div>
  )
}

export default SpeciesCombobox

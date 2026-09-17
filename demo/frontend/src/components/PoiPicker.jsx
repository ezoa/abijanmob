import { useEffect, useMemo, useRef, useState } from 'react'

// Recherche tolérante : insensible à la casse et aux accents.
export function normaliser(s) {
  return s
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[\u2019']/g, "'")
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ')
}

const MAX_RESULTATS = 30

export default function PoiPicker({ label, pois, selected, onSelect, allowGeo = false, geoBusy = false }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [hi, setHi] = useState(0)
  const boxRef = useRef(null)

  useEffect(() => {
    function onDocClick(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  const index = useMemo(
    () => (pois || []).map((p) => ({ ...p, _n: normaliser(p.label), _nc: normaliser(p.commune) })),
    [pois]
  )
  const nq = normaliser(query)
  const resultats = useMemo(() => {
    if (!nq) return index.slice(0, MAX_RESULTATS)
    return index.filter((p) => p._n.includes(nq) || p._nc.includes(nq)).slice(0, MAX_RESULTATS)
  }, [index, nq])

  const entrees = useMemo(
    () => (allowGeo ? [{ __geo: true }, ...resultats] : resultats),
    [allowGeo, resultats]
  )

  function choisir(entree) {
    setOpen(false)
    setQuery('')
    if (entree.__geo) {
      onSelect({ __geo: true })
      return
    }
    onSelect({ poi_id: entree.id, stop_id: entree.stop_id, label: entree.label })
  }

  function onKey(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setHi((h) => Math.min(h + 1, entrees.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHi((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (open && entrees[hi]) choisir(entrees[hi])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="poi-box" ref={boxRef}>
      <span className="lbl">{label}</span>
      <input
        type="text"
        aria-label={label}
        autoComplete="off"
        value={geoBusy ? '📍 Localisation en cours…' : open ? query : selected?.label || query}
        placeholder="Quartier, gare ou lieu…"
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setHi(0)
        }}
        onFocus={() => {
          setQuery('')
          setOpen(true)
          setHi(0)
        }}
        onKeyDown={onKey}
      />
      {open && (
        <div className="poi-list" role="listbox" aria-label={label}>
          {entrees.length === 0 && <div className="poi-empty">Aucun lieu ne correspond.</div>}
          {entrees.map((p, i) =>
            p.__geo ? (
              <button
                key="__geo"
                type="button"
                role="option"
                aria-selected={i === hi}
                className={`poi-opt ${i === hi ? 'poi-hi' : ''}`}
                onMouseEnter={() => setHi(i)}
                onClick={() => choisir(p)}
              >
                <span className="poi-name poi-geo">📍 Utiliser ma position actuelle</span>
                <span className="poi-meta">Géolocalisation de l'appareil</span>
              </button>
            ) : (
              <button
                key={p.id}
                type="button"
                role="option"
                aria-selected={i === hi}
                className={`poi-opt ${i === hi ? 'poi-hi' : ''}`}
                onMouseEnter={() => setHi(i)}
                onClick={() => choisir(p)}
              >
                <span className="poi-name">{p.label}</span>
                <span className="poi-meta">
                  {p.commune}
                  {p.kind === 'quartier' && p.stop_name ? ` · arrêt ${p.stop_name}` : ''}
                </span>
              </button>
            )
          )}
        </div>
      )}
    </div>
  )
}

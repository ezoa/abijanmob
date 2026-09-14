import { useMemo, useState } from 'react'
import MapView from './MapView.jsx'
import { MODE_ICONS } from '../api.js'

export default function HomeView({ pois, network, vehicles, onSearch }) {
  const [from, setFrom] = useState('riviera2')
  const [to, setTo] = useState('cite_administrative')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const byCommune = useMemo(() => {
    const m = {}
    ;(pois || []).forEach((p) => {
      ;(m[p.commune] = m[p.commune] || []).push(p)
    })
    return m
  }, [pois])

  async function go(f = from, t = to) {
    if (f === t) {
      setError('Le départ et la destination doivent être différents.')
      return
    }
    setError('')
    setBusy(true)
    try {
      await onSearch(f, t)
    } catch (e) {
      setError('Service momentanément indisponible — réessayez.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="screen-pad home">
      <div className="home-hero">
        <div className="hello">Bonjour 👋</div>
        <h1>Où allez-vous&nbsp;?</h1>
        <p className="sub">Itinéraires et tarifs de <b>tous</b> les transports d'Abidjan — gbakas, woro-woro, SOTRA, bateaux-bus.</p>
      </div>

      <div className="search-card">
        <label>
          <span className="lbl">Départ</span>
          <select value={from} onChange={(e) => setFrom(e.target.value)}>
            {Object.entries(byCommune).map(([c, ps]) => (
              <optgroup key={c} label={c}>
                {ps.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <button
          className="swap"
          title="Inverser"
          onClick={() => {
            setFrom(to)
            setTo(from)
          }}
        >
          ⇅
        </button>
        <label>
          <span className="lbl">Destination</span>
          <select value={to} onChange={(e) => setTo(e.target.value)}>
            {Object.entries(byCommune).map(([c, ps]) => (
              <optgroup key={c} label={c}>
                {ps.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        {error && <div className="form-error">{error}</div>}
        <button className="btn-go" disabled={busy} onClick={() => go()}>
          {busy ? 'Recherche…' : 'Rechercher'}
        </button>
      </div>

      <button
        className="demo-chip"
        onClick={() => {
          setFrom('riviera2')
          setTo('cite_administrative')
          go('riviera2', 'cite_administrative')
        }}
      >
        ⚡ Trajet démo : Riviera 2 → Cité Administrative
      </button>

      <div className="home-map">
        <MapView network={network} vehicles={vehicles} />
        <div className="map-legend">
          {[
            ['gbaka', 'Gbakas'],
            ['woro', 'Woro-woro'],
            ['sotra', 'SOTRA'],
            ['bateau', 'Bateau-bus'],
          ].map(([m, label]) => (
            <span key={m}>
              {MODE_ICONS[m]} {label}
            </span>
          ))}
          <span title="Simulation accélérée ×4 pour la démonstration">🔴 Véhicules en direct (×4)</span>
        </div>
      </div>
    </div>
  )
}

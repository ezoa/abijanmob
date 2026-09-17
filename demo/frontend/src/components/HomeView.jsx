import { useMemo, useState } from 'react'
import MapView from './MapView.jsx'
import PoiPicker from './PoiPicker.jsx'
import { MODE_ICONS } from '../api.js'

const DEFAUT_DEPART = { poi_id: 'riviera2', label: 'Riviera 2' }
const DEFAUT_DESTINATION = { poi_id: 'cite_administrative', label: 'Cité Administrative' }

function distanceM(lat1, lon1, lat2, lon2) {
  const r = Math.PI / 180
  const h =
    Math.sin(((lat2 - lat1) * r) / 2) ** 2 +
    Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(((lon2 - lon1) * r) / 2) ** 2
  return 2 * 6371000 * Math.asin(Math.sqrt(h))
}

export default function HomeView({ pois, network, vehicles, onSearch, onSpendings }) {
  const [from, setFrom] = useState(DEFAUT_DEPART)
  const [to, setTo] = useState(DEFAUT_DESTINATION)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [geoBusy, setGeoBusy] = useState(false)

  const stops = useMemo(
    () =>
      (network?.stops?.features || []).map((f) => ({
        id: f.properties.id,
        name: f.properties.name,
        lat: f.geometry.coordinates[1],
        lon: f.geometry.coordinates[0],
      })),
    [network]
  )

  const stopIdOf = (sel) =>
    sel.stop_id || (pois || []).find((p) => p.id === sel.poi_id)?.stop_id

  function useMyPosition() {
    if (!navigator.geolocation) {
      setError('Géolocalisation indisponible sur cet appareil. Choisissez un quartier.')
      return
    }
    setError('')
    setGeoBusy(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        let meilleur = null
        let dMin = Infinity
        for (const s of stops) {
          const d = distanceM(pos.coords.latitude, pos.coords.longitude, s.lat, s.lon)
          if (d < dMin) {
            dMin = d
            meilleur = s
          }
        }
        setGeoBusy(false)
        if (!meilleur) {
          setError('Position inexploitable. Choisissez un quartier.')
          return
        }
        setFrom({ stop_id: meilleur.id, label: `📍 ${meilleur.name} (position actuelle)` })
      },
      () => {
        setGeoBusy(false)
        setError('Position inaccessible : autorisez la géolocalisation ou choisissez un quartier.')
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }
    )
  }

  async function go(f = from, t = to) {
    if (stopIdOf(f) && stopIdOf(f) === stopIdOf(t)) {
      setError('Le départ et la destination doivent être différents.')
      return
    }
    setError('')
    setBusy(true)
    const body = {}
    if (f.poi_id) body.from_poi = f.poi_id
    else if (f.stop_id) body.from_stop = f.stop_id
    if (t.poi_id) body.to_poi = t.poi_id
    else if (t.stop_id) body.to_stop = t.stop_id
    try {
      await onSearch(body)
    } catch (e) {
      setError('Service momentanément indisponible. Réessayez.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="screen-pad home">
      <div className="home-hero">
        <div className="hello">Bonjour 👋</div>
        <h1>Où allez-vous&nbsp;?</h1>
        <p className="sub">Itinéraires et tarifs de <b>tous</b> les transports d'Abidjan : gbakas, woro-woro, SOTRA, bateaux-bus, etc.</p>
      </div>

      <div className="search-card">
        <PoiPicker
          label="Départ"
          pois={pois}
          selected={from}
          allowGeo
          geoBusy={geoBusy}
          onSelect={(sel) => (sel.__geo ? useMyPosition() : setFrom(sel))}
        />
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
        <PoiPicker label="Destination" pois={pois} selected={to} onSelect={setTo} />
        {error && <div className="form-error">{error}</div>}
        <button className="btn-go" disabled={busy} onClick={() => go()}>
          {busy ? 'Recherche…' : 'Rechercher'}
        </button>
      </div>

      <button
        className="demo-chip"
        onClick={() => {
          setFrom(DEFAUT_DEPART)
          setTo(DEFAUT_DESTINATION)
          go(DEFAUT_DEPART, DEFAUT_DESTINATION)
        }}
      >
        ⚡ Trajet démo : Riviera 2 → Cité Administrative
      </button>

      {onSpendings && (
        <button className="home-spendings" onClick={onSpendings}>
          📊 Mes dépenses de transport
        </button>
      )}

      <div className="home-map">
        <MapView network={network} vehicles={vehicles} />
        <div className="map-legend">
          {[
            ['gbaka', 'Gbakas'],
            ['woro', 'Woro-woro'],
            ['sotra', 'SOTRA'],
            ['bateau', 'Bateau-bus'],
            ['taxi_communal', 'Taxis communaux'],
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

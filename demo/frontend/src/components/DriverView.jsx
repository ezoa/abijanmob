import { useEffect, useState } from 'react'
import MapView from './MapView.jsx'
import { fmtF, getJSON } from '../api.js'

const PROVIDER_COLORS = {
  Wave: '#00A9E0',
  'Orange Money': '#FF7900',
  'MTN MoMo': '#FFCC00',
  'Moov Money': '#0066B3',
}

export default function DriverView({ onBack, network, vehicles }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    const load = () =>
      getJSON('/api/driver/drv_001/receipts')
        .then((d) => alive && setData(d))
        .catch(() => alive && setError(true))
    load()
    const t = setInterval(load, 4000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  if (error && !data) return <div className="driver-load">Connexion à l'API impossible…</div>
  if (!data) return <div className="driver-load">Chargement…</div>

  const me = (vehicles || []).find((v) => v.driver_id === 'drv_001')
  const maxProv = Math.max(1, ...Object.values(data.by_provider || {}))

  return (
    <div className="driver">
      <div className="res-head">
        <button className="back" onClick={onBack}>
          ←
        </button>
        <div>
          <div className="res-title">Mode conducteur</div>
          <div className="res-sub">Tableau de bord des recettes</div>
        </div>
        <span className="live-dot" title="En ligne">
          ●
        </span>
      </div>

      <div className="drv-profile">
        <div className="drv-avatar">KA</div>
        <div>
          <div className="drv-name">{data.driver.name}</div>
          <div className="drv-line">
            {data.driver.line} · {data.driver.vehicle}
          </div>
        </div>
      </div>

      {me && (
        <div className="drv-pos">
          <div>
            <div className="drv-pos-title">📍 Position partagée en direct</div>
            <div className="drv-pos-dir">
              {me.line_name} · {me.dir_label}
            </div>
          </div>
          <div className="drv-map">
            <MapView network={network} vehicles={vehicles} dim />
          </div>
          <div className="drv-pos-note">
            Les usagers voient votre véhicule arriver sur leur carte et savent quand se
            présenter à l'arrêt — moins d'attente dans les deux sens.
          </div>
        </div>
      )}

      <div className="drv-stats">
        <div className="stat stat-main">
          <span className="stat-val">{fmtF(data.total)}</span>
          <span className="stat-lbl">recettes du {data.date}</span>
        </div>
        <div className="stat">
          <span className="stat-val">{data.count}</span>
          <span className="stat-lbl">paiements</span>
        </div>
        <div className="stat">
          <span className="stat-val">0 F</span>
          <span className="stat-lbl">monnaie rendue 🎉</span>
        </div>
      </div>

      <div className="drv-provs">
        {(Object.entries(data.by_provider) || []).map(([name, amount]) => (
          <div key={name} className="prov-row">
            <span className="prov-name">
              <span className="prov-dot" style={{ background: PROVIDER_COLORS[name] || '#999' }} />
              {name}
            </span>
            <span className="prov-bar">
              <span style={{ width: `${(amount / maxProv) * 100}%`, background: PROVIDER_COLORS[name] || '#999' }} />
            </span>
            <span className="prov-amt">{fmtF(amount)}</span>
          </div>
        ))}
      </div>

      <div className="drv-list">
        {data.receipts.map((r, i) => (
          <div key={i} className="rcpt">
            <span className="rcpt-time">{r.time_hm}</span>
            <span className="rcpt-line">{r.line_name}</span>
            <span className="rcpt-psp" style={{ background: PROVIDER_COLORS[r.provider] || '#999' }}>
              {r.provider}
            </span>
            <span className="rcpt-fare">{fmtF(r.fare)}</span>
          </div>
        ))}
      </div>

      <div className="flywheel">Chaque paiement apparaît ici en temps réel — fini la crise de monnaie à la descente.</div>
    </div>
  )
}

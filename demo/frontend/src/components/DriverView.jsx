import { useEffect, useState } from 'react'
import MapView from './MapView.jsx'
import StubsTab from './StubsTab.jsx'
import ExpensesTab from './ExpensesTab.jsx'
import TaxesTab from './TaxesTab.jsx'
import ClosureTab from './ClosureTab.jsx'
import { fmtF, fmtSign, getJSON } from '../api.js'

const PROVIDER_COLORS = {
  Wave: '#00A9E0',
  'Orange Money': '#FF7900',
  'MTN MoMo': '#FFCC00',
  'Moov Money': '#0066B3',
}

const TABS = [
  { id: 'overview', label: 'Vue d\u2019ensemble' },
  { id: 'stubs', label: 'Souches' },
  { id: 'expenses', label: 'Dépenses' },
  { id: 'taxes', label: 'Taxes' },
  { id: 'closure', label: 'Clôture' },
]

export default function DriverView({ onBack, network, vehicles }) {
  const [tab, setTab] = useState('overview')
  const [data, setData] = useState(null)
  const [fin, setFin] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    const load = () =>
      getJSON('/api/driver/drv_001/receipts')
        .then((d) => alive && setData(d))
        .catch(() => alive && setError(true))
    const loadFin = () =>
      getJSON('/api/driver/drv_001/financial-summary')
        .then((d) => alive && setFin(d))
        .catch(() => {}) // le dashboard recettes reste utilisable sans le module
    load()
    loadFin()
    const t = setInterval(load, 4000)
    const tf = setInterval(loadFin, 8000)
    return () => {
      alive = false
      clearInterval(t)
      clearInterval(tf)
    }
  }, [])

  if (error && !data) return <div className="driver-load">Connexion à l'API impossible…</div>
  if (!data) return <div className="driver-load">Chargement…</div>

  const me = (vehicles || []).find((v) => v.driver_id === 'drv_001')
  const maxProv = Math.max(1, ...Object.values(data.by_provider || {}))

  return (
    <div className="driver">
      <div className="res-head">
        <button className="back" onClick={onBack} aria-label="Retour">
          ←
        </button>
        <div>
          <div className="res-title">Ma caisse</div>
          <div className="res-sub">Tableau de bord conducteur</div>
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

      <div className="tabbar" role="tablist" aria-label="Sections de la caisse">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={`tab-btn ${tab === t.id ? 'tab-btn-active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="tab-pane tab-scroll">
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
              <span className="stat-val tnum">{fmtF(data.total)}</span>
              <span className="stat-lbl">recettes du {data.date}</span>
            </div>
            <div className="stat">
              <span className="stat-val tnum">{data.count}</span>
              <span className="stat-lbl">paiements</span>
            </div>
            <div className="stat">
              <span className="stat-val">0 F</span>
              <span className="stat-lbl">monnaie rendue 🎉</span>
            </div>
          </div>

          {fin && (
            <div className="fin-grid">
              <div className="stat">
                <span className="stat-val tnum">
                  −{fmtF(fin.today.payment_fees + fin.today.commissions)}
                </span>
                <span className="stat-lbl">frais + commissions (jour) ▼</span>
              </div>
              <div className="stat">
                <span className="stat-val tnum">−{fmtF(fin.today.tax_provisions)}</span>
                <span className="stat-lbl">provisions fiscales ▼</span>
              </div>
              <div className="stat">
                <span className="stat-val tnum">−{fmtF(fin.today.expenses)}</span>
                <span className="stat-lbl">dépenses ▼</span>
              </div>
              <div className="stat">
                <span
                  className={`stat-val tnum ${fin.today.estimated_net_income >= 0 ? 'val-pos' : 'val-neg'}`}
                >
                  {fmtSign(fin.today.estimated_net_income)}
                </span>
                <span className="stat-lbl">
                  bénéfice net estimé {fin.today.estimated_net_income >= 0 ? '▲' : '▼'}
                </span>
              </div>
              <div className="stat">
                <span className="stat-val tnum">{fmtF(fin.week.gross_revenue)}</span>
                <span className="stat-lbl">recettes 7 jours</span>
              </div>
              <div className="stat">
                <span className="stat-val tnum">{fmtF(fin.today.net_to_remit)}</span>
                <span className="stat-lbl">solde à reverser</span>
              </div>
            </div>
          )}

          <div className="drv-provs">
            {(Object.entries(data.by_provider) || []).map(([name, amount]) => (
              <div key={name} className="prov-row">
                <span className="prov-name">
                  <span
                    className="prov-dot"
                    style={{ background: PROVIDER_COLORS[name] || '#999' }}
                  />
                  {name}
                </span>
                <span className="prov-bar">
                  <span
                    style={{
                      width: `${(amount / maxProv) * 100}%`,
                      background: PROVIDER_COLORS[name] || '#999',
                    }}
                  />
                </span>
                <span className="prov-amt tnum">{fmtF(amount)}</span>
              </div>
            ))}
          </div>

          <div className="drv-list">
            {data.receipts.map((r, i) => (
              <div key={i} className="rcpt">
                <span className="rcpt-time">{r.time_hm}</span>
                <span className="rcpt-line">{r.line_name}</span>
                <span
                  className="rcpt-psp"
                  style={{ background: PROVIDER_COLORS[r.provider] || '#999' }}
                >
                  {r.provider}
                </span>
                <span className="rcpt-fare tnum">{fmtF(r.fare)}</span>
              </div>
            ))}
          </div>

          <div className="flywheel">
            Chaque paiement apparaît ici en temps réel — fini la crise de monnaie à la
            descente.
          </div>
        </div>
      )}

      {tab === 'stubs' && <StubsTab />}
      {tab === 'expenses' && <ExpensesTab />}
      {tab === 'taxes' && <TaxesTab />}
      {tab === 'closure' && <ClosureTab />}
    </div>
  )
}

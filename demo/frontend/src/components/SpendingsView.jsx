import { useEffect, useState } from 'react'
import { fmtF, getJSON } from '../api.js'

// Date et heure compactes sur une seule ligne : « 17/09 · 14:30 ».
function fmtCourt(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return (
    d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) +
    ' · ' +
    d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  )
}

const PERIODES = [
  ['day', 'Jour'],
  ['week', 'Semaine'],
  ['month', 'Mois'],
  ['quarter', 'Trimestre'],
]

const PSP = {
  wave: ['Wave', '#00A9E0'],
  orange: ['Orange Money', '#FF7900'],
  mtn: ['MTN MoMo', '#FFCC00'],
  moov: ['Moov Money', '#0066B3'],
}

export default function SpendingsView({ onBack }) {
  const [data, setData] = useState(null)
  const [tx, setTx] = useState(null)
  const [error, setError] = useState(false)
  const [periode, setPeriode] = useState('day')

  useEffect(() => {
    let alive = true
    getJSON('/api/wallets/spending-summary')
      .then((d) => alive && setData(d))
      .catch(() => alive && setError(true))
    getJSON('/api/wallets/transactions?limit=30')
      .then((d) => alive && setTx(d))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  if (error)
    return (
      <div className="driver-load">
        Impossible de charger vos dépenses.
        <button className="btn-ghost" onClick={onBack}>
          ← Retour
        </button>
      </div>
    )
  if (!data) return <div className="driver-load">Chargement…</div>

  const p = data.periods[periode]
  const label = (PERIODES.find(([id]) => id === periode) || [null, 'jour'])[1]
  const ticketMoyen = p.count ? Math.round(p.total / p.count) : 0

  return (
    <div className="spendings">
      <div className="res-head">
        <button className="back" onClick={onBack} aria-label="Retour">
          ←
        </button>
        <div>
          <div className="res-title">Mes dépenses</div>
          <div className="res-sub">Bilan de vos paiements transport (simulation)</div>
        </div>
      </div>

      <div className="periode-chips" role="group" aria-label="Période du bilan">
        {PERIODES.map(([id, l]) => (
          <button
            key={id}
            className={`chip-btn ${periode === id ? 'chip-on' : ''}`}
            onClick={() => setPeriode(id)}
          >
            {l}
          </button>
        ))}
      </div>

      <div className="drv-stats">
        <div className="stat stat-main">
          <span className="stat-val tnum">{fmtF(p.total)}</span>
          <span className="stat-lbl">dépenses ({label.toLowerCase()})</span>
        </div>
        <div className="stat">
          <span className="stat-val tnum">{p.count}</span>
          <span className="stat-lbl">paiements</span>
        </div>
        <div className="stat">
          <span className="stat-val tnum">{fmtF(ticketMoyen)}</span>
          <span className="stat-lbl">ticket moyen</span>
        </div>
      </div>

      {Object.keys(p.by_provider).length > 0 && (
        <div className="drv-provs">
          {Object.entries(p.by_provider).map(([name, montant]) => {
            const couleur = Object.values(PSP).find(([labelP]) => labelP === name)?.[1] || '#999'
            return (
              <div key={name} className="prov-row">
                <span className="prov-name">
                  <span className="prov-dot" style={{ background: couleur }} />
                  {name}
                </span>
                <span className="prov-amt tnum">{fmtF(montant)}</span>
              </div>
            )
          })}
        </div>
      )}

      <div className="closure-title">Derniers paiements</div>
      <div className="drv-list">
        {(tx?.transactions || []).length === 0 && (
          <div className="tab-empty">Aucun paiement pour l'instant.</div>
        )}
        {(tx?.transactions || []).map((t) => {
          const [nomP, couleurP] = PSP[t.provider] || [t.provider, '#999']
          return (
            <div key={t.id} className="rcpt">
              <span className="rcpt-time">{fmtCourt(t.ts)}</span>
              <span className="rcpt-line">{t.line_name || 'Trajet'}</span>
              <span className="rcpt-psp" style={{ background: couleurP }}>
                {nomP}
              </span>
              <span className="rcpt-fare tnum">−{fmtF(t.amount)}</span>
            </div>
          )
        })}
      </div>

      <div className="tab-note">{data.disclaimer}</div>
    </div>
  )
}

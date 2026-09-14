import { useEffect, useState } from 'react'
import { fmtDate, fmtF, getJSON } from '../api.js'

function isoDaysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const TYPE_LABEL = {
  percentage: 'pourcentage',
  fixed_per_trip: 'montant par course',
  fixed_daily: 'forfait journalier (provision)',
  fixed_monthly: 'forfait mensuel (provision)',
  fixed_annual: 'forfait annuel (provision)',
}

export default function TaxesTab() {
  const [from, setFrom] = useState(isoDaysAgo(6))
  const [to, setTo] = useState(isoDaysAgo(0))
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    const p = new URLSearchParams({ date_from: from, date_to: to })
    getJSON('/api/driver/drv_001/tax-summary?' + p.toString())
      .then((d) => alive && setData(d))
      .catch(() => alive && setError(true))
    return () => {
      alive = false
    }
  }, [from, to])

  if (error) return <div className="tab-load">Impossible de charger la synthèse fiscale…</div>
  if (!data) return <div className="tab-load">Chargement…</div>

  return (
    <div className="tab-pane">
      <div className="filter-row">
        <label className="filter-field">
          <span>Du</span>
          <input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label className="filter-field">
          <span>Au</span>
          <input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} />
        </label>
        <div className="exp-total tnum">
          Période : <b>{fmtDate(from)}</b> → <b>{fmtDate(to)}</b>
        </div>
      </div>

      <div className="tax-cards">
        <div className="stat">
          <span className="stat-val tnum">{fmtF(data.totals.operator_taxes)}</span>
          <span className="stat-lbl">taxes par course (démo)</span>
        </div>
        <div className="stat">
          <span className="stat-val tnum">{fmtF(data.totals.estimated_provisions)}</span>
          <span className="stat-lbl">provisions estimées ∝</span>
        </div>
        <div className="stat stat-main">
          <span className="stat-val tnum">{fmtF(data.totals.all)}</span>
          <span className="stat-lbl">total estimé</span>
        </div>
      </div>

      {data.rules.length === 0 && (
        <div className="tab-empty">
          Aucune règle appliquée sur la période (aucune recette, ou règles non applicables).
        </div>
      )}

      <table className="tax-table" aria-label="Synthèse des taxes par règle">
        <thead>
          <tr>
            <th>Règle appliquée</th>
            <th>Autorité</th>
            <th>Calcul</th>
            <th className="ta-r">Courses</th>
            <th className="ta-r">Montant</th>
          </tr>
        </thead>
        <tbody>
          {data.rules.map((r) => (
            <tr key={r.code}>
              <td>
                <div className="tax-label">{r.label}</div>
                {r.is_official ? (
                  <span className="tag tag-official">officielle</span>
                ) : (
                  <span className="tag tag-demo">règle de démonstration</span>
                )}
                {!r.enabled && <span className="tag tag-off">désactivée</span>}
              </td>
              <td>
                <div>{r.authority_name}</div>
                <span className="tax-auth-type">
                  {r.authority_type === 'communal' ? 'communale' : 'étatique'}
                </span>
              </td>
              <td>
                {TYPE_LABEL[r.calculation_type] || r.calculation_type}
                {r.calculation_type === 'percentage' && (
                  <span className="tnum"> ({r.rate} %)</span>
                )}
              </td>
              <td className="ta-r tnum">{r.count}</td>
              <td className="ta-r tnum">
                <b>{fmtF(r.amount)}</b>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="tax-disclaimer" role="note">
        ⚖️ {data.disclaimer}
        <br />
        Les montants « forfait journalier / mensuel / annuel » (marqués ∝) sont des
        <b> provisions estimatives réparties par course</b> — jamais des prélèvements
        légalement exigibles par course. Aucun taux officiel ivoirien n'est codé en dur :
        tout provient des règles configurées, toutes fictives ici (is_official=false).
      </div>
    </div>
  )
}

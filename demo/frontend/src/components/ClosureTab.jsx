import { useEffect, useState } from 'react'
import { fmtDate, fmtF, fmtSign, getJSON, postJSON } from '../api.js'

export default function ClosureTab() {
  const [summary, setSummary] = useState(null)
  const [closures, setClosures] = useState(null)
  const [error, setError] = useState(false)
  const [closing, setClosing] = useState(false)
  const [message, setMessage] = useState('')

  function load() {
    getJSON('/api/driver/drv_001/financial-summary')
      .then(setSummary)
      .catch(() => setError(true))
    getJSON('/api/driver/drv_001/daily-closures')
      .then(setClosures)
      .catch(() => setError(true))
  }

  useEffect(load, [])

  const today = new Date().toISOString().slice(0, 10)
  const alreadyClosed = (closures?.closures || []).some((c) => c.closure_date === today)

  async function closeDay() {
    setClosing(true)
    setMessage('')
    try {
      const r = await postJSON('/api/driver/drv_001/daily-closures', {
        closure_date: today,
      })
      setMessage(
        r.already_closed
          ? 'Journée déjà clôturée — aucun doublon créé.'
          : `Journée clôturée ✓ ${r.closure_number} — résultat net estimé ${fmtF(r.estimated_net_income)}`
      )
      load()
    } catch {
      setMessage('Clôture impossible (API injoignable).')
    }
    setClosing(false)
  }

  if (error) return <div className="tab-load">Impossible de charger les clôtures…</div>
  if (!summary || !closures) return <div className="tab-load">Chargement…</div>

  const t = summary.today

  return (
    <div className="tab-pane">
      <div className="closure-recap" aria-label="Récapitulatif de la journée">
        <div className="closure-title">Récapitulatif du {fmtDate(today)}</div>
        <table className="closure-table tnum">
          <tbody>
            <tr>
              <td>Recettes brutes ({t.payment_count} paiement{t.payment_count > 1 ? 's' : ''})</td>
              <td className="ta-r">
                <b>{fmtF(t.gross_revenue)}</b>
              </td>
            </tr>
            <tr>
              <td>− Frais de paiement</td>
              <td className="ta-r">−{fmtF(t.payment_fees)}</td>
            </tr>
            <tr>
              <td>− Commissions plateforme</td>
              <td className="ta-r">−{fmtF(t.commissions)}</td>
            </tr>
            <tr>
              <td>− Taxes / provisions (estimations démo)</td>
              <td className="ta-r">−{fmtF(t.tax_provisions)}</td>
            </tr>
            <tr>
              <td>− Dépenses saisies</td>
              <td className="ta-r">−{fmtF(t.expenses)}</td>
            </tr>
            <tr className="closure-net">
              <td>= Résultat net estimé</td>
              <td className="ta-r">
                <b>{fmtSign(t.estimated_net_income)}</b>
              </td>
            </tr>
            <tr>
              <td>Solde à reverser (souches en attente)</td>
              <td className="ta-r">{fmtF(t.net_to_remit)}</td>
            </tr>
          </tbody>
        </table>
        <div className="closure-note">{summary.disclaimer}</div>
      </div>

      <button
        className="btn-go closure-btn"
        onClick={closeDay}
        disabled={closing || alreadyClosed}
      >
        {alreadyClosed
          ? '✓ Journée déjà clôturée'
          : closing
            ? 'Clôture en cours…'
            : '📑 Clôturer ma journée'}
      </button>
      {message && (
        <div className="closure-msg" role="status">
          {message}
        </div>
      )}

      <div className="closure-history">
        <div className="closure-title">Historique des clôtures</div>
        {closures.closures.length === 0 && (
          <div className="tab-empty">Aucune clôture enregistrée.</div>
        )}
        {closures.closures.map((c) => (
          <div key={c.closure_date} className="closure-row">
            <span className="tnum">{c.closure_number}</span>
            <span>{fmtDate(c.closure_date)}</span>
            <span className="tnum">
              {c.payment_count} paiement{c.payment_count > 1 ? 's' : ''}
            </span>
            <span className="tnum">{fmtF(c.gross_revenue)}</span>
            <span className={`tnum ${c.estimated_net_income >= 0 ? 'pos' : 'neg'}`}>
              {fmtSign(c.estimated_net_income)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { fmtDateTime, fmtF, getJSON } from '../api.js'

const PROVIDERS = ['Wave', 'Orange Money', 'MTN MoMo', 'Moov Money']
const STATUSES = [
  { value: 'pending', label: 'À reverser' },
  { value: 'settled', label: 'Reversé' },
]

export default function StubsTab() {
  const [filters, setFilters] = useState({ provider: '', status: '', from: '', to: '' })
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  const [openId, setOpenId] = useState(null)
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    const p = new URLSearchParams()
    if (filters.provider) p.set('provider', filters.provider)
    if (filters.status) p.set('settlement_status', filters.status)
    if (filters.from) p.set('date_from', filters.from)
    if (filters.to) p.set('date_to', filters.to)
    let alive = true
    getJSON('/api/driver/drv_001/stubs' + (p.toString() ? '?' + p.toString() : ''))
      .then((d) => alive && setData(d))
      .catch(() => alive && setError(true))
    return () => {
      alive = false
    }
  }, [filters])

  async function toggleDetail(stub) {
    if (openId === stub.id) {
      setOpenId(null)
      setDetail(null)
      return
    }
    setOpenId(stub.id)
    setDetail(null)
    try {
      setDetail(await getJSON(`/api/driver/drv_001/stubs/${stub.id}`))
    } catch {
      setDetail({ error: true })
    }
  }

  if (error) return <div className="tab-load">Impossible de charger les souches…</div>
  if (!data) return <div className="tab-load">Chargement…</div>

  const lines = [...new Set(data.stubs.map((s) => s.line_name))]

  return (
    <div className="tab-pane">
      <div className="filter-row" role="group" aria-label="Filtres des souches">
        <label className="filter-field">
          <span>Du</span>
          <input
            type="date"
            value={filters.from}
            max={filters.to || undefined}
            onChange={(e) => setFilters({ ...filters, from: e.target.value })}
          />
        </label>
        <label className="filter-field">
          <span>Au</span>
          <input
            type="date"
            value={filters.to}
            min={filters.from || undefined}
            onChange={(e) => setFilters({ ...filters, to: e.target.value })}
          />
        </label>
        <label className="filter-field">
          <span>Ligne</span>
          <select
            value={filters.line || ''}
            onChange={(e) => setFilters({ ...filters, line: e.target.value })}
          >
            <option value="">Toutes</option>
            {lines.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Opérateur</span>
          <select
            value={filters.provider}
            onChange={(e) => setFilters({ ...filters, provider: e.target.value })}
          >
            <option value="">Tous</option>
            {PROVIDERS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>Reversement</span>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">Tous</option>
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="stub-totals tnum">
        <span>
          {data.count} souche{data.count > 1 ? 's' : ''}
        </span>
        <span>Brut {fmtF(data.totals.gross_amount)}</span>
        <span>
          Frais + commissions −{fmtF(data.totals.payment_fee + data.totals.platform_fee)}
        </span>
        <span className="stub-net">Net {fmtF(data.totals.net_amount)}</span>
      </div>

      {data.stubs.length === 0 && (
        <div className="tab-empty">Aucune souche pour ces filtres.</div>
      )}

      <div className="stub-list">
        {data.stubs.map((s) => (
          <div key={s.id} className="stub-card">
            <button
              className="stub-head"
              onClick={() => toggleDetail(s)}
              aria-expanded={openId === s.id}
            >
              <span className="stub-num tnum">{s.stub_number}</span>
              <span className="stub-date">{fmtDateTime(s.created_at)}</span>
              <span className="stub-prov">{s.provider}</span>
              <span className={`stub-status ${s.settlement_status}`}>
                {s.settlement_status === 'settled' ? 'Reversé' : 'À reverser'}
              </span>
              <span className="stub-net-amt tnum">{fmtF(s.net_amount)}</span>
              <span className="stub-caret" aria-hidden>
                {openId === s.id ? '▾' : '▸'}
              </span>
            </button>
            {openId === s.id && (
              <div className="stub-detail">
                {!detail && <div className="tab-load">Chargement…</div>}
                {detail?.error && <div className="form-error">Détail indisponible.</div>}
                {detail && !detail.error && (
                  <>
                    <div className="stub-breakdown tnum">
                      <span>Montant brut</span>
                      <b>{fmtF(detail.gross_amount)}</b>
                      <span>− Frais de paiement</span>
                      <b>−{fmtF(detail.payment_fee)}</b>
                      <span>− Commission plateforme</span>
                      <b>−{fmtF(detail.platform_fee)}</b>
                      <span>− Taxes / provisions (démo)</span>
                      <b>−{fmtF(detail.tax_provision)}</b>
                      <span className="stub-net-label">= Net conducteur</span>
                      <b className="stub-net-label">{fmtF(detail.net_amount)}</b>
                    </div>
                    {(detail.taxes || []).length > 0 && (
                      <ul className="stub-taxes">
                        {detail.taxes.map((t, i) => (
                          <li key={i}>
                            <span>{t.label}</span>
                            <span className="tnum">
                              {t.calculation_kind === 'estimated_provision' ? '∝ ' : ''}
                              {fmtF(t.calculated_amount)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                    <div className="stub-note">
                      Souche confirmée. Toute correction passerait par une annulation /
                      remboursement (non implémenté dans ce lot de démonstration).
                      Paiement {detail.payment_id} · transaction {detail.transaction_id}.
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { fmtDate, fmtF, getJSON, postJSON, delJSON } from '../api.js'

const CATEGORIES = [
  ['fuel', '⛽ Carburant'],
  ['maintenance', '🔧 Entretien'],
  ['repair', '🛠️ Réparation'],
  ['tires', '🛞 Pneus'],
  ['insurance', '🛡️ Assurance'],
  ['technical_inspection', '📋 Visite technique'],
  ['parking', '🅿️ Stationnement'],
  ['station_fee', '🚏 Frais de gare'],
  ['toll', '🛣️ Péage'],
  ['washing', '🧼 Lavage'],
  ['union_fee', '🤝 Cotisation syndicale'],
  ['tax', '🏛️ Taxe'],
  ['other', '📌 Autre'],
]
const CAT_LABEL = Object.fromEntries(CATEGORIES)

export default function ExpensesTab() {
  const [category, setCategory] = useState('')
  const [expenses, setExpenses] = useState(null)
  const [error, setError] = useState(false)
  const [form, setForm] = useState({
    category: 'fuel',
    amount: '',
    expense_date: new Date().toISOString().slice(0, 10),
    description: '',
    receipt_reference: '',
  })
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [confirmId, setConfirmId] = useState(null)

  function load() {
    const p = new URLSearchParams()
    if (category) p.set('category', category)
    getJSON('/api/driver/drv_001/expenses' + (p.toString() ? '?' + p.toString() : ''))
      .then(setExpenses)
      .catch(() => setError(true))
  }

  useEffect(load, [category])

  async function add(e) {
    e.preventDefault()
    setFormError('')
    const amount = Number(form.amount)
    if (!Number.isInteger(amount) || amount < 1) {
      setFormError('Montant invalide (entier positif, en FCFA).')
      return
    }
    setSaving(true)
    try {
      await postJSON('/api/driver/drv_001/expenses', {
        category: form.category,
        amount,
        expense_date: form.expense_date,
        description: form.description,
        receipt_reference: form.receipt_reference || null,
      })
      setForm({ ...form, amount: '', description: '', receipt_reference: '' })
      load()
    } catch {
      setFormError('Enregistrement impossible (API injoignable ou données invalides).')
    }
    setSaving(false)
  }

  async function remove(id) {
    setConfirmId(null)
    try {
      await delJSON(`/api/driver/drv_001/expenses/${id}`)
    } catch {
      /* déjà supprimée ou API indisponible : on rafraîchit l'état réel */
    }
    load()
  }

  if (error) return <div className="tab-load">Impossible de charger les dépenses…</div>
  if (!expenses) return <div className="tab-load">Chargement…</div>

  return (
    <div className="tab-pane">
      <form className="exp-form" onSubmit={add} aria-label="Ajouter une dépense">
        <div className="exp-form-row">
          <label className="filter-field">
            <span>Catégorie</span>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              {CATEGORIES.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Date</span>
            <input
              type="date"
              value={form.expense_date}
              onChange={(e) => setForm({ ...form, expense_date: e.target.value })}
            />
          </label>
          <label className="filter-field">
            <span>Montant (FCFA)</span>
            <input
              type="number"
              inputMode="numeric"
              min="1"
              step="1"
              placeholder="4500"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
            />
          </label>
        </div>
        <div className="exp-form-row">
          <label className="filter-field">
            <span>Description</span>
            <input
              type="text"
              maxLength="200"
              placeholder="Ex. plein d'essence (démo)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <label className="filter-field">
            <span>Référence justificatif</span>
            <input
              type="text"
              maxLength="100"
              placeholder="Ex. ticket n° 123 (facultatif)"
              value={form.receipt_reference}
              onChange={(e) => setForm({ ...form, receipt_reference: e.target.value })}
            />
          </label>
        </div>
        {formError && <div className="form-error">{formError}</div>}
        <button className="btn-go exp-add" disabled={saving}>
          {saving ? 'Enregistrement…' : '+ Ajouter la dépense'}
        </button>
      </form>

      <div className="filter-row">
        <label className="filter-field">
          <span>Filtrer par catégorie</span>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">Toutes</option>
            {CATEGORIES.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <div className="exp-total tnum">
          Total : <b>{fmtF(expenses.total)}</b> ({expenses.count})
        </div>
      </div>

      {expenses.expenses.length === 0 && (
        <div className="tab-empty">Aucune dépense enregistrée pour l'instant.</div>
      )}

      <div className="exp-list">
        {expenses.expenses.map((e) => (
          <div key={e.id} className="exp-row">
            <span className="exp-cat">{CAT_LABEL[e.category] || e.category}</span>
            <span className="exp-desc" title={e.description}>
              {e.description || '(non renseignée)'}
            </span>
            <span className="exp-date">{fmtDate(e.expense_date)}</span>
            <span className="exp-amt tnum">−{fmtF(e.amount)}</span>
            {confirmId === e.id ? (
              <span className="exp-confirm" role="alert">
                Supprimer ?
                <button className="exp-del-yes" onClick={() => remove(e.id)}>
                  Oui
                </button>
                <button className="exp-del-no" onClick={() => setConfirmId(null)}>
                  Non
                </button>
              </span>
            ) : (
              <button
                className="exp-del"
                onClick={() => setConfirmId(e.id)}
                aria-label={`Supprimer la dépense ${CAT_LABEL[e.category] || e.category} du ${fmtDate(e.expense_date)}`}
              >
                🗑
              </button>
            )}
          </div>
        ))}
      </div>
      <div className="tab-note">
        Référence de justificatif saisie manuellement : aucun fichier n'est stocké
        par le prototype.
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import Logo from './Logo.jsx'
import { fmtDateTime, fmtF, getJSON } from '../api.js'

// Texte partagé via l'API Web Share (avec repli copie dans le presse-papiers).
function shareText(doc) {
  return (
    `Reçu AbidjanMob ${doc.document_number} · ${fmtF(doc.gross_amount)}` +
    ` · ${doc.line_name}${doc.origin_name ? ` (${doc.origin_name} → ${doc.destination_name})` : ''}` +
    ` · Vérification : ${doc.verify_payload}`
  )
}

export default function ReceiptView({ ticket, onBack, autoPrint = false }) {
  const [doc, setDoc] = useState(null)
  const [error, setError] = useState(false)
  const [shared, setShared] = useState('')

  useEffect(() => {
    let alive = true
    getJSON(`/api/customer/documents/${ticket.document_id}`)
      .then((d) => alive && setDoc(d))
      .catch(() => alive && setError(true))
    return () => {
      alive = false
    }
  }, [ticket.document_id])

  // Impression A4 : seul le document est imprimé (CSS @media print).
  useEffect(() => {
    if (!autoPrint || !doc) return
    const t = setTimeout(() => window.print(), 450)
    return () => clearTimeout(t)
  }, [autoPrint, doc])

  async function share() {
    const text = shareText(doc)
    if (navigator.share) {
      try {
        await navigator.share({ title: `Reçu AbidjanMob ${doc.document_number}`, text })
        setShared('Partagé ✓')
      } catch {
        setShared('') // partage annulé par l'utilisateur
      }
    } else {
      try {
        await navigator.clipboard.writeText(text)
        setShared('Copié dans le presse-papiers ✓')
      } catch {
        setShared('Copie impossible. Notez le numéro ' + doc.document_number)
      }
    }
    setTimeout(() => setShared(''), 4000)
  }

  if (error)
    return (
      <div className="rcp-scroll">
        <div className="rcp-status">
          Reçu indisponible (API injoignable).
          <button className="btn-ghost" onClick={onBack}>
            ← Retour au billet
          </button>
        </div>
      </div>
    )
  if (!doc)
    return (
      <div className="rcp-scroll">
        <div className="rcp-status">Chargement du reçu…</div>
      </div>
    )

  const customerTaxes = (doc.tax_lines || []).filter(
    (t) => t.calculation_kind === 'customer_collected_tax'
  )

  return (
    <div className="rcp-scroll">
      <div className="rcp-actions no-print">
        <button className="btn-ghost" onClick={onBack}>
          ← Retour au billet
        </button>
        <div className="rcp-actions-right">
          <button className="btn-ghost" onClick={() => window.print()}>
            🖨️ Imprimer / PDF
          </button>
          <button className="btn-ghost" onClick={share}>
            📤 Partager
          </button>
        </div>
      </div>
      {shared && <div className="rcp-shared no-print">{shared}</div>}

      <article className="receipt-doc" aria-label="Reçu de transport AbidjanMob">
        <header className="rcp-head">
          <div className="rcp-brand">
            <Logo size={44} />
            <div>
              <div className="rcp-brand-name">
                Abidjan<span>Mob</span>
              </div>
              <div className="rcp-brand-sub">Reçu / facture de transport</div>
            </div>
          </div>
          <div className="rcp-head-meta">
            <div className="rcp-doc-number">{doc.document_number}</div>
            <div className="rcp-doc-date">{fmtDateTime(doc.created_at)}</div>
          </div>
        </header>

        <div className="rcp-banner">
          ⚠️ Prototype de démonstration : document simulé, sans valeur officielle ni fiscale.
        </div>

        <div className="rcp-parties">
          <div>
            <div className="rcp-lbl">Exploitant / conducteur</div>
            <div className="rcp-party">
              <b>{doc.issuer_name}</b>
              <span>{doc.issuer_identifier}</span>
            </div>
          </div>
          <div>
            <div className="rcp-lbl">Client</div>
            <div className="rcp-party">
              <b>{doc.customer_name}</b>
              <span>Payé via {doc.payment_provider}</span>
            </div>
          </div>
        </div>

        <div className="rcp-trip">
          <div className="rcp-lbl">Trajet</div>
          <div className="rcp-trip-line">{doc.line_name}</div>
          {doc.origin_name && (
            <div className="rcp-trip-od">
              <span>{doc.origin_name}</span>
              <span className="rcp-trip-arrow">→</span>
              <span>{doc.destination_name || '(non renseignée)'}</span>
            </div>
          )}
        </div>

        <table className="rcp-amounts">
          <tbody>
            <tr>
              <td>Montant brut (TTC)</td>
              <td className="tnum">{fmtF(doc.gross_amount)}</td>
            </tr>
            {customerTaxes.length > 0 &&
              customerTaxes.map((t) => (
                <tr key={t.code} className="rcp-tax-row">
                  <td>dont {t.label}</td>
                  <td className="tnum">{fmtF(t.calculated_amount)}</td>
                </tr>
              ))}
            {customerTaxes.length > 0 && (
              <tr>
                <td>Net hors taxe (démo)</td>
                <td className="tnum">{fmtF(doc.net_amount)}</td>
              </tr>
            )}
          </tbody>
        </table>

        <div className="rcp-payment">
          <div className="rcp-lbl">Paiement</div>
          <div className="rcp-payment-grid">
            <span>Moyen</span>
            <b>{doc.payment_provider} (simulation)</b>
            <span>Transaction</span>
            <b className="tnum">{doc.transaction_id}</b>
            <span>Billet</span>
            <b className="tnum">{doc.ticket_id}</b>
            <span>Devise</span>
            <b>{doc.currency}</b>
          </div>
        </div>

        <div className="rcp-verify">
          <div className="rcp-qr">
            <QRCodeSVG value={doc.verify_payload} size={104} level="M" />
          </div>
          <div>
            <div className="rcp-verify-title">Vérification AbidjanMob</div>
            <div className="rcp-verify-sub">
              Scannez ce QR (ou saisissez le jeton dans l'application) pour vérifier
              l'authenticité de ce reçu. QR de démonstration AbidjanMob, pas un QR FNE.
            </div>
            <div className="rcp-verify-token tnum">{doc.verification_token}</div>
          </div>
        </div>

        <div className="rcp-fne">
          <span className="rcp-fne-badge">Certification FNE/RNE</span>
          <span>
            <b>non certifié (prototype)</b> · {doc.fne_message}
          </span>
        </div>

        <footer className="rcp-footer">
          Reçu généré par AbidjanMob (prototype de démonstration AIMD 2026) : paiements
          simulés, aucun débit réel. Document {doc.document_number} · paiement {doc.payment_id}.
        </footer>
      </article>
    </div>
  )
}

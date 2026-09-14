import { QRCodeSVG } from 'qrcode.react'
import { fmtF } from '../api.js'

export default function TicketView({ ticket, itinerary, onHome, onDriver }) {
  const lines = (itinerary?.legs || [])
    .filter((l) => l.type === 'ride' && l.mode !== 'taxi')
    .map((l) => l.line_name)

  return (
    <div className="ticket-view">
      <div className="check-wrap">
        <div className="check">✓</div>
        <div className="check-title">Paiement confirmé</div>
        <div className="check-sub">Le conducteur a reçu la confirmation en direct.</div>
      </div>

      <div className="ticket">
        <div className="tk-head">
          <span className="tk-brand">AbidjanMob</span>
          <span className="tk-id">{ticket.ticket_id}</span>
        </div>
        <div className="tk-qr">
          <QRCodeSVG value={ticket.ticket_id} size={120} level="M" />
        </div>
        <div className="tk-lines">{lines.join('  +  ')}</div>
        <div className="tk-row">
          <span>Montant</span>
          <b>{fmtF(ticket.fare)}</b>
        </div>
        <div className="tk-row">
          <span>Payé avec</span>
          <b>{ticket.provider}</b>
        </div>
        <div className="tk-row">
          <span>Heure</span>
          <b>{ticket.time_hm}</b>
        </div>
        <div className="tk-note">Billet numérique — présentez-le en cas de contrôle.</div>
      </div>

      <div className="flywheel">✨ Ce paiement enrichit déjà la carte : ligne, tarif et horodatage enregistrés pour tous les usagers.</div>

      <div className="tk-actions">
        <button className="btn-ghost" onClick={onHome}>
          Nouvelle recherche
        </button>
        <button className="btn-go" onClick={onDriver}>
          👀 Voir côté conducteur
        </button>
      </div>
    </div>
  )
}

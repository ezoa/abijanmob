import { QRCodeSVG } from 'qrcode.react'
import LiveChip from './LiveChip.jsx'
import { fmtF } from '../api.js'

export default function TicketView({ ticket, itinerary, vehicles, stopMap, onHome, onDriver }) {
  const rides = (itinerary?.legs || []).filter((l) => l.type === 'ride' && l.mode !== 'taxi')
  const firstRide = rides[0]
  const hasLive =
    firstRide && (vehicles || []).some((v) => v.line_id === firstRide.line_id)

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
        <div className="tk-lines">{rides.map((l) => l.line_name).join('  +  ')}</div>
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

      {hasLive && firstRide && (
        <LiveChip
          lineId={firstRide.line_id}
          stopId={firstRide.from}
          stopName={stopMap?.[firstRide.from]?.name}
          who={`Votre ${firstRide.mode_label.toLowerCase()}`}
        />
      )}

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

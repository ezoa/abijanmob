import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import LiveChip from './LiveChip.jsx'
import { fmtF } from '../api.js'

function ticketShareText(ticket) {
  return (
    `Billet AbidjanMob ${ticket.ticket_id} · ${fmtF(ticket.fare)}` +
    ` · ${ticket.line_name} · payé avec ${ticket.provider} (simulation)`
  )
}

export default function TicketView({
  ticket,
  itinerary,
  vehicles,
  stopMap,
  onHome,
  onReceipt,
  onPrint,
}) {
  const [shared, setShared] = useState('')
  const rides = (itinerary?.legs || []).filter((l) => l.type === 'ride' && l.mode !== 'taxi')
  const firstRide = rides[0]
  const hasLive = firstRide && (vehicles || []).some((v) => v.line_id === firstRide.line_id)

  async function share() {
    const text = ticketShareText(ticket)
    if (navigator.share) {
      try {
        await navigator.share({ title: `Billet AbidjanMob ${ticket.ticket_id}`, text })
        setShared('Partagé ✓')
      } catch {
        setShared('') // partage annulé
      }
    } else {
      try {
        await navigator.clipboard.writeText(text)
        setShared('Copié dans le presse-papiers ✓')
      } catch {
        setShared('Copie impossible. Notez ' + ticket.ticket_id)
      }
    }
    setTimeout(() => setShared(''), 4000)
  }

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
        {(ticket.splits || []).length > 1 && (
          <div className="tk-row">
            <span>Répartition</span>
            <b className="tnum">
              {ticket.splits.map((s) => `${s.provider} ${fmtF(s.amount)}`).join(' + ')}
            </b>
          </div>
        )}
        <div className="tk-row">
          <span>Heure</span>
          <b>{ticket.time_hm}</b>
        </div>
        {ticket.document_number && (
          <div className="tk-row">
            <span>Reçu</span>
            <b className="tnum">{ticket.document_number}</b>
          </div>
        )}
        {ticket.financial && (
          <div className="tk-row">
            <span>Net conducteur (démo)</span>
            <b className="tnum">{fmtF(ticket.financial.net_amount)}</b>
          </div>
        )}
        <div className="tk-note">Billet numérique. Présentez-le en cas de contrôle.</div>
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

      {shared && <div className="tk-shared">{shared}</div>}

      <div className="tk-actions">
        <button className="btn-go" onClick={onHome}>
          Nouvelle recherche
        </button>
      </div>
      {ticket.document_id && (
        <div className="tk-actions">
          <button className="btn-ghost" onClick={onReceipt}>
            🧾 Voir le reçu
          </button>
          <button className="btn-ghost" onClick={onPrint}>
            🖨️ Imprimer / PDF
          </button>
          <button className="btn-ghost" onClick={share}>
            📤 Partager
          </button>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import MapView from './MapView.jsx'
import { fmtF, MODE_ICONS } from '../api.js'

const TAG_CLASS = {
  'Le plus rapide': 'tag tag-rapide',
  'Le moins cher': 'tag tag-cheap',
  'Réseau formel': 'tag tag-formel',
  'Réseau informel': 'tag tag-informel',
}

function LegRow({ leg, stopMap }) {
  const from = stopMap[leg.from]?.name || leg.from
  const to = stopMap[leg.to]?.name || leg.to
  if (leg.type === 'walk') {
    return (
      <div className="leg leg-walk">
        <span className="leg-bar" style={{ background: '#1A2238' }} />
        <div>
          <div className="leg-title">🚶 Marche {Math.round(leg.min)} min</div>
          <div className="leg-sub">
            {from} → {to} · {Math.round(leg.m)} m
          </div>
        </div>
      </div>
    )
  }
  return (
    <div className="leg">
      <span className="leg-bar" style={{ background: leg.color }} />
      <div>
        <div className="leg-title">
          {MODE_ICONS[leg.mode]} {leg.line_name}
        </div>
        <div className="leg-sub">
          {from} → {to} · attente ~{Math.round(leg.wait_min)} min · trajet {Math.round(leg.ride_min)} min
        </div>
        <div className="leg-sub">
          {leg.mode === 'taxi' ? 'tarif négocié' : `départ ~ toutes les ${leg.headway_min} min`} ·{' '}
          <b>{fmtF(leg.fare)}</b>
        </div>
      </div>
    </div>
  )
}

export default function ResultsView({ plan, selected, onSelect, onPay, onBack, stopMap, network }) {
  const [open, setOpen] = useState(selected?.id || null)
  const transit = (it) => it.legs.some((l) => l.type === 'ride' && l.mode !== 'taxi')

  return (
    <div className="results">
      <div className="res-head">
        <button className="back" onClick={onBack}>
          ←
        </button>
        <div>
          <div className="res-title">
            {plan.from.label} → {plan.to.label}
          </div>
          <div className="res-sub">
            {plan.itineraries.length} options · formel & informel comparés
          </div>
        </div>
      </div>

      <div className="res-map">
        <MapView network={network} itinerary={selected} plan={plan} dim />
      </div>

      <div className="res-list">
        {plan.itineraries.map((it) => (
          <div
            key={it.id}
            className={`it-card ${selected?.id === it.id ? 'it-selected' : ''} ${
              !transit(it) ? 'it-taxi' : ''
            }`}
            onClick={() => onSelect(it)}
          >
            <div className="it-top">
              {it.tag && <span className={TAG_CLASS[it.tag] || 'tag'}>{it.tag}</span>}
              <span className="it-icons">
                {it.legs.map((l, i) => (
                  <span key={i}>{l.type === 'walk' ? '🚶' : MODE_ICONS[l.mode]}</span>
                ))}
              </span>
            </div>
            <div className="it-mid">
              <span className="it-time">{Math.round(it.total_min)} min</span>
              <span className="it-fare">{fmtF(it.fare)}</span>
              <span className="it-corr">
                {it.transfers === 0 ? 'direct' : `${it.transfers} correspondance${it.transfers > 1 ? 's' : ''}`}
              </span>
              {it.co2_saved_g > 0 && <span className="it-co2">−{Math.round(it.co2_saved_g)} g CO₂ vs taxi</span>}
            </div>
            {it.walk_m > 0 && <div className="it-walk">🚶 {Math.round(it.walk_m)} m de marche au total</div>}

            <button className="link-details" onClick={(e) => { e.stopPropagation(); setOpen(open === it.id ? null : it.id) }}>
              {open === it.id ? 'Masquer les détails ▴' : "Détails de l'itinéraire ▾"}
            </button>

            {open === it.id && (
              <div className="legs" onClick={(e) => e.stopPropagation()}>
                {it.legs.map((l, i) => (
                  <LegRow key={i} leg={l} stopMap={stopMap} />
                ))}
              </div>
            )}

            {transit(it) ? (
              <button className="btn-pay" onClick={(e) => { e.stopPropagation(); onPay(it) }}>
                Payer ce trajet · {fmtF(it.fare)}
              </button>
            ) : (
              <div className="it-note">Hors plateforme — estimation pour comparaison</div>
            )}
          </div>
        ))}
        <div className="disclaimer-mini">
          Itinéraires indicatifs (prototype) · tarifs et fréquences à valider terrain
        </div>
      </div>
    </div>
  )
}

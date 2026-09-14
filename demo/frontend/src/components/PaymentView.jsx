import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { fmtF, MODE_ICONS, postJSON } from '../api.js'

const PROVIDERS = [
  { key: 'wave', name: 'Wave', color: '#00A9E0', text: '#fff' },
  { key: 'orange', name: 'Orange Money', color: '#FF7900', text: '#fff' },
  { key: 'mtn', name: 'MTN MoMo', color: '#FFCC00', text: '#1A2238' },
  { key: 'moov', name: 'Moov Money', color: '#0066B3', text: '#fff' },
]

const DRIVER = {
  name: 'Koffi Assamoi',
  line: 'Gbaka Riviera 3 – Adjamé',
  qr: 'ABJMOB|drv_001|gb_riviera_adjamme',
}

export default function PaymentView({ itinerary, onDone, onCancel }) {
  const [step, setStep] = useState('scan')
  const [provider, setProvider] = useState(null)
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')

  const lines = itinerary.legs.filter((l) => l.type === 'ride' && l.mode !== 'taxi')
  const lineNames = lines.map((l) => l.line_name).join(' + ')

  async function confirm() {
    if (pin.length !== 4) return
    setStep('processing')
    await new Promise((r) => setTimeout(r, 1300))
    try {
      const ticket = await postJSON('/api/payments', {
        line_name: lineNames,
        mode: lines[0]?.mode || 'woro',
        fare: itinerary.fare,
        provider: provider.key,
        driver_id: 'drv_001',
      })
      onDone(ticket)
    } catch (e) {
      setError('Paiement refusé (simulation) — réessayez.')
      setStep('pin')
    }
  }

  return (
    <div className="pay">
      <div className="pay-head">
        <button className="back" onClick={step === 'scan' ? onCancel : () => setStep('scan')}>
          ←
        </button>
        <div>
          <div className="res-title">Paiement du trajet</div>
          <div className="res-sub">
            {MODE_ICONS[lines[0]?.mode]} {lineNames}
          </div>
        </div>
      </div>

      <div className="pay-body">
        {step === 'scan' && (
          <div className="scan-step">
            <div className="cam">
              <div className="cam-frame">
                <span className="c1" />
                <span className="c2" />
                <span className="c3" />
                <span className="c4" />
              </div>
              <button className="btn-scan" onClick={() => setTimeout(() => setStep('driver'), 900)}>
                📷 Scanner le QR du conducteur
              </button>
            </div>
            <div className="hint">Chaque conducteur affiche sa carte QR — aucun matériel à installer.</div>
          </div>
        )}

        {step === 'driver' && (
          <div className="driver-card">
            <div className="dc-badge">✓ QR authentifié</div>
            <div className="dc-qr">
              <QRCodeSVG value={DRIVER.qr} size={140} level="M" />
            </div>
            <div className="dc-name">{DRIVER.name}</div>
            <div className="dc-line">{DRIVER.line}</div>
            <div className="dc-fare">
              Montant exact du trajet&nbsp;: <b>{fmtF(itinerary.fare)}</b>
            </div>
            <button className="btn-go" onClick={() => setStep('provider')}>
              Continuer
            </button>
          </div>
        )}

        {step === 'provider' && (
          <div className="prov-step">
            <div className="hint">Choisissez votre opérateur mobile money&nbsp;:</div>
            {PROVIDERS.map((p) => (
              <button
                key={p.key}
                className="prov-btn"
                style={{ borderLeft: `6px solid ${p.color}` }}
                onClick={() => {
                  setProvider(p)
                  setStep('pin')
                }}
              >
                <span>{p.name}</span>
                <span className="prov-arrow">›</span>
              </button>
            ))}
            <div className="hint">Débit du montant exact du trajet — zéro monnaie, zéro friction.</div>
          </div>
        )}

        {step === 'pin' && provider && (
          <div className="pin-step">
            <div className="prov-screen" style={{ background: provider.color, color: provider.text }}>
              <div className="prov-logo">{provider.name}</div>
              <div className="prov-amount">{fmtF(itinerary.fare)}</div>
              <div className="prov-to">pour {DRIVER.name} · {DRIVER.line}</div>
            </div>
            <div className="pin-box">
              <label>Code secret (4 chiffres)</label>
              <input
                type="password"
                inputMode="numeric"
                maxLength={4}
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
                placeholder="••••"
              />
              {error && <div className="form-error">{error}</div>}
              <button className="btn-go" disabled={pin.length !== 4} onClick={confirm}>
                Payer {fmtF(itinerary.fare)}
              </button>
            </div>
          </div>
        )}

        {step === 'processing' && (
          <div className="processing">
            <div className="spinner" />
            <div>Débit en cours…</div>
          </div>
        )}
      </div>

      <div className="sim-badge">SIMULATION — aucun débit réel</div>
    </div>
  )
}

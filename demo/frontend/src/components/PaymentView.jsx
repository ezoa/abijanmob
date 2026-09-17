import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { fmtF, MODE_ICONS, postJSON } from '../api.js'

const PROVIDERS = [
  { key: 'wave', name: 'Wave', color: '#00A9E0', text: '#fff' },
  { key: 'orange', name: 'Orange Money', color: '#FF7900', text: '#fff' },
  { key: 'mtn', name: 'MTN MoMo', color: '#FFCC00', text: '#1A2238' },
  { key: 'moov', name: 'Moov Money', color: '#0066B3', text: '#fff' },
]

const CLE_ORDRE = 'abijanmob_ordre_comptes'

// Ordre de priorité des comptes pour « Remplir automatiquement » (persisté).
function ordreInitial() {
  try {
    const s = JSON.parse(localStorage.getItem(CLE_ORDRE) || '[]')
    if (
      Array.isArray(s) &&
      s.length === PROVIDERS.length &&
      s.every((k) => PROVIDERS.some((p) => p.key === k))
    ) {
      return s.map((k) => PROVIDERS.find((p) => p.key === k))
    }
  } catch {
    /* ordre par défaut */
  }
  return PROVIDERS
}

const DRIVER = {
  name: 'Koffi Assamoi',
  line: 'Gbaka Riviera 3 – Adjamé',
  qr: 'ABJMOB|drv_001|gb_riviera_adjamme',
}

export default function PaymentView({ itinerary, onDone, onCancel }) {
  const [step, setStep] = useState('scan')
  const [pin, setPin] = useState('')
  const [balances, setBalances] = useState(null)
  const [amounts, setAmounts] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [ordre, setOrdre] = useState(ordreInitial)
  const [dragKey, setDragKey] = useState(null)
  const [aideOuverte, setAideOuverte] = useState(false)
  const [rechargePour, setRechargePour] = useState(null)
  const [rechargeMontant, setRechargeMontant] = useState('')
  const [rechargeInfo, setRechargeInfo] = useState('')

  const lines = itinerary.legs.filter((l) => l.type === 'ride' && l.mode !== 'taxi')
  const lineNames = lines.map((l) => l.line_name).join(' + ')
  const fare = itinerary.fare

  function remplirAuto(bal = balances, liste = ordre) {
    const auto = {}
    let restant = fare
    for (const p of liste) {
      const dispo = bal?.[p.key]?.balance || 0
      const prend = Math.min(dispo, restant)
      auto[p.key] = prend > 0 ? String(prend) : ''
      restant -= prend
    }
    setAmounts(auto)
  }

  // Glisser-déposer : réordonner les comptes = changer la priorité de prélèvement.
  function deposer(cibleKey) {
    if (!dragKey || dragKey === cibleKey) {
      setDragKey(null)
      return
    }
    const next = [...ordre]
    const [deplace] = next.splice(
      next.findIndex((p) => p.key === dragKey),
      1
    )
    next.splice(
      next.findIndex((p) => p.key === cibleKey),
      0,
      deplace
    )
    setOrdre(next)
    localStorage.setItem(
      CLE_ORDRE,
      JSON.stringify(next.map((p) => p.key))
    )
    setDragKey(null)
  }

  async function unlock() {
    if (pin.length !== 4) return
    setBusy(true)
    setError('')
    try {
      const r = await postJSON('/api/wallets/unlock', { pin })
      setBalances(r.balances)
      remplirAuto(r.balances)
      setStep('allocate')
    } catch {
      setError('Code invalide ou service indisponible. Réessayez.')
    }
    setBusy(false)
  }

  async function resetWallets() {
    setBusy(true)
    try {
      const r = await postJSON('/api/wallets/reset')
      setBalances(r.balances)
      setAmounts({})
      setError('')
    } catch {
      setError('Réinitialisation impossible.')
    }
    setBusy(false)
  }

  async function recharger(key) {
    const montant = Number(rechargeMontant)
    if (!Number.isInteger(montant) || montant <= 0) return
    setBusy(true)
    setRechargeInfo('')
    try {
      const r = await postJSON('/api/wallets/topup', { pin, provider: key, amount: montant })
      setBalances(r.balances)
      setRechargeInfo(r.message)
      setRechargePour(null)
      setRechargeMontant('')
    } catch {
      setRechargeInfo('Rechargement impossible. Vérifiez le code et le montant.')
    }
    setBusy(false)
  }

  const alloue = PROVIDERS.reduce((s, p) => s + (Number(amounts[p.key]) || 0), 0)
  const totalDispo = PROVIDERS.reduce((s, p) => s + (balances?.[p.key]?.balance || 0), 0)
  const depasse = PROVIDERS.some(
    (p) => (Number(amounts[p.key]) || 0) > (balances?.[p.key]?.balance || 0)
  )
  const complet = alloue === fare

  async function confirm() {
    setStep('processing')
    await new Promise((r) => setTimeout(r, 1300))
    const splits = ordre
      .filter((p) => Number(amounts[p.key]) > 0)
      .map((p) => ({ provider: p.key, amount: Number(amounts[p.key]) }))
    try {
      const ticket = await postJSON('/api/payments', {
        line_name: lineNames,
        mode: lines[0]?.mode || 'woro',
        fare,
        driver_id: 'drv_001',
        line_id: lines[0]?.line_id,
        stop_id: lines[0]?.from,
        dest_stop_id: lines[lines.length - 1]?.to,
        splits,
      })
      onDone(ticket)
    } catch (e) {
      setError('Paiement refusé (soldes insuffisants ?). Ajustez la répartition.')
      try {
        const r = await postJSON('/api/wallets/unlock', { pin })
        setBalances(r.balances)
      } catch {
        /* on garde les soldes connus */
      }
      setStep('allocate')
    }
  }

  return (
    <div className="pay">
      <div className="pay-head">
        <button
          className="back"
          onClick={
            step === 'scan'
              ? onCancel
              : step === 'driver'
                ? () => setStep('scan')
                : step === 'unlock'
                  ? () => setStep('driver')
                  : () => setStep('unlock')
          }
        >
          ←
        </button>
        <div>
          <div className="res-title">Paiement du trajet</div>
          <div className="res-sub">
            {MODE_ICONS[lines[0]?.mode]} {lineNames}
          </div>
        </div>
        <button
          className="tb-btn aide-btn"
          onClick={() => setAideOuverte(true)}
          title="Aide : comptes virtuels, code secret, rechargement, priorités"
        >
          ?
        </button>
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
            <div className="hint">Chaque conducteur affiche sa carte QR. Aucun matériel à installer.</div>
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
              Montant exact du trajet&nbsp;: <b>{fmtF(fare)}</b>
            </div>
            <button className="btn-go" onClick={() => setStep('unlock')}>
              Continuer
            </button>
          </div>
        )}

        {step === 'unlock' && (
          <div className="unlock-step">
            <div className="prov-screen prov-multi">
              <div className="prov-logo">Mes comptes mobile money</div>
              <div className="prov-amount">{fmtF(fare)}</div>
              <div className="prov-to">à payer à {DRIVER.name}</div>
            </div>
            <div className="pin-box">
              <label>Code secret AbidjanMob (4 chiffres)</label>
              <input
                type="password"
                inputMode="numeric"
                maxLength={4}
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
                placeholder="••••"
                autoFocus
              />
              <div className="hint">
                Ce code protège vos portefeuilles virtuels AbidjanMob-Wave, AbidjanMob-Orange
                Money… Ce n'est pas le code de vos applications mobile money. Simulation :
                4 chiffres quelconques.
              </div>
              {error && <div className="form-error">{error}</div>}
              <button className="btn-go" disabled={pin.length !== 4 || busy} onClick={unlock}>
                {busy ? 'Déverrouillage…' : 'Débloquer mes comptes'}
              </button>
            </div>
          </div>
        )}

        {step === 'allocate' && balances && (
          <div className="alloc-step">
            <div className="hint">
              Répartissez le paiement de <b>{fmtF(fare)}</b> entre vos comptes&nbsp;:
              glissez-les pour changer la priorité de prélèvement.
            </div>
            {ordre.map((p) => {
              const dispo = balances[p.key]?.balance || 0
              const montant = Number(amounts[p.key]) || 0
              return (
                <div key={p.key}>
                  <div
                    className={`wa-row ${montant > dispo ? 'wa-over' : ''} ${
                      dragKey === p.key ? 'wa-drag' : ''
                    }`}
                    style={{ borderLeft: `6px solid ${p.color}` }}
                    draggable
                    onDragStart={() => setDragKey(p.key)}
                    onDragEnd={() => setDragKey(null)}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => deposer(p.key)}
                  >
                    <span className="wa-handle" title="Glissez la carte pour changer la priorité">
                      ⠿
                    </span>
                    <div className="wa-info">
                      <span className="wa-name">AbidjanMob-{p.name}</span>
                      <span className="wa-bal tnum">{fmtF(dispo)} disponible</span>
                    </div>
                    <button
                      className="wa-topup-btn"
                      title={`Recharger AbidjanMob-${p.name} depuis votre vrai compte ${p.name} (simulation)`}
                      onClick={() => {
                        setRechargePour(rechargePour === p.key ? null : p.key)
                        setRechargeMontant('')
                        setRechargeInfo('')
                      }}
                    >
                      +
                    </button>
                    <input
                      className="wa-input tnum"
                      type="number"
                      inputMode="numeric"
                      min="0"
                      max={dispo}
                      placeholder="0"
                      value={amounts[p.key] || ''}
                      onChange={(e) => setAmounts({ ...amounts, [p.key]: e.target.value })}
                    />
                  </div>
                  {rechargePour === p.key && (
                    <div className="wa-topup">
                      <span>
                        Rechargez AbidjanMob-{p.name} depuis votre vrai compte {p.name}
                        (simulation).
                      </span>
                      <div className="wa-topup-form">
                        <input
                          type="number"
                          inputMode="numeric"
                          min="1"
                          placeholder="Montant (FCFA)"
                          value={rechargeMontant}
                          onChange={(e) => setRechargeMontant(e.target.value)}
                        />
                        <button
                          className="btn-go"
                          disabled={
                            busy ||
                            !Number.isInteger(Number(rechargeMontant)) ||
                            Number(rechargeMontant) <= 0
                          }
                          onClick={() => recharger(p.key)}
                        >
                          Recharger
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
            <div className={`wa-total tnum ${complet ? 'wa-ok' : ''}`}>
              {complet ? (
                <>✓ Répartition complète : {fmtF(alloue)}</>
              ) : (
                <>Alloué {fmtF(alloue)} · reste {fmtF(fare - alloue)}</>
              )}
            </div>
            {depasse && (
              <div className="form-error">Un montant dépasse le solde disponible du compte.</div>
            )}
            {totalDispo < fare && (
              <div className="form-error">
                Solde total insuffisant ({fmtF(totalDispo)}). Rechargez un compte depuis votre
                vrai compte mobile money (bouton +), ou réinitialisez les soldes.
              </div>
            )}
            {rechargeInfo && <div className="wa-total wa-ok">{rechargeInfo}</div>}
            {error && <div className="form-error">{error}</div>}
            <div className="wa-actions">
              <button
                className="btn-ghost"
                onClick={() => remplirAuto()}
                title="Remplit dans l'ordre d'affichage des comptes : le compte affiché en haut est utilisé en premier, jusqu'à son solde, puis le compte suivant, jusqu'à couvrir le montant exact. Glissez-déposez les comptes pour changer cet ordre."
              >
                Remplir automatiquement
              </button>
              <button
                className="btn-ghost"
                disabled={busy}
                onClick={resetWallets}
                title="Restaure les soldes de départ du compte de démonstration, sans toucher à l'historique."
              >
                ↺ Réinitialiser les soldes
              </button>
            </div>
            <button className="btn-go" disabled={!complet || depasse || busy} onClick={confirm}>
              Payer {fmtF(fare)}
            </button>
          </div>
        )}

        {step === 'processing' && (
          <div className="processing">
            <div className="spinner" />
            <div>Débit en cours…</div>
          </div>
        )}
      </div>

      {aideOuverte && (
        <div className="help-overlay" role="dialog" aria-label="Aide des portefeuilles">
          <div className="help-card">
            <div className="help-head">
              <b>Aide : vos portefeuilles AbidjanMob</b>
              <button className="help-close" onClick={() => setAideOuverte(false)}>
                ✕
              </button>
            </div>
            <div className="help-body">
              <p>
                <b>Des comptes virtuels, pas vos vrais comptes.</b> Wave, Orange Money, MTN et
                Moov ne sont pas interopérables : aucune application ne peut lire ou débiter vos
                comptes chez eux. AbidjanMob ne touche donc jamais à vos vrais comptes. Chaque
                compte affiché ici est un portefeuille virtuel (AbidjanMob-Wave,
                AbidjanMob-Orange Money…) qui vous appartient dans l'application.
              </p>
              <p>
                <b>Le code secret.</b> Le code à 4 chiffres est celui de votre compte AbidjanMob.
                Il donne accès à vos portefeuilles virtuels. Ce n'est pas le code de vos
                applications Orange, Wave, MTN ou Moov, et vous n'avez pas à les saisir ici.
              </p>
              <p>
                <b>Recharger (bouton + sur chaque compte).</b> Pour disposer d'argent sur un
                portefeuille virtuel, rechargez-le depuis votre vrai compte de l'opérateur. Dans
                le prototype c'est une simulation ; dans le MVP, l'API officielle de chaque
                opérateur effectuera le transfert avec votre validation dans votre application
                mobile money.
              </p>
              <p>
                <b>Remplir automatiquement.</b> Le bouton remplit la répartition dans l'ordre
                d'affichage des comptes : le compte affiché en haut est débité en premier,
                jusqu'à concurrence de son solde, puis le compte suivant, jusqu'à couvrir le
                montant exact du trajet.
              </p>
              <p>
                <b>Changer la priorité (glisser-déposer).</b> Faites glisser une carte de compte
                vers le haut ou vers le bas pour changer l'ordre utilisé par « Remplir
                automatiquement ». Votre ordre est mémorisé sur cet appareil.
              </p>
              <p>
                <b>Réinitialiser les soldes.</b> Restaure les soldes de départ du compte de
                démonstration, sans toucher à l'historique.
              </p>
              <p className="help-note">Simulation : aucun débit réel, aucune donnée bancaire.</p>
            </div>
          </div>
        </div>
      )}

      <div className="sim-badge">SIMULATION : aucun débit réel</div>
    </div>
  )
}

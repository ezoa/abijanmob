import { useLineEta, fmtEta } from '../live.js'

export default function LiveChip({ lineId, lineName, stopId, stopName, who }) {
  const eta = useLineEta(lineId, stopId)
  return (
    <div className="live-chip" title="Simulation accélérée ×4 pour la démonstration">
      <span className="live-dot2" />
      <span>
        {who || lineName} — <b>arrive à {stopName} dans {fmtEta(eta?.eta_min)}</b>
        {eta?.eta2_min != null && (
          <span className="live-next"> · puis {fmtEta(eta.eta2_min)}</span>
        )}
      </span>
    </div>
  )
}

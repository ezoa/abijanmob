import { useEffect, useRef, useState } from 'react'
import { getJSON } from './api.js'

function usePoll(fn, ms) {
  const [data, setData] = useState(null)
  const fnRef = useRef(fn)
  fnRef.current = fn
  useEffect(() => {
    let alive = true
    const run = () =>
      fnRef
        .current()
        .then((d) => {
          if (alive) setData(d)
        })
        .catch(() => {})
    run()
    const t = setInterval(run, ms)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [ms])
  return data
}

export const useVehicles = () => usePoll(() => getJSON('/api/drivers/live'), 2000)

export const useLineEta = (lineId, stopId) =>
  usePoll(
    () =>
      lineId && stopId
        ? getJSON(`/api/lines/${lineId}/eta?stop_id=${stopId}`)
        : Promise.resolve(null),
    2500
  )

export const fmtEta = (m) =>
  m == null ? '…' : m <= 0.3 ? "à l'approche 🔴" : `~${Math.max(1, Math.round(m))} min`

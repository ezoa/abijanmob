// URL relative : servie par le proxy Vite (demo.sh) ou nginx (docker compose).
export const API = ''

export async function getJSON(path) {
  const r = await fetch(API + path)
  if (!r.ok) throw new Error('API ' + r.status)
  return r.json()
}

export async function postJSON(path, body) {
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error('API ' + r.status)
  return r.json()
}

export async function delJSON(path) {
  const r = await fetch(API + path, { method: 'DELETE' })
  if (!r.ok) throw new Error('API ' + r.status)
  return r.status === 204 ? null : r.json()
}

export const fmtF = (n) => `${Number(n).toLocaleString('fr-FR')} F`

// Date ISO (2026-09-14) → 14/09/2026 ; datetime ISO → 14/09 21:52
export const fmtDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('fr-FR')
}

export const fmtDateTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.toLocaleDateString('fr-FR')} · ${d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`
}

export const fmtSign = (n) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(Number(n)).toLocaleString('fr-FR')} F`

export const MODE_ICONS = {
  gbaka: '🚐',
  woro: '🚕',
  sotra: '🚌',
  bateau: '⛴️',
  taxi: '🚖',
  taxi_communal: '🚙',
  walk: '🚶',
}

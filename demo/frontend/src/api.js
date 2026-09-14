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

export const fmtF = (n) => `${Number(n).toLocaleString('fr-FR')} F`

export const MODE_ICONS = {
  gbaka: '🚐',
  woro: '🚕',
  sotra: '🚌',
  bateau: '⛴️',
  taxi: '🚖',
  walk: '🚶',
}

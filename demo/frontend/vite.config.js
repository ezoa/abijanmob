import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Le proxy /api permet d'utiliser une URL relative côté navigateur :
// même comportement derrière vite (démo locale) et derrière nginx (docker).
const proxy = { '/api': 'http://127.0.0.1:8000' }

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
})

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Served by Flask at /app/ in production (src/deliver/app.py). In dev, run
// the Flask app on :5000 and `npm run dev` here - API and auth calls are
// proxied so the session cookie stays same-origin.
const flask = 'http://127.0.0.1:5000'

export default defineConfig({
  base: '/app/',
  plugins: [react()],
  server: {
    proxy: { '/api': flask, '/login': flask, '/logout': flask },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/status': 'http://localhost:8000',
      '/result': 'http://localhost:8000',
      '/cancel': 'http://localhost:8000',
      '/generate': 'http://localhost:8000',
      '/cover-letter': 'http://localhost:8000',
      '/cover-letter-pdf': 'http://localhost:8000',
      '/structure': 'http://localhost:8000',
    },
  },
})

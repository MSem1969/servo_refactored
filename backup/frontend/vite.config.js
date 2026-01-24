import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Carica variabili da .env
  const env = loadEnv(mode, process.cwd(), '')

  const apiHost = env.VITE_API_HOST || '127.0.0.1'
  const apiPort = env.VITE_API_PORT || '8000'

  return {
    plugins: [react()],
    server: {
      port: 5174,
      proxy: {
        '/api': {
          target: `http://${apiHost}:${apiPort}`,
          changeOrigin: true,
        }
      }
    }
  }
})

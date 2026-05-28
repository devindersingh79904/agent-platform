import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Load environment variables dynamically to target backend correctly locally and in docker
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '../', '')
  const backendTarget = env.BACKEND_URL || 'http://localhost:8000'
  const wsTarget = backendTarget.replace(/^http/, 'ws')

  return {
    plugins: [
      react(),
      tailwindcss()
    ],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true
        },
        '/ws': {
          target: wsTarget,
          ws: true
        }
      }
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/setupTests.ts'
    }
  }
})

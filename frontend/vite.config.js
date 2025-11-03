import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

/**
 * Read backend port from unified discovery file
 * @returns {string} Backend target URL
 */
function getBackendTarget() {
  const unifiedPortFilePath = path.resolve(process.cwd(), '../.dev-ports.json')
  const defaultTarget = 'http://localhost:54321'

  // Try unified discovery file
  try {
    if (fs.existsSync(unifiedPortFilePath)) {
      const fileContent = fs.readFileSync(unifiedPortFilePath, 'utf8')
      const portData = JSON.parse(fileContent)

      const backendInfo = portData.backend
      if (backendInfo) {
        // Check if file is stale (older than 24 hours)
        const fileAge = Date.now() - (backendInfo.started_at * 1000)
        if (fileAge > 24 * 60 * 60 * 1000) {
          console.warn('Unified port discovery file is stale, using default target:', defaultTarget)
          return defaultTarget
        }

        if (backendInfo.url) {
          console.log('Using backend target from unified discovery file:', backendInfo.url)
          return backendInfo.url
        }

        const discoveredTarget = `http://${backendInfo.host}:${backendInfo.port}`
        console.log('Using backend target from unified discovery file:', discoveredTarget)
        return discoveredTarget
      }
    }
  } catch (error) {
    console.warn('Failed to read unified port discovery file:', error.message)
  }

  console.warn('No unified port discovery file found, using default target:', defaultTarget)
  return defaultTarget
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',  // Écouter sur toutes les interfaces pour l'accès réseau mobile
    port: 5173,
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    },
    proxy: {
      '/api': {
        target: getBackendTarget(),
        changeOrigin: true
      }
    }
  },
  test: {
    environment: 'jsdom',
    isolate: false,
    threads: {
      singleThread: true
    }
  }
})

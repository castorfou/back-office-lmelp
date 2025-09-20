import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

/**
 * Read backend port from discovery file
 * @returns {string} Backend target URL
 */
function getBackendTarget() {
  const portFilePath = path.resolve(process.cwd(), '../.backend-port.json')
  const defaultTarget = 'http://localhost:54321'

  try {
    if (!fs.existsSync(portFilePath)) {
      console.warn('Backend port discovery file not found, using default target:', defaultTarget)
      return defaultTarget
    }

    const fileContent = fs.readFileSync(portFilePath, 'utf8')
    const portData = JSON.parse(fileContent)

    // Check if file is stale (older than 24 hours)
    const fileAge = Date.now() - (portData.timestamp * 1000)
    if (fileAge > 24 * 60 * 60 * 1000) {
      console.warn('Backend port discovery file is stale, using default target:', defaultTarget)
      return defaultTarget
    }

    if (portData.url) {
      console.log('Using backend target from discovery file:', portData.url)
      return portData.url
    }

    const discoveredTarget = `http://${portData.host}:${portData.port}`
    console.log('Using backend target from discovery file:', discoveredTarget)
    return discoveredTarget

  } catch (error) {
    console.warn('Failed to read backend port discovery file:', error.message)
    console.warn('Using default target:', defaultTarget)
    return defaultTarget
  }
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
    proxy: {
      '/api': {
        target: getBackendTarget(),
        changeOrigin: true
      }
    }
  },
  test: {
    environment: 'jsdom'
  }
})

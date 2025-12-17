import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import { memoryGuard } from './utils/memoryGuard.js'

// Logs de démarrage frontend (Issue #136)
console.log('=' + '='.repeat(49))
console.log('🚀 Front-end LMELP')
console.log('=' + '='.repeat(49))
console.log(`📦 Mode: ${import.meta.env.MODE}`)
console.log(`🌐 Base URL: ${import.meta.env.BASE_URL}`)

// Note: Backend URL sera affiché après sa découverte dans les composants qui l'utilisent
console.log('=' + '='.repeat(49))
console.log('')

// Démarrer la surveillance mémoire
console.log('🛡️ Initialisation du garde-fou mémoire frontend')

createApp(App)
  .use(router)
  .mount('#app')

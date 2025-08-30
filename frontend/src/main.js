import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import { memoryGuard } from './utils/memoryGuard.js'

// Démarrer la surveillance mémoire
console.log('🛡️ Initialisation du garde-fou mémoire frontend')

createApp(App).mount('#app')

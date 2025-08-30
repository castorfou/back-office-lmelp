/**
 * Garde-fou mémoire pour le frontend Vue.js
 */

class MemoryGuard {
  constructor(maxMemoryMB = 100, checkIntervalMs = 5000) {
    this.maxMemoryBytes = maxMemoryMB * 1024 * 1024
    this.checkInterval = checkIntervalMs
    this.warningThreshold = this.maxMemoryBytes * 0.8 // 80% = warning
    this.intervalId = null
    this.isMonitoring = false
  }

  /**
   * Obtient l'utilisation mémoire actuelle (si disponible)
   */
  getMemoryUsage() {
    if (performance.memory) {
      return {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      }
    }
    return null
  }

  /**
   * Vérifie si la limite mémoire est dépassée
   */
  checkMemoryLimit() {
    const memory = this.getMemoryUsage()
    if (!memory) {
      return null // API non disponible dans ce navigateur
    }

    const currentMB = memory.used / (1024 * 1024)
    const maxMB = this.maxMemoryBytes / (1024 * 1024)

    if (memory.used > this.maxMemoryBytes) {
      return `LIMITE MÉMOIRE DÉPASSÉE: ${currentMB.toFixed(1)}MB > ${maxMB}MB`
    } else if (memory.used > this.warningThreshold) {
      const percentage = (memory.used / this.maxMemoryBytes * 100).toFixed(1)
      return `AVERTISSEMENT MÉMOIRE: ${currentMB.toFixed(1)}MB / ${maxMB}MB (${percentage}%)`
    }

    return null
  }

  /**
   * Force le nettoyage et l'arrêt de l'application
   */
  forceShutdown(reason) {
    console.error(`🚨 ARRÊT D'URGENCE: ${reason}`)
    const memory = this.getMemoryUsage()
    if (memory) {
      console.error(`Mémoire actuelle: ${(memory.used / (1024 * 1024)).toFixed(1)}MB`)
    }
    console.error('Application fermée pour éviter un crash navigateur')

    // Nettoyer les ressources
    this.stopMonitoring()

    // Forcer le garbage collector si possible
    if (window.gc) {
      try {
        window.gc()
      } catch (e) {
        // Ignoré
      }
    }

    // Afficher un message à l'utilisateur
    alert('⚠️ Limite mémoire dépassée - Application fermée pour votre sécurité')

    // Rediriger vers une page d'erreur ou recharger
    window.location.reload()
  }

  /**
   * Démarre la surveillance mémoire
   */
  startMonitoring() {
    if (this.isMonitoring) return

    this.isMonitoring = true
    this.intervalId = setInterval(() => {
      const memoryCheck = this.checkMemoryLimit()
      if (memoryCheck) {
        if (memoryCheck.includes('LIMITE MÉMOIRE DÉPASSÉE')) {
          this.forceShutdown(memoryCheck)
        } else {
          console.warn(`⚠️ ${memoryCheck}`)
        }
      }
    }, this.checkInterval)

    console.log(`🛡️ Surveillance mémoire activée (limite: ${this.maxMemoryBytes / (1024 * 1024)}MB)`)
  }

  /**
   * Arrête la surveillance mémoire
   */
  stopMonitoring() {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }
    this.isMonitoring = false
    console.log('🛡️ Surveillance mémoire désactivée')
  }

  /**
   * Obtient des statistiques mémoire formatées
   */
  getMemoryStats() {
    const memory = this.getMemoryUsage()
    if (!memory) {
      return 'Statistiques mémoire non disponibles dans ce navigateur'
    }

    return {
      used: `${(memory.used / (1024 * 1024)).toFixed(1)} MB`,
      total: `${(memory.total / (1024 * 1024)).toFixed(1)} MB`,
      limit: `${(memory.limit / (1024 * 1024)).toFixed(1)} MB`,
      percentage: `${((memory.used / memory.limit) * 100).toFixed(1)}%`
    }
  }
}

// Instance globale
export const memoryGuard = new MemoryGuard(100, 5000) // 100MB, vérification toutes les 5s

// Démarrer automatiquement la surveillance
if (typeof window !== 'undefined') {
  memoryGuard.startMonitoring()
}

export default MemoryGuard

"""Garde-fou mémoire pour éviter les fuites."""

import psutil


class MemoryGuard:
    """Surveille et limite l'utilisation mémoire."""

    def __init__(self, max_memory_mb: int = 1000, check_interval: int = 10):
        """
        Initialise le garde-fou mémoire.

        Args:
            max_memory_mb: Limite mémoire en MB (défaut: 1000MB)
            check_interval: Intervalle de vérification en secondes
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.check_interval = check_interval
        self.process = psutil.Process()
        self.warning_threshold = self.max_memory_bytes * 0.8  # 80% = warning

    def get_memory_usage(self) -> int:
        """Retourne l'utilisation mémoire actuelle en bytes."""
        return int(self.process.memory_info().rss)

    def get_memory_usage_mb(self) -> float:
        """Retourne l'utilisation mémoire actuelle en MB."""
        return self.get_memory_usage() / (1024 * 1024)

    def check_memory_limit(self) -> str | None:
        """
        Vérifie si la limite mémoire est dépassée.

        Returns:
            Message d'erreur si limite dépassée, None sinon
        """
        current_memory = self.get_memory_usage()
        current_mb = current_memory / (1024 * 1024)
        max_mb = self.max_memory_bytes / (1024 * 1024)

        if current_memory > self.max_memory_bytes:
            return f"LIMITE MÉMOIRE DÉPASSÉE: {current_mb:.1f}MB > {max_mb}MB"
        if current_memory > self.warning_threshold:
            return f"AVERTISSEMENT MÉMOIRE: {current_mb:.1f}MB / {max_mb}MB ({current_mb / max_mb * 100:.1f}%)"

        return None

    def force_shutdown(self, reason: str) -> None:
        """Force l'arrêt de l'application de manière plus gracieuse."""
        print(f"🚨 ARRÊT D'URGENCE: {reason}")
        print(f"Mémoire actuelle: {self.get_memory_usage_mb():.1f}MB")
        print("Application fermée pour éviter un crash système")

        # Nettoyer les ressources
        try:
            # Forcer le garbage collector
            import gc

            gc.collect()
            print("🧹 Garbage collector exécuté")
        except Exception:
            pass

        # Essayer d'arrêter le serveur proprement si possible
        try:
            # Importer ici pour éviter les dépendances circulaires
            from back_office_lmelp.app import _server_instance

            if _server_instance is not None:
                _server_instance.should_exit = True
                print("📡 Signal d'arrêt envoyé au serveur")
                # Donner un peu de temps pour l'arrêt gracieux
                import time

                time.sleep(0.5)
        except ImportError:
            # Si on ne peut pas importer (par exemple dans les tests),
            # on continue avec l'arrêt normal
            pass
        except Exception as e:
            print(f"⚠️ Erreur lors de l'arrêt gracieux: {e}")

        # Arrêt via exception plutôt qu'os._exit pour permettre le cleanup
        raise SystemExit(1)


# Instance globale
memory_guard = MemoryGuard(max_memory_mb=1000)

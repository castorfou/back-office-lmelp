<template>
  <nav class="navigation" v-if="showNavigation">
    <div class="nav-content">
      <!-- Lien vers l'accueil -->
      <router-link
        to="/"
        class="nav-link home-link"
        data-testid="home-link"
      >
        <span class="nav-icon">🏠</span>
        Accueil
      </router-link>

      <!-- Titre de la page courante -->
      <div class="page-title" v-if="pageTitle">
        {{ pageTitle }}
      </div>
    </div>
  </nav>
</template>

<script>
export default {
  name: 'Navigation',

  props: {
    pageTitle: {
      type: String,
      default: null
    }
  },

  computed: {
    showNavigation() {
      // Ne pas afficher la navigation sur la page d'accueil
      return this.$route.path !== '/';
    }
  }
};
</script>

<style scoped>
.navigation {
  background: white;
  border-bottom: 1px solid #e0e0e0;
  padding: 1rem 0;
  margin-bottom: 2rem;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.nav-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.nav-link:hover {
  background: #f0f2ff;
  color: #5a67d8;
}

.nav-icon {
  font-size: 1.1rem;
}

.page-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin-left: auto;
}

/* Responsive Design */
@media (max-width: 768px) {
  .nav-content {
    padding: 0 1rem;
  }

  .page-title {
    font-size: 1rem;
  }

  .nav-link {
    font-size: 0.9rem;
    padding: 0.4rem 0.8rem;
  }
}

@media (max-width: 480px) {
  .nav-content {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }

  .page-title {
    margin-left: 0;
    font-size: 0.9rem;
  }
}
</style>

<template>
  <div class="babelio-test">
    <Navigation page-title="Test Babelio" />

    <main class="test-content">
      <!-- Bandeau d'information -->
      <section class="info-banner">
        <h1>🔍 Test du service Babelio</h1>
        <p>
          Testez la vérification orthographique des auteurs, livres et éditeurs via l'API Babelio.
          Ce service permet de corriger automatiquement les fautes de frappe et d'obtenir les informations officielles.
        </p>
      </section>

      <!-- Formulaires de test -->
      <section class="test-forms">
        <!-- Test Auteur -->
        <div class="test-form-card">
          <h2>✍️ Vérifier un auteur</h2>
          <form @submit.prevent="verifyAuthor" class="test-form">
            <div class="form-group">
              <label for="author-name">Nom de l'auteur :</label>
              <input
                id="author-name"
                v-model="forms.author.name"
                type="text"
                placeholder="ex: Amélie Notombe (avec faute)"
                :disabled="loading.author"
                class="form-input"
              />
            </div>
            <button
              type="submit"
              :disabled="!forms.author.name || loading.author"
              class="submit-button"
              :class="{ loading: loading.author }"
            >
              {{ loading.author ? 'Vérification...' : 'Vérifier l\'auteur' }}
            </button>
          </form>

          <div v-if="results.author" class="result-card">
            <h3>Résultat :</h3>
            <pre class="result-content">{{ JSON.stringify(results.author, null, 2) }}</pre>
          </div>
        </div>

        <!-- Test Livre -->
        <div class="test-form-card">
          <h2>📚 Vérifier un livre</h2>
          <form @submit.prevent="verifyBook" class="test-form">
            <div class="form-group">
              <label for="book-title">Titre du livre :</label>
              <input
                id="book-title"
                v-model="forms.book.title"
                type="text"
                placeholder="ex: Le petite prince (avec faute)"
                :disabled="loading.book"
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label for="book-author">Auteur (optionnel) :</label>
              <input
                id="book-author"
                v-model="forms.book.author"
                type="text"
                placeholder="ex: Antoine de Saint-Exupéry"
                :disabled="loading.book"
                class="form-input"
              />
            </div>
            <button
              type="submit"
              :disabled="!forms.book.title || loading.book"
              class="submit-button"
              :class="{ loading: loading.book }"
            >
              {{ loading.book ? 'Vérification...' : 'Vérifier le livre' }}
            </button>
          </form>

          <div v-if="results.book" class="result-card">
            <h3>Résultat :</h3>
            <pre class="result-content">{{ JSON.stringify(results.book, null, 2) }}</pre>
          </div>
        </div>

        <!-- Test Éditeur -->
        <div class="test-form-card">
          <h2>🏢 Vérifier un éditeur</h2>
          <form @submit.prevent="verifyPublisher" class="test-form">
            <div class="form-group">
              <label for="publisher-name">Nom de l'éditeur :</label>
              <input
                id="publisher-name"
                v-model="forms.publisher.name"
                type="text"
                placeholder="ex: Galimard (avec faute)"
                :disabled="loading.publisher"
                class="form-input"
              />
            </div>
            <button
              type="submit"
              :disabled="!forms.publisher.name || loading.publisher"
              class="submit-button"
              :class="{ loading: loading.publisher }"
            >
              {{ loading.publisher ? 'Vérification...' : 'Vérifier l\'éditeur' }}
            </button>
          </form>

          <div v-if="results.publisher" class="result-card">
            <h3>Résultat :</h3>
            <pre class="result-content">{{ JSON.stringify(results.publisher, null, 2) }}</pre>
          </div>
        </div>
      </section>

      <!-- Messages d'erreur -->
      <div v-if="error" class="error-banner">
        <h3>❌ Erreur</h3>
        <p>{{ error }}</p>
      </div>

      <!-- Guide d'utilisation -->
      <section class="usage-guide">
        <h2>💡 Guide d'utilisation</h2>
        <div class="guide-content">
          <div class="guide-item">
            <h3>✍️ Test Auteur</h3>
            <p>Entrez le nom d'un auteur (même avec des fautes) pour obtenir la correction orthographique et les informations depuis Babelio.</p>
          </div>
          <div class="guide-item">
            <h3>📚 Test Livre</h3>
            <p>Entrez le titre d'un livre (obligatoire) et éventuellement l'auteur pour affiner la recherche.</p>
          </div>
          <div class="guide-item">
            <h3>🏢 Test Éditeur</h3>
            <p>Entrez le nom d'un éditeur pour vérifier l'orthographe et obtenir le nom officiel.</p>
          </div>
          <div class="guide-item">
            <h3>🔍 Résultats</h3>
            <p>Chaque test retourne un objet JSON avec : la correction suggérée, le niveau de confiance, et les données trouvées sur Babelio.</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import Navigation from '../components/Navigation.vue';
import axios from 'axios';

export default {
  name: 'BabelioTest',
  components: {
    Navigation
  },

  data() {
    return {
      forms: {
        author: {
          name: ''
        },
        book: {
          title: '',
          author: ''
        },
        publisher: {
          name: ''
        }
      },
      results: {
        author: null,
        book: null,
        publisher: null
      },
      loading: {
        author: false,
        book: false,
        publisher: false
      },
      error: null
    };
  },

  methods: {
    async verifyAuthor() {
      this.loading.author = true;
      this.error = null;
      this.results.author = null;

      try {
        const response = await axios.post('/api/verify-babelio', {
          type: 'author',
          name: this.forms.author.name
        });

        this.results.author = response.data;
      } catch (error) {
        console.error('Erreur lors de la vérification de l\'auteur:', error);
        this.error = `Erreur lors de la vérification de l'auteur: ${error.response?.data?.detail || error.message}`;
      } finally {
        this.loading.author = false;
      }
    },

    async verifyBook() {
      this.loading.book = true;
      this.error = null;
      this.results.book = null;

      try {
        const requestData = {
          type: 'book',
          title: this.forms.book.title
        };

        // Ajouter l'auteur s'il est fourni
        if (this.forms.book.author.trim()) {
          requestData.author = this.forms.book.author;
        }

        const response = await axios.post('/api/verify-babelio', requestData);
        this.results.book = response.data;
      } catch (error) {
        console.error('Erreur lors de la vérification du livre:', error);
        this.error = `Erreur lors de la vérification du livre: ${error.response?.data?.detail || error.message}`;
      } finally {
        this.loading.book = false;
      }
    },

    async verifyPublisher() {
      this.loading.publisher = true;
      this.error = null;
      this.results.publisher = null;

      try {
        const response = await axios.post('/api/verify-babelio', {
          type: 'publisher',
          name: this.forms.publisher.name
        });

        this.results.publisher = response.data;
      } catch (error) {
        console.error('Erreur lors de la vérification de l\'éditeur:', error);
        this.error = `Erreur lors de la vérification de l'éditeur: ${error.response?.data?.detail || error.message}`;
      } finally {
        this.loading.publisher = false;
      }
    }
  }
};
</script>

<style scoped>
.babelio-test {
  min-height: 100vh;
  background: #f8f9fa;
}

.test-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.info-banner {
  text-align: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem;
  border-radius: 12px;
  margin-bottom: 2rem;
}

.info-banner h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  font-weight: 700;
}

.info-banner p {
  font-size: 1.1rem;
  opacity: 0.9;
  line-height: 1.6;
  max-width: 800px;
  margin: 0 auto;
}

.test-forms {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

.test-form-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 2rem;
}

.test-form-card h2 {
  font-size: 1.3rem;
  margin-bottom: 1.5rem;
  color: #333;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.test-form {
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.form-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.submit-button {
  width: 100%;
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.submit-button:hover:not(:disabled) {
  background: #5a67d8;
  transform: translateY(-1px);
}

.submit-button:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
  transform: none;
}

.submit-button.loading {
  background: #a0aec0;
}

.result-card {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.result-card h3 {
  margin-bottom: 0.5rem;
  color: #333;
  font-size: 1.1rem;
}

.result-content {
  background: #fff;
  padding: 1rem;
  border-radius: 6px;
  font-size: 0.9rem;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.error-banner {
  background: #fed7d7;
  border: 1px solid #feb2b2;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 2rem;
}

.error-banner h3 {
  color: #c53030;
  margin-bottom: 0.5rem;
}

.error-banner p {
  color: #742a2a;
  margin: 0;
}

.usage-guide {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 2rem;
}

.usage-guide h2 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  color: #333;
  text-align: center;
}

.guide-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.guide-item {
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.guide-item h3 {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
  color: #333;
}

.guide-item p {
  color: #666;
  font-size: 0.9rem;
  line-height: 1.4;
  margin: 0;
}

/* Responsive Design */
@media (max-width: 768px) {
  .test-content {
    padding: 1rem;
  }

  .info-banner {
    padding: 1.5rem;
  }

  .info-banner h1 {
    font-size: 2rem;
  }

  .test-forms {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .test-form-card {
    padding: 1.5rem;
  }

  .guide-content {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
}

@media (max-width: 480px) {
  .info-banner h1 {
    font-size: 1.5rem;
  }

  .info-banner p {
    font-size: 1rem;
  }

  .test-form-card {
    padding: 1rem;
  }
}
</style>

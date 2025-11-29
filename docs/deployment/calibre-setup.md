# Configuration Calibre en Production

## Vue d'ensemble

L'intégration Calibre permet d'accéder à votre bibliothèque Calibre existante depuis l'application back-office-lmelp. L'application lit directement la base de données SQLite de Calibre (`metadata.db`) sans nécessiter l'installation de Calibre dans le conteneur Docker.

## Prérequis

- Une bibliothèque Calibre existante sur votre système hôte
- Le fichier `metadata.db` doit être accessible en lecture
- Calibre peut continuer à fonctionner normalement (lecture seule depuis Docker)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NAS Synology (ou PC)                     │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Bibliothèque Calibre (sur l'hôte)                 │   │
│  │  /volume1/books/Calibre Library/                   │   │
│  │    ├── metadata.db (SQLite)                        │   │
│  │    ├── metadata_db_prefs_backup.json               │   │
│  │    └── Author/                                     │   │
│  │         └── Book Title (ID)/                       │   │
│  │              ├── cover.jpg                         │   │
│  │              └── Book Title - Author.epub          │   │
│  └──────────────────┬─────────────────────────────────┘   │
│                     │ Montage volume Docker (:ro)          │
│                     ▼                                       │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Backend Container (FastAPI)                        │   │
│  │  /calibre/ (lecture seule)                         │   │
│  │    ├── metadata.db ← Lecture directe via SQLite    │   │
│  │    └── ...                                         │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Étape 1 : Identifier le chemin de votre bibliothèque Calibre

Localisez le répertoire de votre bibliothèque Calibre sur l'hôte :

**NAS Synology :**
```bash
# Vérifier que le fichier metadata.db existe
ls -l "/volume1/books/Calibre Library/metadata.db"
```

**Linux :**
```bash
ls -l "$HOME/Calibre Library/metadata.db"
```

**Mac :**
```bash
ls -l "$HOME/Calibre Library/metadata.db"
```

**Windows (WSL2/Docker Desktop) :**
```bash
ls -l "/mnt/c/Users/username/Calibre Library/metadata.db"
```

### Étape 2 : Modifier le fichier .env

Éditez le fichier `.env` (ou uploadez-le dans Portainer) et décommentez/modifiez les lignes Calibre :

```bash
# Exemple pour NAS Synology
CALIBRE_HOST_PATH=/volume1/books/Calibre Library

# Optionnel : Tag de bibliothèque virtuelle pour filtrer les livres
CALIBRE_VIRTUAL_LIBRARY_TAG=guillaume
```

**Important** : Assurez-vous que le chemin :
- Pointe vers le **répertoire racine** de la bibliothèque Calibre (pas vers `metadata.db` directement)
- Ne contient **pas** de barre oblique finale (`/`)
- Utilise des guillemets si le chemin contient des espaces

**Note sur le tag** : Si votre bibliothèque Calibre utilise des tags pour organiser les livres (ex: "guillaume" pour vos livres personnels), définissez `CALIBRE_VIRTUAL_LIBRARY_TAG` pour afficher uniquement ces livres. Laissez vide pour afficher tous les livres.

### Étape 3 : Redéployer la stack

Dans Portainer :

1. Accédez à votre stack `lmelp`
2. Cliquez sur **Update the stack**
3. Uploadez le fichier `.env` modifié
4. Cliquez sur **Update**
5. Attendez que les conteneurs redémarrent

### Étape 4 : Vérifier la configuration

#### Vérifier le montage du volume

```bash
# Vérifier que le volume est bien monté dans le conteneur backend
docker exec lmelp-backend ls -l /calibre/metadata.db
```

Vous devriez voir :
```
-rw-r--r-- 1 root root 123456 Nov 29 19:00 /calibre/metadata.db
```

#### Tester l'API Calibre

```bash
# Vérifier le statut Calibre
docker exec lmelp-backend curl -f http://localhost:8000/api/calibre/status

# Devrait retourner :
# {"available":true,"library_path":"/calibre","total_books":516,...}
```

#### Accéder à l'interface web

Ouvrez votre navigateur et accédez à :
```
https://lmelp.ascot63.synology.me/calibre
```

Vous devriez voir :
- La liste de vos livres Calibre
- Les boutons de filtre (Tous / Lus / Non lus)
- La barre de recherche
- Les boutons de tri

## Dépannage

### Erreur : "Calibre non disponible"

**Symptôme** : Message d'erreur dans l'interface web : "Bibliothèque Calibre non trouvée"

**Solutions** :

1. Vérifiez que `CALIBRE_HOST_PATH` est défini dans le fichier `.env`
2. Vérifiez que le chemin existe sur l'hôte :
   ```bash
   ls -l "/volume1/books/Calibre Library/metadata.db"
   ```
3. Vérifiez que le volume est bien monté dans le conteneur (le dossier `/calibre` doit exister et contenir `metadata.db`).
4. Redéployez la stack après modification du `.env`

### Erreur : "Permission denied"

**Symptôme** : Erreur dans les logs backend : `Permission denied: '/calibre/metadata.db'`

**Cause** : Les permissions du fichier `metadata.db` ne permettent pas la lecture par le conteneur Docker.

**Solution** :
```bash
# Sur l'hôte, rendre le fichier lisible par tous
chmod +r "/volume1/books/Calibre Library/metadata.db"
chmod +r "/volume1/books/Calibre Library/"
```

### Erreur : "No such file or directory"

**Symptôme** : Logs backend : `FileNotFoundError: [Errno 2] No such file or directory: '/calibre/metadata.db'`

**Cause** : Le volume Docker n'est pas monté correctement ou le chemin `CALIBRE_HOST_PATH` est incorrect.

**Solutions** :

1. Vérifier que le volume est monté :
   ```bash
   docker inspect lmelp-backend | grep -A 10 Mounts
   ```

2. Vérifier le chemin dans `.env` :
   ```bash
   # Le chemin doit pointer vers le RÉPERTOIRE Calibre, pas vers metadata.db
   # ✅ CORRECT
   CALIBRE_HOST_PATH=/volume1/books/Calibre Library

   # ❌ INCORRECT
   CALIBRE_HOST_PATH=/volume1/books/Calibre Library/metadata.db
   ```

3. Vérifier que le fichier existe sur l'hôte :
   ```bash
   ls -l "/volume1/books/Calibre Library/metadata.db"
   ```

### Livres affichés : 0

**Symptôme** : L'interface Calibre s'affiche mais "0 livres au total"

**Causes possibles** :

1. **Tag de bibliothèque virtuelle non configuré** :
   - Si votre bibliothèque Calibre utilise des tags pour filtrer (ex: tag "guillaume")
   - Définissez la variable d'environnement `CALIBRE_VIRTUAL_LIBRARY_TAG` dans le fichier `.env`
   - Exemple : `CALIBRE_VIRTUAL_LIBRARY_TAG=guillaume`
   - Redéployez la stack après modification

2. **Base de données vide** :
   - Vérifiez que votre bibliothèque Calibre contient bien des livres :
   ```bash
   docker exec lmelp-backend python3 -c "
   import sqlite3
   conn = sqlite3.connect('/calibre/metadata.db')
   cursor = conn.cursor()
   cursor.execute('SELECT COUNT(*) FROM books')
   print(f'Total books in DB: {cursor.fetchone()[0]}')
   conn.close()
   "
   ```

## Fonctionnalités disponibles

Avec Calibre configuré, vous avez accès à :

### API REST

- **GET /api/calibre/status** - Statut de l'intégration Calibre
- **GET /api/calibre/statistics** - Statistiques de la bibliothèque
- **GET /api/calibre/books** - Liste des livres (avec pagination, tri, filtres)

### Interface web

- **Recherche en temps réel** - Filtrer par titre ou auteur (insensible aux accents)
- **Filtres de statut** - Tous / Lus / Non lus
- **Tri** :
  - Derniers ajoutés (défaut)
  - Titre A→Z / Z→A
  - Auteur A→Z / Z→A
- **Mise en surbrillance** - Termes de recherche surlignés en jaune
- **Affichage** :
  - Titre, auteur(s), éditeur
  - ISBN, note (sur 5)
  - Tags Calibre
  - Statut de lecture

## Sécurité

### Montage en lecture seule

Le volume Calibre est monté avec l'option `:ro` (read-only) dans `docker-compose.yml` :

```yaml
volumes:
  - ${CALIBRE_HOST_PATH:-/dev/null}:/calibre:ro
```

Cela garantit que :
- L'application Docker **ne peut pas** modifier votre bibliothèque Calibre
- Les métadonnées Calibre restent gérées uniquement par Calibre
- Aucun risque de corruption de la base de données

### Accès concurrent

Il est **sûr** d'utiliser Calibre et back-office-lmelp en même temps :
- Back-office-lmelp lit uniquement `metadata.db` en mode lecture
- Calibre peut continuer à ajouter/modifier des livres
- SQLite gère automatiquement les lectures concurrentes

**Note** : Les modifications faites dans Calibre apparaîtront après actualisation de la page web.

## Limitations

1. **Pas de modification** - L'interface est en lecture seule (par conception)
2. **Pas de couvertures** - Les images de couverture ne sont pas affichées (pour l'instant)
3. **Pas de téléchargement** - Impossible de télécharger les fichiers EPUB/PDF/MOBI
4. **Colonnes personnalisées** - Seules 3 colonnes personnalisées sont supportées :
   - `#read` (booléen) - Livre lu ou non
   - `#paper` (booléen) - Livre possédé en format papier
   - `#text` (texte) - Commentaires personnels

## Désactivation de Calibre

Pour désactiver l'intégration Calibre :

1. Commentez la ligne `CALIBRE_HOST_PATH` dans le fichier `.env` :
   ```bash
   # CALIBRE_HOST_PATH=/volume1/books/Calibre Library
   ```

2. Redéployez la stack dans Portainer

3. L'interface web affichera "Calibre non disponible"

## Liens utiles

- [Documentation Calibre](https://manual.calibre-ebook.com/)
- [Structure de la base SQLite Calibre](../dev/calibre-db-schema.md)
- [API Calibre](../dev/api.md#calibre-endpoints)

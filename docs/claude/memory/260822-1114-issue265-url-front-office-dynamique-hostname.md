# Issue #265 — URL front-office lmelp dérivée dynamiquement du hostname

## Contexte

La stack lmelp a été migrée d'un déploiement local (laptop) vers une stack hébergée sur le NAS, derrière un reverse proxy Synology :
- Back-office : `https://lmelp-bo.ascot63.synology.me/`
- Front-office lmelp (Streamlit) : `https://lmelp.ascot63.synology.me/`

Sur la page d'accueil du back-office, la tuile "Dernière mise à jour" est cliquable et doit ouvrir le front-office lmelp. L'URL était hardcodée sur `http://localhost:8501/` dans `frontend/src/views/Dashboard.vue:470-478` (computed `lmelpFrontOfficeUrl` / `lmelpAvisCritiquesUrl`, héritées de l'Issue #128), ce qui cassait le lien dès que le back-office n'était plus accédé via localhost.

## Décision architecturale clé

Une exploration du repo a montré qu'**aucun mécanisme de config runtime frontend n'existe** : l'image Docker frontend (`ghcr.io/castorfou/lmelp-frontend`, cf. `docker/build/frontend/Dockerfile`) est buildée une seule fois par la CI avec un bundle Vite statique figé, servi par nginx. Le `docker-compose.yml` de prod (`docker/deployment/docker-compose.yml`) ne passe aucune variable d'environnement au service `frontend` (contrairement au `backend` qui utilise `environment:` lu au runtime par FastAPI).

Une variable `VITE_*` classique (lue via `import.meta.env`) est résolue au **build-time** uniquement — elle aurait nécessité d'ajouter un `ARG`/`ENV` au Dockerfile et un `--build-arg` dans le pipeline CI, ou un mécanisme d'injection runtime via un entrypoint nginx générant un `config.js` (aucun des deux n'existe actuellement dans ce repo).

**Solution retenue avec l'utilisateur** : dériver l'URL cible **à l'exécution, côté client**, à partir de `window.location.hostname` — zéro configuration Docker/CI/env var nécessaire. Trois règles :

1. `hostname === 'localhost'` ou `'127.0.0.1'` → `http://<hostname>:8501/`
2. `hostname` est une IPv4 brute (regex `/^\d{1,3}(\.\d{1,3}){3}$/`) → même IP, port `8501`
3. Sinon, si le hostname suit le pattern `xxx-bo.yyy` (regex `/^([\w-]+)-bo\./`) → retirer le suffixe `-bo` du premier label et servir en `https://` : `lmelp-bo.ascot63.synology.me` → `https://lmelp.ascot63.synology.me/`
4. Fallback (aucune règle ne matche) → comportement historique `http://localhost:8501/`, pour ne jamais casser le lien plus qu'avant

Règle 3 validée par l'utilisateur comme **générique**, pas limitée au domaine `ascot63.synology.me` — réutilisable pour tout déploiement suivant la même convention de nommage back-office/front-office.

## Implémentation

- **Nouveau** `frontend/src/utils/lmelpFrontOfficeUrl.js` : fonction pure `getLmelpFrontOfficeUrl(hostname, path = '')` implémentant les 4 règles ci-dessus.
- `frontend/src/views/Dashboard.vue` : les computed `lmelpFrontOfficeUrl` et `lmelpAvisCritiquesUrl` appellent désormais `getLmelpFrontOfficeUrl(window.location.hostname)` / `getLmelpFrontOfficeUrl(window.location.hostname, 'avis_critiques')`.
- **Nouveau** `frontend/tests/unit/lmelpFrontOfficeUrl.test.js` : 10 tests unitaires TDD (localhost, 127.0.0.1, IP brute, domaine `-bo` générique, fallback hostname sans `-bo`, fallback hostname vide, path optionnel sur les 3 branches).
- `frontend/tests/integration/Dashboard.test.js` : nouveau bloc `describe('Dashboard - URL front-office lmelp dynamique (Issue #265)')` avec mock de `window.location` (pattern `delete window.location; window.location = { ...original, hostname }` — `vi.spyOn(window.location, 'hostname', 'get')` échoue en jsdom avec `TypeError: Cannot redefine property: hostname`).

## Cycle TDD suivi

1. RED #1 : test unitaire écrit avant `lmelpFrontOfficeUrl.js` → échec d'import (RED technique attendu, fichier n'existe pas).
2. GREEN #1 : implémentation de la fonction pure → 10/10 tests passent.
3. RED #2 : test d'intégration Dashboard avec hostname `-bo` mocké → échec métier confirmé (`Dashboard.vue` retournait encore la valeur hardcodée `http://localhost:8501/` au lieu de `https://lmelp.ascot63.synology.me/`).
4. GREEN #2 : `Dashboard.vue` appelle la nouvelle fonction utilitaire → tous les tests passent.
5. Suite complète frontend : 657 tests passent, 0 régression.

## Validation utilisateur

Testé manuellement en localhost et en IP locale (`npm run dev` / accès réseau local) : lien correct dans les deux cas — comportement identique à l'existant, donc peu de risque de régression. Le cas NAS (règle `-bo`) n'a pas pu être testé manuellement avant déploiement (pas d'accès facile au NAS depuis l'environnement de dev) ; il est couvert par les tests automatisés unitaires et d'intégration qui vérifient explicitement `lmelp-bo.ascot63.synology.me` → `https://lmelp.ascot63.synology.me/`.

## Apprentissage réutilisable

Pour toute future config différenciant dev local / déploiement NAS-reverse-proxy côté **frontend Vue/Vite** dans ce repo : préférer une dérivation dynamique basée sur `window.location` (hostname, protocol, etc.) plutôt qu'une variable d'environnement Vite, **sauf** si le pipeline CI/Docker est modifié pour supporter l'injection runtime (entrypoint nginx + `config.js`) ou build-time (`--build-arg`). Le doc `docs/dev/environment-variables.md` mentionne `VITE_API_BASE_URL` mais ce n'est qu'une doc orpheline — jamais implémentée dans le code, ne pas s'y fier comme référence d'un mécanisme existant.

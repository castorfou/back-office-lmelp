# Issue #318 — 502 sur /api après recréation du backend (nginx fige l'IP)

## Problème
`docker/build/frontend/nginx.conf` proxifiait vers `http://backend:8000/...` en dur, sans
`resolver`. nginx résout un nom d'hôte statique **une seule fois, au chargement de la conf**.
Après recréation du conteneur `backend` (Watchtower — mis à jour fréquemment —, reboot NAS),
le backend peut obtenir une autre IP sur le réseau Docker : nginx continue de viser l'ancienne
→ `connect() failed (111: Connection refused)` → 502 sur `/api`, `/docs`, `/openapi.json`,
jusqu'au redémarrage du frontend. Le healthcheck frontend (`/health`, servi localement) ne voit
rien : le conteneur reste « healthy ».

## Correctif
- `docker/build/frontend/nginx.conf` (niveau `server`) :
  - `resolver 127.0.0.11 valid=10s ipv6=off;` (DNS embarqué de Docker, réseaux user-defined)
  - `set $backend backend:8000;`
  - `/api/`, `/docs`, `/openapi.json` → `proxy_pass http://$backend;` (**sans chemin**)
  - `location = /api` → `proxy_pass http://$backend/;` (réécrit `/api` → `/` comme avant)
- `docker/build/frontend/Dockerfile` : `RUN nginx -t` après le `COPY` de la conf.

## Points saillants
- **Piège `proxy_pass` à variable** : dès que `proxy_pass` contient une variable, un chemin
  éventuel remplace **toute** l'URI de la requête (pas de substitution du préfixe de
  `location`). Il faut donc omettre le chemin pour que nginx transmette l'URI d'origine (query
  string incluse). Vérifié en réel : `/api/livres?x=1&y=%C3%A9`, `/docs/oauth2-redirect`,
  `/openapi.json` arrivent identiques au backend ; `/api` arrive en `/`.
- **`nginx -t` au build comme garde-fou de régression** : avec un hôte en dur, `nginx -t`
  échoue hors de la stack (`host not found in upstream "backend"`) ; avec une variable, aucune
  résolution n'a lieu au chargement → passe. Le build Docker bloque donc tout retour à un
  `proxy_pass http://backend:...` statique.
- Tests statiques dans `tests/test_docker_frontend_config.py` (même pattern que
  `tests/test_docker_backend_config.py`) : resolver présent, `set $backend`, aucun `proxy_pass`
  à hôte en dur, mapping exact par location (parsing regex des blocs `location`), `RUN nginx -t`.

## Vérification locale sans Docker
Le devcontainer n'a pas docker. nginx s'installe via apt, mais le miroir `bullseye-security`
renvoie 404 → épingler la version de base :
`sudo apt-get install nginx-light=1.18.0-6.1+deb11u3 libnginx-mod-http-echo=1.18.0-6.1+deb11u3 nginx-common=1.18.0-6.1+deb11u3`.
Test fonctionnel : conf wrappée dans un `http {}` minimal (pid/logs/temp dans le scratchpad),
`listen` sur un port non privilégié, `set $backend 127.0.0.1:<port>` (IP littérale, pas de
résolution) devant un petit serveur Python qui renvoie `self.path`. Ne pas lancer
`sudo nginx -t` dans le dossier de test : il y crée des fichiers root qui empêchent ensuite le
lancement non-root (`nginx.pid` permission denied).
La re-résolution elle-même (`127.0.0.11`) n'est testable que dans une vraie stack Docker :
validation à faire sur le NAS après merge (`docker compose up -d --force-recreate backend`).

## Divers
- `test_avis_critiques_generation_service.py::...episode_2017_04_09_should_succeed` fait un
  vrai appel Azure OpenAI quand les credentials sont présents localement et dépasse le timeout
  pytest de 15 s — sans lien avec cette issue (sauté en CI).

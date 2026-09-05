# Issue #286 — Étude de faisabilité VPN embarqué + proxy Babelio interne

## Contexte

Étude d'architecture pure (pas de code), livrée sous forme de document `docs/dev/vpn-babelio-feasibility-study.md`. Objectif : évaluer la faisabilité de faire transiter tout le flux réseau sortant du backend (Babelio en priorité) par un tunnel VPN dédié, indépendant de l'IP domicile du NAS, suite au ban IP de l'issue #285.

## Fait marquant découvert en cours de rédaction : ce n'est pas un incident isolé

La première version du document concluait "ne pas implémenter" en se basant sur "un seul incident documenté (issue #285)". L'utilisateur a corrigé ce point factuel en cours de session : les bans IP Babelio sont **récurrents depuis le début du projet**, déjà contournés manuellement à l'époque où l'app tournait en local (Docker sur laptop) via un montage VPN mobile + point d'accès Wi-Fi + laptop connecté dessus. Le rate-limiter/circuit-breaker de `babelio_service.py` a été développé en parallèle précisément pour limiter ces bans, mais un nouveau ban s'est produit **malgré** ce mécanisme, 2 semaines après le passage en hébergement NAS.

**Leçon méthodologique** : pour une étude de faisabilité, ne jamais présumer la fréquence/l'historique d'un problème à partir du seul ticket GitHub qui la documente formellement — l'historique réel (contournements passés, tentatives déjà faites) change complètement le rapport bénéfice/coût et donc la conclusion. Toujours demander explicitement ce contexte avant de conclure, plutôt que de le déduire du nombre d'issues ouvertes sur le sujet.

Deuxième correction factuelle : le tableau comparatif présentait la clause CGU NordVPN ("usage personnel, non-commercial") comme un point défavorable générique. L'utilisateur a précisé que back-office-lmelp est open-source et sans revenus — cette clause n'est donc pas un obstacle réel pour ce projet, contrairement à ce qu'une lecture superficielle du comparatif suggérait.

Ces deux corrections ont fait basculer la recommandation finale de "ne pas implémenter" à "justifié, avec portée limitée".

## Contenu technique retenu dans le document final

- **Architecture** : sidecar `gluetun` (pas d'intégration dans le code Python), `network_mode: "service:gluetun"` sur le conteneur backend, kill switch natif, IP VPN fixe (pas de rotation automatique, pour préserver la validité du cookie anti-captcha stocké en mémoire dans `babelio_service.py::_stored_cookie`).
- **Comparatif VPN** : Mullvad recommandé (WireGuard natif, ~5€/mois flat, pas de compte email, orienté usage technique, supporté nativement par `gluetun`). NordVPN, ProtonVPN, Surfshark, AirVPN, VPS Hetzner et proxy résidentiel Bright Data également comparés — proxy résidentiel écarté (8-15$/Go, disproportionné pour ce volume).
- **WireGuard vs OpenVPN** : section pédagogique ajoutée à la demande de l'utilisateur (taille du code ~4000 vs ~100000 lignes, perf, simplicité de config, reconnexion sans état) — Mullvad a d'ailleurs retiré OpenVPN en janvier 2026.
- **Mise en route Mullvad concrète** : création de compte (pas d'email, numéro à conserver), crédit, génération de clé WireGuard, choix du pays de sortie (`SERVER_COUNTRIES=France`), réutilisation du même compte pour d'autres usages (5 connexions simultanées max, clés distinctes recommandées).
- **Proxy interne pour les covers** : 3 vues frontend identifiées chargeant `url_cover` directement (`LivreDetail.vue`, `Dashboard.vue`, `BabelioMigration.vue` — pas seulement `LivreDetail.vue` comme le laissait penser l'issue #285 initiale), nécessitant un endpoint `/api/cover-image` avec cache disque.
- **Résolution du cookie captcha via le tunnel** : l'utilisateur a précisé que refaire la résolution manuelle du captcha à chaque rotation d'IP n'est PAS un problème en soi (déjà l'usage actuel) — le vrai besoin est que cette résolution transite par le VPN backend, pas par l'IP domicile. Conclusion technique : un simple relais GET ne suffit pas (URLs relatives dans le HTML/CSS/JS cassées, captcha JS interactif hors du proxy) — il faut un vrai reverse-proxy avec réécriture d'URLs et transmission bidirectionnelle de cookies (brique type `nginx proxy_pass`/`sub_filter`, pas un endpoint FastAPI ad hoc).
- **Rotation d'IP** : recommandation de rotation **manuelle** (pas d'automatisation), procédure en 4 étapes documentée (détection via circuit breaker existant ou healthcheck `gluetun`, modification `SERVER_CITIES`, `docker restart gluetun`, re-résolution du captcha via le reverse-proxy).
- **Toggle `WIREGUARD_ENABLED`** : l'utilisateur voulait une seule variable d'environnement pour activer/désactiver le VPN. `network_mode` étant une directive Compose statique (pas interpolable), la solution documentée combine `profiles` Compose (pour le service `gluetun`) + un fichier `docker-compose.vpn.yml` optionnel (pour la ligne `network_mode` du backend), le tout piloté par un script de déploiement lisant `WIREGUARD_ENABLED` dans `.env` — un redémarrage du stack reste nécessaire (pas de toggle à chaud), mais un seul point de configuration côté exploitant.
- **Stratégie de validation avant déploiement NAS** (ajoutée à la demande explicite de l'utilisateur — angle mort de la première version) : validation par couches indépendantes en local avant tout déploiement NAS — (1) tunnel VPN seul (`curl ifconfig.me` depuis le network namespace de `gluetun`), (2) backend routé via `gluetun` en local avec un `curl babelio.com` ponctuel, (3) kill switch (couper le tunnel, vérifier l'absence de fallback en clair), (4) toggle `WIREGUARD_ENABLED` dans les deux positions, (5) déploiement NAS en dernier avec `WIREGUARD_ENABLED=false` comme filet de sécurité immédiat.

## Recommandation finale du document

Le VPN est jugé justifié (contrairement à la première ébauche), avec portée volontairement limitée : Mullvad + `gluetun` + IP fixe + proxy interne pour les covers (qui a un intérêt propre indépendant du VPN, via le cache disque). Réserve maintenue : l'architecture `network_mode` fait dépendre tout le backend (pas seulement Babelio) de la santé du tunnel — compromis à assumer consciemment, une architecture plus sélective n'ayant pas de solution simple avec les outils standards.

## Fichiers modifiés

- `docs/dev/vpn-babelio-feasibility-study.md` (nouveau, ~200 lignes)
- `docs/dev/.nav.yml` — entrée de navigation ajoutée
- Commentaires GitHub sur l'issue #286 (résumé initial de l'étude)

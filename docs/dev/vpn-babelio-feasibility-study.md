# Étude de faisabilité — VPN embarqué et proxy Babelio interne

Étude d'architecture (issue #286), sans implémentation de code. Objectif : évaluer la faisabilité de faire transiter tout le flux réseau sortant du backend (Babelio en priorité) par un tunnel VPN dédié, indépendant de l'IP domicile du NAS.

## Contexte

Le backend et le poste domicile de l'exploitant partagent la même IP publique (NAS auto-hébergé derrière la box internet personnelle). Un ban de cette IP par Babelio (issue #285) a cassé l'affichage des couvertures dans toute l'application — y compris pour les visiteurs du site, dont le navigateur charge les images de couverture directement depuis Babelio, hors du contrôle du backend.

**Ce n'est pas un incident isolé.** Les bans IP par Babelio se produisent de manière récurrente depuis le début du projet :
- À l'époque où l'application tournait en local (Docker sur laptop), le contournement était manuel : activer le VPN gratuit de l'opérateur mobile sur le téléphone, créer un point d'accès Wi-Fi, et connecter le laptop dessus pour changer d'IP de sortie.
- Le rate-limiter et le circuit breaker actuels de `babelio_service.py` (1 requête/2-5s, ouverture automatique après un 403) ont été développés en parallèle, précisément pour limiter ces bans.
- Depuis le passage en hébergement sur le NAS (il y a 2 semaines au moment de cette étude), un nouveau ban s'est produit **malgré** ce rate-limiter — la fréquence exacte reste difficile à quantifier, mais le motif est clairement récurrent sur la durée du projet, pas un aléa ponctuel.

Cet historique pèse directement sur la recommandation finale (dernière section de ce document) : la question n'est pas "un incident vaut-il le coût d'un VPN", mais "un problème structurel récurrent, déjà contourné manuellement plusieurs fois, justifie-t-il une automatisation".

## 1. Architecture recommandée

### VPN permanent au niveau service, pas par connexion client

Le tunnel doit être établi en continu au niveau du conteneur backend, jamais déclenché par une connexion client individuelle (latence et complexité inutiles pour un usage où le débit de requêtes Babelio est déjà très faible — rate-limité à 1 requête/2-5s).

### Sidecar `gluetun` plutôt qu'intégration dans le processus Python

Deux approches sont possibles :

- **Sidecar `gluetun`** : conteneur Docker dédié qui établit le tunnel VPN et route le trafic réseau des conteneurs qui partagent son network namespace (`network_mode: "service:gluetun"`). Le code Python du backend n'a besoin d'aucune modification — c'est Docker qui route.
- **VPN intégré au processus** (bibliothèque WireGuard userspace type `wireguard-go`, ou appel `wg-quick` au démarrage du conteneur backend lui-même) : plus de couplage entre le code applicatif et l'infrastructure réseau, plus de surface de maintenance.

**Recommandation : sidecar `gluetun`.** C'est un projet mature (>10k étoiles GitHub), maintenu activement, qui expose un kill switch natif, un health check HTTP intégré, et supporte nativement la plupart des fournisseurs candidats (voir tableau §2). Il s'intègre au `docker-compose.yml` de déploiement actuel (`docker/deployment/docker-compose.yml`) sans réécriture de l'infrastructure existante :

```yaml
services:
  gluetun:
    image: qmcgaw/gluetun
    cap_add:
      - NET_ADMIN
    environment:
      - VPN_SERVICE_PROVIDER=mullvad   # ou autre fournisseur supporté
      - VPN_TYPE=wireguard
      - WIREGUARD_PRIVATE_KEY=...
      - SERVER_COUNTRIES=France        # garde une IP de sortie française
    healthcheck:
      test: ["CMD", "wget", "-qO-", "https://ipinfo.io/ip"]
      interval: 30s

  backend:
    image: ghcr.io/castorfou/lmelp-backend:latest
    network_mode: "service:gluetun"   # tout le trafic backend passe par le tunnel
    depends_on:
      gluetun:
        condition: service_healthy
```

Le conteneur `frontend` (qui ne fait aucun appel sortant vers Babelio — c'est le backend qui scrape, cf. §3) reste sur le réseau bridge normal, non affecté.

### Santé, reconnexion, kill switch

- `gluetun` expose un **kill switch natif** : si le tunnel tombe, tout le trafic réseau du conteneur backend est bloqué (pas de fallback silencieux vers l'IP domicile). C'est le comportement attendu par l'issue — mieux vaut un Babelio indisponible pour l'application entière qu'une fuite de trafic non protégé.
- `gluetun` a un healthcheck HTTP intégré, redémarre automatiquement le tunnel en cas de coupure (paramètre `VPN_PORT_FORWARDING`/watchdog interne).
- **Conséquence opérationnelle** : si le VPN est down, **tout le backend** est down (MongoDB, endpoints internes, tout), pas seulement l'accès Babelio — puisque `network_mode: "service:gluetun"` route l'intégralité du trafic réseau du conteneur, pas seulement les appels sortants vers Babelio. C'est un compromis important à trancher (voir §5 « Points de vigilance transverses », alternative avec un point de sortie réseau plus sélectif que ce document n'a pas creusé faute de mécanisme simple pour scoper `network_mode` à un sous-ensemble de destinations).

### Rotation d'IP dynamique en cas de nouveau ban

`gluetun` permet de changer de serveur de sortie via une variable d'environnement (`SERVER_CITIES`/`SERVER_HOSTNAMES`) suivie d'un redémarrage du conteneur — pas de rotation automatique à chaud native sur détection de 403, ce qui demanderait un script de supervision externe (ex: un cron qui teste `curl` régulièrement vers Babelio, et déclenche un `docker restart gluetun` avec un serveur différent en cas d'échecs répétés). Cette automatisation n'existe dans aucun outil standard trouvé — elle serait à écrire spécifiquement pour ce projet, hors scope de cette étude.

**Tension avec le cookie anti-captcha** (confirmée dans le code, `babelio_service.py:97` — `self._stored_cookie`, posé via `POST /api/babelio/cookie`, jamais persisté sur disque) : ce cookie est probablement lié à une empreinte de session avec l'IP source. Une rotation d'IP invaliderait potentiellement ce cookie, nécessitant sa reconfiguration manuelle après chaque rotation — annulant une partie du bénéfice d'automatisation. Non vérifiable sans test réel contre Babelio (risque de nouveau ban pendant l'expérimentation).

**Recommandation** : démarrer avec une **IP VPN fixe stable** (pas de rotation automatique) — plus simple, cohérent avec le cookie actuel, et le seul ban documenté à ce jour (issue #285) n'a pas de cause confirmée liée à un volume excessif justifiant une rotation défensive. Réévaluer si un nouveau ban survient malgré le VPN.

## 2. Comparatif des solutions VPN

| Solution | Prix | Protocole | Support `gluetun` | Connexions/IP | CGU usage serveur/Docker | Notes |
|---|---|---|---|---|---|---|
| **Mullvad** | ~5€/mois (tarif plat, pas de palier) | WireGuard natif (OpenVPN retiré en 2026) | ✅ Natif | 5 appareils simultanés/compte | Pas d'interdiction explicite trouvée ; usage automatisé/serveur documenté comme fonctionnant en pratique (scripts de connexion), mais "à la marge" d'un usage non officiellement garanti | Pas de compte email requis, orienté usage technique — candidat le plus documenté pour ce cas d'usage |
| **ProtonVPN** | à partir de ~3$/mois (Plus), gamme de plans | WireGuard | ✅ Natif | 10 connexions simultanées (Plus) | CGU génériques grand public, pas de clause serveur/Docker identifiée avec certitude | Écosystème plus large (mail, cloud) que nécessaire ici |
| **NordVPN** | ~3,50-13$/mois selon durée d'engagement | WireGuard (NordLynx) | ✅ Natif | Variable selon plan | Licence limitée à un usage "personnel, non-commercial" — **non bloquant ici** : ce projet est open-source, sans revenus, donc un usage non-commercial au sens propre | Pas de clause spécifique serveur/Docker identifiée au-delà de cette limitation générale non-commerciale |
| **Surfshark** | ~2,50-16$/mois selon durée | WireGuard | ✅ Natif | Connexions illimitées | Pas de clause Docker/serveur identifiée dans les CGU publiques trouvées | Connexions illimitées intéressant si plusieurs services devaient un jour partager le tunnel |
| **AirVPN** | ~32€/an (~2,65€/mois), pas d'abonnement mensuel pur | OpenVPN + WireGuard | ✅ Natif | 5 connexions (offre standard), port forwarding disponible | **"Tout protocole bienvenu, y compris p2p"** — le plus explicitement permissif trouvé sur l'usage technique | Communauté orientée confidentialité/technique, politique de bande passante transparente sans sur-souscription |
| **VPS auto-hébergé (Hetzner CX)** | ~7$/mois (2 vCPU, 4 Go RAM, 20 To trafic inclus) | WireGuard (auto-installé) | N/A (pas un "VPN provider", c'est votre propre serveur) | Illimité (c'est votre serveur) | Aucune CGU d'usage VPN à respecter — c'est un serveur générique | **IP dédiée unique** : re-bannissable comme n'importe quelle IP si Babelio la bloque un jour ; nécessiterait un pool de plusieurs VPS pour permettre une vraie rotation, ce qui multiplie le coût et la complexité opérationnelle |
| **Proxy résidentiel (Bright Data)** | 8-15$/Go à l'usage (jusqu'à ~3$/Go en engagement mensuel élevé) | HTTP/SOCKS5 (pas un VPN classique) | ❌ Non supporté par gluetun | Rotation par design (pool d'IP résidentielles) | Usage commercial explicitement autorisé (c'est le modèle commercial du produit) | Coût largement disproportionné pour ce volume (quelques Mo/jour de scraping Babelio) — pertinent seulement si le volume de scraping devenait massif |

**Sources** : recherche web de septembre 2026, CGU non auditées ligne par ligne par un juriste — voir limites en §5 « Points de vigilance transverses ».

### WireGuard vs OpenVPN — pourquoi WireGuard

Le comparatif ci-dessus retient WireGuard comme protocole cible (natif chez tous les fournisseurs listés, et Mullvad a retiré OpenVPN en janvier 2026). Différences pratiques avec OpenVPN :

- **Taille du code et audit** : WireGuard tient en ~4000 lignes de code contre ~100 000 pour OpenVPN — plus simple à auditer, moins de surface d'attaque.
- **Performance** : intégré au noyau Linux (depuis 5.6), généralement 2 à 3× plus rapide qu'OpenVPN et avec une latence plus faible. Pour ce cas d'usage (trafic Babelio déjà throttlé à 1 req/2-5s), le gain de perf est indifférent — c'est surtout la simplicité de config et de maintenance qui compte.
- **Configuration** : un fichier WireGuard (clé privée, clé publique du pair, IP, endpoint) tient en une dizaine de lignes, contre plusieurs fichiers (certificats, clés TLS) pour OpenVPN — cohérent avec l'approche "peu de composants à maintenir" recherchée ici.
- **Reconnexion** : WireGuard est sans état côté protocole (pas de "session" à renégocier), ce qui le rend rapide à rétablir après une coupure — pertinent pour le comportement de reconnexion automatique attendu de `gluetun`.

### Mise en route concrète avec Mullvad

1. **Créer un compte** sur mullvad.net — pas d'email demandé, un numéro de compte à 16 chiffres est généré aléatoirement. **À conserver précieusement** : Mullvad ne peut pas le retrouver en cas de perte (par conception, pour l'anonymat).
2. **Ajouter du crédit** (carte bancaire, ou options plus anonymes comme le cash par courrier ou la crypto) — le tarif est un forfait plat (~5€/mois) décompté automatiquement du crédit disponible.
3. **Générer une clé WireGuard** dans l'espace compte Mullvad — soit une paire générée par eux, soit l'upload d'une clé publique générée localement (utile pour préparer la config `gluetun` à l'avance).
4. **Récupérer les paramètres de connexion** (clé privée, adresse IP interne attribuée, endpoint du serveur) à injecter dans les variables d'environnement `gluetun` (`WIREGUARD_PRIVATE_KEY`, `SERVER_COUNTRIES=France`, etc.).
5. **Choisir le pays de sortie** : `SERVER_COUNTRIES=France` (voire `SERVER_CITIES=Paris` pour cibler une ville précise) garde une IP de sortie française, cohérent avec un site consommé principalement par des utilisateurs francophones.

**Réutilisation du même compte pour d'autres usages** (ex: un navigateur perso) : possible, dans la limite de **5 connexions simultanées par compte**. Le NAS en utilisant une en continu, il en reste 4 disponibles. Bonne pratique : générer une clé WireGuard **distincte** par usage (une pour le NAS, une pour le navigateur) plutôt que de réutiliser la même — permet de révoquer un usage sans couper les autres, sans toucher à l'abonnement lui-même.

## 3. Proxy interne pour tout le flux Babelio

### Périmètre réel identifié dans le code (au-delà des covers)

L'issue #285 portait sur les images de couverture, mais le grep du code révèle que **3 vues frontend** chargent `url_cover` directement depuis Babelio, hors du contrôle du backend et donc hors VPN quelle que soit la solution retenue en §1 :

- `frontend/src/views/LivreDetail.vue`
- `frontend/src/views/Dashboard.vue`
- `frontend/src/views/BabelioMigration.vue`

Le scraping HTML (`babelio_service.py::_fetch_page`, `search()`, `verify_book()`, etc.) est déjà exclusivement côté backend — il bénéficierait automatiquement du VPN sans aucun changement de code si l'architecture du §1 est retenue.

**Autres flux sortants backend identifiés** (candidats à un VPN partagé, si le scope devait s'étendre) :
- `annas_archive_url_service.py` — recherche de liens vers Anna's Archive
- `radiofrance_service.py` — scraping JSON-LD RadioFrance (recherche d'épisodes)

Ces deux services tournant dans le même conteneur backend, ils passeraient par le même tunnel VPN sans configuration supplémentaire si `network_mode: "service:gluetun"` est appliqué au conteneur backend entier (§1) — c'est un effet de bord automatique, pas un choix à faire séparément. **Point de vigilance** : un ban éventuel sur Anna's Archive ou RadioFrance depuis l'IP VPN partagée impacterait alors Babelio aussi, et réciproquement — la mutualisation d'un tunnel unique pour plusieurs services tiers concentre le risque de ban sur une seule IP de sortie.

### Nouvel endpoint proxy pour les covers

Pour que les couvertures bénéficient elles aussi du VPN, il faut qu'elles cessent d'être chargées directement par le navigateur du visiteur — remplacer `<img :src="livre.url_cover">` par un appel à un nouvel endpoint backend, par exemple :

```
GET /api/cover-image?url=<url_cover_encodée>
```

qui télécharge l'image via `babelio_service` (donc via le VPN, avec le rate-limiter déjà en place) et la ressert au navigateur. Une fois récupérée avec succès, la mettre en cache disque (une couverture Babelio ne change jamais) pour ne plus jamais la redemander — cache déjà présent en pattern dans `babelio_cache_service.py` pour les pages HTML, extensible aux binaires images.

### Résolution du cookie anti-captcha via le tunnel

Le mécanisme actuel (copier le header `Cookie` depuis les DevTools d'un vrai navigateur, puis `POST /api/babelio/cookie`) suppose que l'exploitant puisse ouvrir `babelio.com` directement — impossible si son IP domicile est bannie (situation vécue lors de l'issue #285). Avec un VPN backend actif, l'IP du backend et celle du domicile de l'exploitant divergent : le problème ne disparaît pas totalement, il persiste si l'IP **domicile** (pas celle du VPN) reste bannie au moment où l'exploitant doit résoudre un captcha dans son propre navigateur.

**Précision de l'exploitant sur ce point** : refaire la résolution manuelle du captcha à chaque changement d'IP n'est pas considéré comme un problème en soi — c'est déjà l'usage actuel. Le vrai besoin est que **cette résolution manuelle transite elle-même par le VPN Mullvad du backend**, pas par l'IP domicile de l'exploitant.

Ça exclut d'emblée un simple relais GET (`/api/babelio/browse?url=...` qui renverrait le HTML brut) : une page Babelio contient des ressources et des liens relatifs (CSS, JS, images, autres pages Babelio) qui pointeraient toujours vers `babelio.com` en dur — la page casserait visuellement, et le captcha (widget JS interactif type reCAPTCHA) ferait ses propres appels réseau hors du proxy. Il faut un **vrai reverse-proxy** :

- Réécriture des URLs absolues et relatives dans le HTML/CSS/JS renvoyé, pour qu'elles pointent vers le proxy plutôt que vers `babelio.com` directement.
- Transmission bidirectionnelle des cookies de session entre le navigateur de l'exploitant et Babelio, à travers le proxy (le proxy doit se comporter comme un vrai intermédiaire de session, pas juste relayer une réponse ponctuelle).
- Toutes les requêtes du proxy vers Babelio passent par le conteneur backend, donc par le tunnel VPN (§1) — c'est ce qui résout le problème.

C'est une brique d'infrastructure connue (reverse-proxy applicatif), pas à réinventer : une configuration `nginx` en mode `proxy_pass` avec `sub_filter` pour la réécriture d'URLs, ou une bibliothèque Python dédiée (ex: un module ASGI de reverse-proxying au-dessus de `httpx`), plutôt qu'un endpoint FastAPI ad hoc. Cette route ne serait utilisée que ponctuellement (résolution manuelle du captcha), pas exposée publiquement — à protéger par une authentification minimale (elle donne accès à naviguer sur Babelio via l'IP du NAS).

### Mécanisme de rotation d'IP en cas de nouveau ban

**Recommandation : rotation manuelle déclenchée par l'exploitant, pas d'automatisation dans un premier temps.** Une automatisation complète (détection + rotation + redémarrage sans intervention) demanderait un accès au socket Docker depuis un processus de supervision, redémarrerait le conteneur backend à chaque rotation (coupure de service de quelques secondes, `gluetun` route tout le conteneur), et risquerait une boucle si le nouveau serveur choisi est lui-même déjà mal vu par Babelio — complexité qui n'est pas justifiée pour un événement resté rare même avant le VPN.

**Procédure manuelle envisagée** :
1. Détection du ban : soit observée directement (échecs 403 répétés, circuit breaker `babelio_service.py::_circuit_open` resté ouvert malgré un cookie à jour), soit via un healthcheck périodique existant côté `gluetun` (`wget` vers une page Babelio, déjà présent nativement dans l'exemple de configuration §1).
2. Modifier `SERVER_CITIES`/`SERVER_HOSTNAMES` dans la configuration du conteneur `gluetun` pour cibler un autre serveur Mullvad (toujours en France si on veut garder cette contrainte).
3. `docker restart gluetun` (et le backend redémarre avec lui, puisqu'il partage son network namespace).
4. Résoudre à nouveau le captcha si nécessaire, **via le reverse-proxy décrit ci-dessus** (pas depuis le navigateur personnel de l'exploitant) pour que cette étape passe elle aussi par la nouvelle IP Mullvad.

Cette procédure reste à la main de l'exploitant — un ticket dédié pourrait documenter les commandes exactes (scripts prêts à l'emploi) sans aller jusqu'à l'automatisation complète, à réévaluer seulement si la fréquence des rotations devenait elle-même contraignante.

### Activer/désactiver le VPN via une variable d'environnement

Besoin exprimé : pouvoir couper le VPN (retour au trafic direct) sans éditer le `docker-compose.yml` à la main — utile en cas de panne du fournisseur VPN, ou pour du débogage. `network_mode: "service:gluetun"` est une directive Compose statique : elle ne peut pas être interpolée par une variable d'environnement au moment du démarrage, donc un vrai flag runtime instantané (sans redémarrage) n'existe pas nativement dans Docker Compose. Un redémarrage du stack pour appliquer le changement reste nécessaire dans tous les cas — mais une **seule variable dans `.env`** peut piloter cet aller-retour, en combinant deux mécanismes Compose :

- **`profiles`** (fonctionnalité native Compose) pour activer/désactiver le service `gluetun` lui-même : `gluetun` est tagué `profiles: ["vpn"]`, et ne démarre que si `COMPOSE_PROFILES=vpn` est positionné (lu depuis `.env`, cohérent avec le pattern déjà en place dans ce projet pour `CALIBRE_VIRTUAL_LIBRARY_TAG`/`BABELIO_FAIR_SEC`).
- **Un fichier `docker-compose.vpn.yml` optionnel** en complément, pour la ligne `network_mode: "service:gluetun"` sur le backend — cette partie ne peut pas être rendue conditionnelle *à l'intérieur* d'un seul fichier compose (contrairement à `profiles`, qui active/désactive des services entiers, pas des attributs d'un service existant). Ce fichier n'est ajouté à la commande `docker compose` que si le flag VPN est actif :

```bash
# .env
WIREGUARD_ENABLED=true

# script de déploiement (ex: deploy.sh), pas Docker lui-même :
if [ "$WIREGUARD_ENABLED" = "true" ]; then
  docker compose -f docker-compose.yml -f docker-compose.vpn.yml up -d
else
  docker compose -f docker-compose.yml up -d
fi
```

Au final, l'exploitant ne manipule qu'une seule variable (`WIREGUARD_ENABLED`) dans `.env`, exactement comme demandé — la complexité des deux mécanismes Compose sous-jacents (`profiles` + fichier compose additionnel) reste cachée dans le script de déploiement, pas exposée à l'usage quotidien. Un redémarrage du stack (backend inclus) est nécessaire pour appliquer le changement, ce qui est cohérent avec un usage occasionnel (bascule en cas de panne VPN ou de débogage), pas un toggle à la volée en production.

## 4. Stratégie de validation avant déploiement NAS

Valider chaque brique indépendamment, en local/devcontainer, avant tout déploiement sur le NAS de production — dans l'ordre, du plus isolé au plus proche de la prod :

1. **Le tunnel VPN seul** : démarrer uniquement `gluetun` (avec les vraies creds Mullvad) sur la machine de dev, et vérifier depuis un conteneur partageant son network namespace que l'IP de sortie a bien changé (`curl ifconfig.me` doit renvoyer une IP Mullvad française, pas l'IP réelle de la machine). Ne sollicite pas Babelio — valide uniquement la config Mullvad/WireGuard elle-même, le point le plus susceptible d'échouer bêtement (clé incorrecte, mauvais pays, credentials expirés).
2. **Backend routé via `gluetun`, en local** : appliquer `network_mode: "service:gluetun"` au backend en local (devcontainer ou Docker Compose local), et vérifier qu'un simple appel sortant (`curl babelio.com` **depuis le conteneur backend**, pas depuis `babelio_service.py`) passe bien par le tunnel. Un seul appel `curl` ponctuel ne sollicite pas plus Babelio qu'une visite normale du site — pas besoin de passer par le rate-limiter applicatif pour cette vérification de routage réseau pur.
3. **Kill switch** : couper délibérément le tunnel (credentials invalides, ou blocage temporaire côté Mullvad) et vérifier que le backend perd bien tout accès réseau plutôt que de basculer en clair vers l'IP locale. C'est le comportement de sécurité le plus critique à valider *avant* la prod — une régression ici resterait invisible tant qu'aucun ban ne se produit, donc pas détectable a posteriori sans test dédié.
4. **Toggle `WIREGUARD_ENABLED`** : basculer la variable `true`/`false` en local et vérifier que le stack démarre correctement dans les deux cas (avec et sans `gluetun`), sans configuration résiduelle qui laisserait le backend dans un état intermédiaire.
5. **Déploiement NAS**, en dernier, une fois les 4 étapes précédentes validées en local — avec `WIREGUARD_ENABLED=false` comme filet de sécurité immédiat en cas de problème (retour à la configuration actuelle sans VPN, sans avoir à toucher au reste du stack).

Cette progression limite le risque de re-solliciter Babelio pendant les tests (seule l'étape 2 fait un vrai appel réseau vers Babelio, et un unique `curl` ponctuel, pas une boucle de requêtes) — et surtout, elle évite de découvrir un problème de configuration VPN ou un défaut de kill switch directement en production sur le NAS.

## 5. Points de vigilance transverses

- **Légal/CGU** : contourner un blocage IP explicite d'un service tiers via VPN est un contournement délibéré des mesures anti-abus de Babelio, au-delà de la question technique. Les CGU des fournisseurs VPN eux-mêmes n'ont pas toutes pu être vérifiées avec certitude sur la clause spécifique "usage serveur/Docker" (recherche web, pas de lecture exhaustive des CGU légales). La clause "usage personnel, non-commercial" trouvée chez NordVPN n'est pas un obstacle pour ce projet : back-office-lmelp est open-source et ne génère aucun revenu. Les autres fournisseurs du comparatif sont ambigus ou favorables sur ce point.
- **Coût récurrent vs fréquence des bans** : ~2,50 à 5€/mois pour Mullvad/AirVPN. Contrairement à un incident isolé, le contexte (§0) montre des bans **récurrents depuis le début du projet**, déjà contournés manuellement à plusieurs reprises (VPN mobile + point d'accès Wi-Fi à l'époque du Docker local) — la fréquence exacte n'est pas quantifiable précisément, mais le motif est structurel. Un coût de quelques euros par mois pour éliminer une corvée de contournement manuel récurrente est a priori favorable, à condition que la charge opérationnelle du point suivant reste maîtrisée.
- **Complexité opérationnelle ajoutée** : un service supplémentaire (`gluetun`) à superviser sur le NAS auto-hébergé, un point de défaillance de plus (si le VPN tombe, **tout le backend** est indisponible avec l'architecture `network_mode` proposée en §1 — pas seulement Babelio), un compte VPN à maintenir dans la durée. C'est le vrai arbitrage : remplacer une corvée manuelle ponctuelle (reconnecter un VPN sur un téléphone) par une dépendance permanente et automatique, avec son propre risque de panne.
- **Impact performance** : négligeable en théorie — le trafic Babelio est déjà throttlé à 1 requête toutes les 2-5 secondes (`BABELIO_FAIR_SEC`), la latence additionnelle d'un tunnel WireGuard (généralement 1-2 chiffres de ms) est invisible à cette échelle. Non mesuré en conditions réelles (nécessiterait de déployer une solution pour le vérifier).

## Recommandation finale

**Le VPN est justifié étant donné l'historique récurrent des bans**, mais avec une portée volontairement limitée pour ne pas faire dépendre tout le backend d'un composant supplémentaire.

Ce qui a fait pencher la balance par rapport à une première lecture superficielle de l'issue #285 (qui semblait n'être qu'un incident isolé) :
- Le problème n'est pas nouveau : il a déjà été contourné manuellement à plusieurs reprises depuis le début du projet (VPN mobile + point d'accès Wi-Fi avant l'hébergement NAS).
- Le rate-limiter/circuit-breaker actuel (`babelio_service.py`), pourtant conçu spécifiquement pour limiter les bans, n'a pas suffi à éviter un nouveau ban après le passage sur le NAS.
- L'usage n'étant pas commercial (projet open-source, aucun revenu), la clause la plus restrictive du comparatif (NordVPN) ne s'applique pas — le champ des solutions viables est donc plus large que redouté initialement.

**Réserves qui restent valables et orientent la façon d'implémenter, pas la décision d'y aller** :
- Le VPN ne résout pas le problème structurellement — il **déplace** le risque de ban vers une nouvelle IP, qui peut à son tour être bannie un jour. Ce n'est pas une garantie définitive, mais une réduction de fréquence probable (une IP VPN dédiée à cet usage devrait accumuler moins de trafic suspect qu'une IP domicile partagée avec tout le reste de l'usage internet du foyer).
- L'architecture `network_mode: "service:gluetun"` proposée en §1 fait dépendre tout le backend (pas seulement Babelio) de la santé du tunnel — c'est un compromis à assumer consciemment, pas à découvrir après coup. Une architecture plus sélective (VPN scopé aux seuls appels sortants vers Babelio/Anna's Archive/RadioFrance, le reste du backend restant sur le réseau normal) serait plus sûre mais plus complexe à mettre en œuvre avec les outils standards (`gluetun` route tout le conteneur, pas un sous-ensemble de destinations) — à étudier plus avant si cette réserve s'avère bloquante en pratique.

**Proposition de mise en œuvre** (implémentation hors scope de cette étude, à traiter dans un ticket dédié) :
1. **Mullvad** (le plus documenté pour cet usage, prix le plus lisible et flat, pas de compte email requis) avec sidecar `gluetun` et **IP fixe** (pas de rotation automatique, pour préserver la validité du cookie anti-captcha actuel).
2. En parallèle, le proxy interne pour les covers (§3) — celui-ci a un intérêt propre indépendant du VPN : mettre les couvertures en cache disque après un premier scraping réussi réduit de toute façon le volume de requêtes futures vers Babelio, quel que soit le mécanisme réseau utilisé pour les récupérer.
3. Prévoir dès le départ une alerte (log, ou notification) en cas de coupure du tunnel VPN détectée par le healthcheck `gluetun`, pour éviter une panne silencieuse prolongée de tout le backend.

Ce document sert de base de décision — aucune implémentation n'a été réalisée dans le cadre de cette étude, conformément au périmètre de l'issue #286.

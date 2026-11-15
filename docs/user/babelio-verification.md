# Guide Utilisateur - Intégration Babelio

## Vue d'ensemble

L'intégration Babelio enrichit automatiquement la base de données avec des liens vers les fiches Babelio des livres et auteurs. Le système vérifie l'orthographe, valide les données bibliographiques, et maintient à jour les URLs Babelio pour faciliter l'accès aux informations détaillées.

## Accès aux fonctionnalités

### Validation bibliographique
**Navigation** : Menu principal → **Livres et Auteurs**

### Gestion de la migration Babelio
**Navigation** : Menu principal → **Gestion Babelio** ou accès direct via `/babelio-migration`

## Comprendre les indicateurs de validation

Dans le tableau des livres, la colonne **"Validation Biblio"** affiche l'un des indicateurs suivants :

### ✅ Validé
**Signification** : Les données sont correctes et confirmées par Babelio.

**Action** : Aucune, les informations sont fiables.

### 🔄 Suggestion
**Signification** : Le système propose une correction orthographique.

**Exemples** :
- "Alain Mabancou" → "Alain Mabanckou" (correction auteur)
- "Tant mieu" → "Tant mieux" (correction titre)

**Action** : Cliquez sur l'indicateur pour voir les détails de la suggestion (original → corrigé).

**Valider une suggestion** : quand Babelio a trouvé le livre suggéré, le champ **URL Babelio** de la
modale « Valider la suggestion » est déjà rempli. Titre, auteur et éditeur sont alors repris de la
page Babelio, et vous voyez ce que vous validez. Si le champ est vide (livre non trouvé sur Babelio,
suggestion venant uniquement du résumé des avis), collez vous-même l'URL de la page Babelio du livre :
l'extraction se déclenche de la même façon.

Le livre est créé avec cette URL Babelio, sa couverture et l'URL Babelio de l'auteur. Il n'apparaît
donc pas dans **Liaison Babelio des livres**. Il en va de même pour l'ajout manuel d'un livre
« Non trouvé » avec une URL collée.

### ❓ Non trouvé
**Signification** : Aucune correspondance fiable n'a été trouvée sur Babelio.

**Raisons possibles** :
- Faute d'orthographe importante
- Livre récent non encore référencé
- Inversion de nom (ex: "Le Floch" → "Lefloc")
- Titre mal transcrit, absent du titre et de la description de l'émission : le système ne
  propose jamais à la place le titre d'un autre livre de la même émission, ni un titre trop
  éloigné de l'original (ex: "Rouge Truite" pour *Rouges Truites*)

**Action** : Vérification manuelle nécessaire. Consultez directement [Babelio.com](https://www.babelio.com) pour confirmation.

### ⚠️ Erreur
**Signification** : Problème technique lors de la vérification.

**Action** : Cliquez sur le bouton **Retry** pour relancer la validation.

## Comment fonctionne la validation ?

Le système combine **plusieurs sources** pour maximiser la fiabilité :

1. **Vérification directe Babelio** : Test rapide si les données sont exactes
2. **Recherche dans les métadonnées d'épisode** : Recherche fuzzy dans titre/description de l'épisode
3. **Validation croisée auteur + titre** : Vérification que l'auteur correspond bien au livre

**Titres courants** : Babelio est d'abord interrogé sur le titre seul. Pour un titre porté par
de nombreux livres (« L'Héritage »), les premiers résultats sont des homonymes populaires et le
livre de l'auteur n'y figure pas forcément. Quand aucun résultat n'est de cet auteur, une seconde
recherche « titre + auteur » est faite (une seule, mise en cache 24 h) : elle retrouve le bon livre
et son URL Babelio.

**Priorité** : Les données de l'épisode (vérifiées par l'éditeur France Inter) sont prioritaires sur les corrections Babelio quand elles sont fiables.

## Enrichissement automatique de l'éditeur

Lors de l'extraction des livres depuis les avis critiques, le système enrichit automatiquement les données avec l'information d'éditeur provenant de Babelio.

### Fonctionnement

**Extraction automatique** :
- Lorsqu'un livre est validé avec un score de confiance ≥ 0.90
- Le système récupère automatiquement le nom de l'éditeur depuis la page Babelio
- L'information est ajoutée au livre dans le cache

**Mise à jour des avis critiques** :
- Lorsqu'une correction d'auteur ou de titre est validée
- Le résumé de l'avis critique est automatiquement mis à jour
- L'éditeur Babelio remplace l'éditeur original si disponible

**Enrichissement différé** :
- Si un livre possède une URL Babelio mais pas d'éditeur
- Le système récupère automatiquement l'éditeur lors du prochain chargement
- Cette information est mise en cache pour éviter les requêtes répétées

### Avantages

- ✅ **Données complètes** : Éditeur automatiquement renseigné pour ~90% des livres
- ✅ **Réduction saisie manuelle** : Moins de champs à compléter manuellement
- ✅ **Qualité des données** : Source Babelio fiable et à jour
- ✅ **Performance** : Cache intelligent évite les requêtes redondantes

## Ré-extraction manuelle depuis Babelio

La page détail d'un livre affiche un bouton orange **↻ Ré-extraire** (visible uniquement si le livre possède une URL Babelio) permettant de rafraîchir les données du livre.

### Données rafraîchies

- **Titre** : Titre complet depuis Babelio
- **Éditeur** : Nom de l'éditeur, stocké via la collection `editeurs` dédiée (avec recherche accent/case insensitive)
- **Auteur** : Nom et URL Babelio de l'auteur

### Fonctionnement

1. Cliquer sur le bouton **↻ Ré-extraire** (animation de rotation pendant le chargement)
2. Le système scrape les données fraîches depuis Babelio (~20 secondes)
3. Si des différences sont détectées, elles sont appliquées automatiquement
4. Une notification toast confirme le résultat :
     - **Vert** : Modifications appliquées avec succès
     - **Bleu** : Données déjà à jour (aucune modification nécessaire)
     - **Rouge** : Erreur lors de l'extraction

### Gestion des éditeurs

Lors du rafraîchissement, l'éditeur extrait est référencé dans la collection `editeurs` :

- Si l'éditeur existe déjà (recherche insensible aux accents et à la casse), son identifiant est réutilisé
- Sinon, un nouvel éditeur est créé automatiquement
- Le livre est mis à jour avec la référence `editeur_id` au lieu d'un simple champ texte

## Cas d'usage typiques

### Utilisateur final (consultation)
1. Sélectionnez un épisode dans la liste déroulante
2. Consultez le tableau des livres avec validation automatique
3. Identifiez rapidement les erreurs orthographiques (🔄)

### Correcteur d'épreuves (validation qualité)
1. Parcourez les épisodes récents
2. Vérifiez les suggestions (🔄) pour confirmer les corrections
3. Traitez manuellement les cas "Non trouvé" (❓)

### Enrichissement de données
1. Utilisez les suggestions validées pour mettre à jour la base de données
2. Récupérez les liens Babelio pour métadonnées supplémentaires (couverture, notes)

## Cookie Babelio (anti-bot)

Babelio active parfois un système anti-bot qui bloque les requêtes automatiques avec une erreur 403. Pour contourner ce blocage, les pages **Livres et Auteurs**, **Liaison Babelio des livres** et **Contrôle Babelio** proposent le même panneau **🔑 Cookie Babelio**, qui permet de fournir un cookie de session valide.

### Obtenir le cookie

1. Ouvrez [babelio.com](https://www.babelio.com) dans Firefox
2. Si un captcha s'affiche, résolvez-le
3. Appuyez sur **F12** → onglet **Réseau** (Network)
4. Rechargez la page (F5) et cliquez sur la requête `/` vers `babelio.com`
5. Dans **En-têtes de la requête**, faites un clic droit sur **Cookie** → **Copier la valeur**

### Configurer le cookie dans l'interface

1. Sur la page **Livres et Auteurs**, sélectionnez un épisode (ou ouvrez **Liaison Babelio des livres** ou **Contrôle Babelio**). Le panneau apparaît aussi dans l'encadré « URL Babelio » des modales d'ajout et de validation d'un livre, dès qu'une URL y est saisie
2. Collez la valeur du cookie dans le champ de texte. Si un cookie actif est déjà enregistré, le champ est masqué : cliquez d'abord sur **Entrer un cookie plus récent**
3. Cliquez sur **Enregistrer**

Une confirmation « ✓ Cookie enregistré » s'affiche, le champ se referme et le badge indique l'état du cookie **côté serveur** :

| Badge | Signification |
|---|---|
| ⚠ non configuré (risque 403) | Le serveur n'a pas de cookie : le champ de saisie est affiché |
| ✓ Actif côté serveur · enregistré à 16:04 · expire dans ~4 min | Cookie utilisable ; le temps restant diminue sans recharger la page |
| ⏰ périmé — collez un cookie frais | Le cookie a dépassé sa durée de vie : le champ de saisie réapparaît |

**Le cookie se colle frais à chaque fois** : le navigateur n'en garde aucune copie, et le champ démarre toujours vide. Seul le serveur conserve le cookie et le joint à toutes les requêtes Babelio (validation, scraping de pages, liaison manuelle par URL, couvertures).

**Le texte collé est vérifié avant l'envoi** : il doit s'agir de la valeur de l'en-tête **Cookie** de la requête, avec un `jstsToken`. Un User-Agent, un en-tête `Set-Cookie` de la réponse ou plusieurs lignes d'en-têtes sont refusés avec un message qui indique quoi copier. Un préfixe `Cookie:` collé par erreur est retiré.

**Durée de validité** : le cookie `jstsToken` expire après 5 minutes. Rafraîchissez-le avant de relancer un traitement long.

**Le serveur n'envoie jamais un cookie périmé** : il date le cookie à l'enregistrement et, au-delà de `BABELIO_COOKIE_MAX_AGE_SEC` (300 s par défaut), refuse d'appeler Babelio plutôt que de risquer un 403.

**Les requêtes portent l'identité de votre navigateur** : en cliquant sur **Enregistrer**, le navigateur transmet aussi son User-Agent et sa langue. Le serveur les reprend pour toutes les requêtes Babelio, avec l'empreinte réseau d'un Firefox (TLS et HTTP/2). Babelio émet le `jstsToken` pour le navigateur qui a résolu son défi anti-robots : présenté par un client différent, le jeton trahit un robot. Récupérez donc le cookie avec le navigateur depuis lequel vous utilisez lmelp. La page **Contrôle Babelio** (`GET /api/babelio/status`) affiche l'identité retenue.

!!! warning "Un 403 Babelio devient un ban IP"
    Quelques minutes après un 403, Babelio ignore toute connexion venant de l'IP
    (aucune réponse, même pas une erreur) pendant environ 24 h. Changer le
    cookie n'y fait rien. Pendant un ban, inutile d'insister : attendre la levée.

### Savoir si l'IP est bannie

Le bouton **🔄 Rafraîchir** de la page **Contrôle Babelio** fait un simple essai de connexion vers Babelio, puis la referme aussitôt : aucune requête n'est envoyée. Une IP bannie ne parvient pas à se connecter, Babelio ne voit donc rien. Une IP libre se connecte, et Babelio ne voit qu'une connexion vide, absente des journaux dont se nourrit son anti-robots. L'essai ne peut donc ni provoquer ni prolonger un ban.

| Ligne de Contrôle Babelio | Affichage | Signification |
|---|---|---|
| **État du service** (badge en haut) | ✅ OK, 🚫 Bloqué (403), ⚠️ Captcha, 🟡 Dégradé | Résultat de la dernière vraie requête à Babelio |
| | 🟢 Joignable | Aucune requête récente, mais le dernier essai de connexion a réussi : l'IP n'est pas bannie (le cookie, lui, n'est pas vérifié) |
| | 🚫 IP bannie | Le dernier essai de connexion a échoué |
| | ❔ Non testé | Ni requête ni essai depuis le démarrage du serveur |
| **Accès réseau (essai TCP)** | ✓ Joignable / 🚫 Injoignable — IP bannie / Non testé | Résultat et heure du dernier essai |
| **Circuit breaker** | 🚫 Ouvert — 403, cookie à renouveler | Un 403 a été reçu : coller un cookie frais |
| | 🚫 Ouvert — IP bannie, inutile de changer le cookie | Une connexion n'a pas abouti : attendre la levée du ban |

### Comprendre un 403

Avec un 403, Babelio renvoie une page qui en dit la raison : refus sec, défi anti-robots, message explicite. Le serveur garde les dix dernières réponses 403 (en-têtes reçus, début de la page, en-têtes envoyés avec le cookie masqué). On les lit sur `GET /api/babelio/blocked-responses`, sans envoyer de requête à Babelio. Elles sont perdues au redémarrage du serveur.

**Le disjoncteur suit l'essai** : un essai qui échoue l'ouvre (plus aucune requête ne part), un essai qui réussit referme un disjoncteur ouvert par un ban IP, sans exiger de nouveau cookie. Un disjoncteur ouvert par un 403 ne se referme qu'avec un cookie frais.

**Vérification avant traitement** : **Valider avec Babelio** (page Livres et Auteurs) et le lancement de la liaison (page Liaison Babelio des livres) font d'abord un essai d'une seconde. Si l'IP est bannie, le traitement s'arrête aussitôt avec le message « Babelio injoignable : IP bannie, inutile de changer le cookie », au lieu d'attendre l'expiration de la première requête.

### Blocages détectés

Le système distingue les deux causes de blocage :

- **Ban IP** : un bandeau 🚫 « Babelio injoignable : IP bannie, inutile de changer le cookie » s'affiche sur **Livres et Auteurs** et **Liaison Babelio des livres**. Le panneau cookie ne s'ouvre pas : un cookie ne lèverait pas le ban.
- **403 Babelio** (cookie expiré en cours de traitement, par exemple) :
    - Sur **Livres et Auteurs** : une bannière rouge ⚠️ s'affiche en haut de page et le panneau cookie s'ouvre
    - Sur **Liaison Babelio des livres** : un bandeau rouge 🚫 « Babelio bloque les requêtes (403) »
      s'affiche en haut de page tant que le circuit breaker est ouvert, ou que le dernier appel a reçu
      un 403 sans cookie actif. Il disparaît dès qu'un cookie frais est enregistré. La dernière liaison
      arrêtée par un 403 s'intitule « 🚫 Dernière liaison interrompue : Babelio bloqué (403) » et le
      livre concerné est marqué « 🚫 403 ». Dans le popup de saisie d'URL, le message d'erreur contient "403".

Pour un 403, la solution est toujours la même : rafraîchir le cookie et relancer.

**Relancer les livres bloqués par un 403** (page **Liaison Babelio des
livres**) : un livre bloqué par un 403 pendant la migration automatique
n'est jamais classé "à traiter manuellement" — il reste éligible à un
nouveau passage. Un bandeau **"⚠️ N livre(s) bloqué(s) par une erreur
403"** apparaît automatiquement quand de tels cas existent, avec un bouton
**"🔄 Relancer tous les 403"** : après avoir rafraîchi le cookie, ce bouton
remet ces livres dans la file d'attente et relance la migration
automatique dessus.

## Limitations connues

- **Rate limiting** : 2 secondes entre requêtes vers Babelio (validation peut prendre 30-40 secondes par livre)
- **Cas difficiles** : Inversions de nom, segmentation incorrecte nécessitent intervention manuelle
- **Dépendance externe** : Nécessite connexion internet pour interroger Babelio
- **Anti-bot Babelio** : Erreurs 403 possibles si l'IP est bloquée — fournir un cookie via la section 🔑 Cookie Babelio

## Migration automatique des URLs Babelio

### Objectif

Le système de migration enrichit automatiquement la base de données avec les URLs Babelio manquantes pour les livres et auteurs existants.

### Fonctionnement

**Phase 1 - Livres sans URL** :
- Recherche automatique sur Babelio par titre et auteur
- Validation de la correspondance avec normalisation du texte
- Extraction de l'URL auteur depuis la page livre
- Mise à jour automatique des champs `url_babelio`

**Phase 2 - Auteurs sans URL** :
- Détection des auteurs dont les livres ont une URL mais pas l'auteur
- Scraping de l'URL auteur depuis les pages livres existantes
- Complétion automatique des URLs manquantes

### Interface de gestion (`/babelio-migration`)

L'interface permet de gérer la migration et de traiter les cas problématiques :

**Statistiques** :
- Nombre total de livres et auteurs
- Taux de complétion des URLs Babelio
- Progression en temps réel

**Actions disponibles** :
- **Démarrer/Arrêter la migration** : Lancement des phases 1 et 2
- **Logs de progression** : Suivi détaillé livre par livre
- **Gestion des cas problématiques** : Traitement manuel des cas non résolus automatiquement

### Cas problématiques

Certains livres ou auteurs nécessitent un traitement manuel :

**Raisons fréquentes** :
- Titre trouvé sur Babelio ne correspond pas exactement
- Livre absent de Babelio (`babelio_not_found: true`)
- Auteur dont tous les livres sont absents de Babelio

**Actions manuelles** :
- **Accepter la suggestion** : Valider l'URL proposée malgré la différence de titre
- **Marquer comme non trouvé** : Confirmer l'absence sur Babelio
- **Supprimer du suivi** : Retirer des cas problématiques après traitement

Un livre lié à Babelio par un autre chemin (validation dans **Livres et Auteurs**, par exemple) ou
marqué absent de Babelio n'est plus compté dans « À traiter manuellement », ni affiché dans la liste,
même si son cas problématique existait avant.

### Affichage des liens Babelio

Les liens Babelio sont affichés sur les pages de détail :

**Pages livre** (`/livre/{id}`) :
- Icône Babelio 80x80px cliquable
- Lien direct vers la fiche Babelio du livre
- Design avec effet hover (couleur brand #FBB91E)

**Pages auteur** (`/auteur/{id}`) :
- Icône Babelio 80x80px cliquable
- Lien direct vers la fiche Babelio de l'auteur
- Layout cohérent avec les liens RadioFrance

### Normalisation intelligente

Le système normalise automatiquement les textes pour améliorer la correspondance :

**Transformations appliquées** :
- Ligatures : œ → oe, æ → ae
- Apostrophes typographiques : ' → '
- Suppression de la ponctuation
- Conversion en minuscules

**Stratégie de secours** :
- Recherche titre + auteur en priorité
- Si échec → Recherche auteur seul
- Scraping de l'URL depuis la page résultat

### Rate limiting

Le système respecte les limitations de Babelio :

- **Délai entre requêtes** : 2 secondes (configurable via `BABELIO_MIN_INTERVAL`)
- **Gestion gracieuse** : Arrêt automatique si Babelio indisponible
- **Reprise possible** : La migration peut être relancée à tout moment

## Récupération automatique des couvertures

### Objectif

Le système récupère automatiquement les URLs de couvertures des livres depuis Babelio et les stocke dans le champ `url_cover` de la collection `livres`. Une fois récupérée, la couverture est affichée automatiquement dans la fiche détail du livre (`/livre/{id}`).

### Pré-requis : cookie Babelio

Le scraping de couvertures (et plus généralement toutes les extractions depuis les pages Babelio, y compris la mise à jour manuelle par URL) peut nécessiter un cookie de session valide si Babelio active sa protection anti-bot. Ce cookie est collé dans l'interface puis gardé par le serveur, qui l'utilise pour toutes ses requêtes Babelio.

Le panneau **🔑 Cookie Babelio** est affiché en haut de la page `/babelio-migration` (juste sous le titre), avant les statistiques — il vaut pour toutes les sections de la page (liaison automatique, couvertures, URL manuelle).

**Obtenir le cookie Babelio :** voir la procédure détaillée dans [Cookie Babelio (anti-bot)](#cookie-babelio-anti-bot) plus haut dans ce document.

### Lancer la migration des couvertures

Dans `/babelio-migration`, section **Couvertures** :

1. Vérifiez que le cookie Babelio est actif (« ✓ Actif côté serveur » en haut de page)
2. Cliquez sur **Lancer la liaison des couvertures**
3. Le système traite les livres un par un, avec un délai de 5 secondes entre chaque requête
4. Les résultats s'affichent en temps réel :
   - ✅ Couverture récupérée avec succès
   - ⚠️ Redirection Babelio détectée (titre de page différent du titre attendu)
   - ❌ Erreur

### Statistiques des couvertures

| Indicateur | Signification |
|------------|--------------|
| **Liés à Babelio** | Livres ayant une URL Babelio (base de travail) |
| **Liés avec succès** | Livres avec `url_cover` récupérée |
| **À traiter manuellement** | Cas de redirection Babelio détectés |
| **En attente** | Livres restant à traiter |

### Cas à traiter manuellement (redirections Babelio)

Babelio redirige parfois une URL obsolète vers un livre différent. Lorsque cela se produit, le système détecte la redirection et affiche le cas dans la section **"À traiter manuellement"**.

**Pour chaque cas :**
- Le titre de la page Babelio réellement retournée est affiché
- Un champ URL est pré-rempli avec la couverture trouvée sur la mauvaise page (peut tout de même convenir si c'est la bonne couverture)
- **Sauvegarder** : accepte l'URL proposée (ou une URL modifiée manuellement)
- **Ignorer** : marque le cas comme traité sans sauvegarder de couverture

## En cas de problème

1. **Erreur de connexion** : Vérifiez votre connexion internet, puis cliquez sur Retry
2. **Résultats incorrects** : Signalez via GitHub Issues avec exemple précis (auteur + titre)
3. **Performance lente** : Normal avec beaucoup de livres (rate limiting Babelio 2 sec/requête)
4. **Migration bloquée** : Consultez les logs de progression pour identifier le problème
5. **Babelio indisponible** : La migration s'arrête automatiquement, relancez plus tard

## Documentation technique

Pour comprendre le fonctionnement détaillé du système de validation :

📖 **Développeurs** : Consultez [biblio-verification-flow.md](../dev/biblio-verification-flow.md)

📖 **Tests** : Consultez [validation-biblio-tests.md](../dev/validation-biblio-tests.md)

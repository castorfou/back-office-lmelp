# Issue #251 — Détection et signalement des blocages 403 Babelio (cookie silencieux)

## Contexte du problème

Après #247 (propagation du cookie `jstsToken`), les 403 Babelio sont revenus. Logs identiques :
`WARNING - Babelio HTTP 403 pour: {titre}` en masse sur la page Livres et Auteurs.

## Diagnostic en conditions réelles (devcontainer + VPN)

Reproduit le problème en lançant le backend localement avec `BABELIO_DEBUG_LOG=1` et en observant
les logs en temps réel pendant que l'utilisateur testait depuis le navigateur :

- **Sans cookie** : 403 systématique sur `search()` (AJAX) ET sur `_fetch_page()` (scraping de
  pages livre/auteur) — confirmé `Response status=403` dans les logs.
- **Avec un cookie jstsToken frais collé dans l'UI** : 0% de 403 sur un cycle complet de
  validation d'épisode.

**Conclusion** : le mécanisme de cookie de #247 fonctionne toujours techniquement. Le vrai
problème est l'absence totale de feedback/signal :

1. **Échec silencieux** : `search()`/`_fetch_page()` loggaient un warning sur 403 mais
   retournaient `[]`/`None` — strictement identique à "vraiment pas trouvé sur Babelio". Le
   frontend recevait `status='not_found'` sans aucun moyen de savoir qu'un blocage anti-bot
   avait eu lieu plutôt qu'une absence légitime.
2. **Pas de confirmation de sauvegarde** : le bouton "Enregistrer" du cookie ne donnait aucun
   retour visuel après clic — seule preuve : le petit badge "✓ configuré", facile à manquer.
3. **Pas d'awareness d'expiration** : le `jstsToken` a une TTL ~5 min côté Babelio. Rien
   n'avertissait l'utilisateur que son cookie précédemment sauvegardé était probablement devenu
   obsolète.

## Découverte additionnelle pendant les tests manuels (hors scope initial)

En testant la page "Liaison Babelio des livres" (`BabelioMigration.vue`, endpoint
`update_from_babelio_url`), l'erreur 403 apparaissait **même avec un cookie configuré** — page
différente de `LivresAuteurs.vue`. Root cause distincte : cette page avait son propre champ
cookie (fonctionnel pour `/api/babelio/extract-cover-url`) mais **`update_from_babelio_url()`
n'avait pas de paramètre `babelio_cookies` du tout** dans toute la chaîne service → endpoint →
frontend. Bug de propagation manquante, pas un problème de détection.

## Solution retenue — 3 volets

### 1. Backend : nouvelle exception `BabelioBlockedError`

`src/back_office_lmelp/services/babelio_service.py:40-45` — exception dédiée levée sur HTTP 403,
distincte des autres erreurs HTTP (503 etc. continuent de retourner `[]`/`None` comme avant).

- `search()` : `elif response.status == 403: raise BabelioBlockedError(...)` avant le `else`
  générique qui retourne `[]`. Le générique `except Exception` en fin de méthode re-raise
  `BabelioBlockedError` explicitement (`except BabelioBlockedError: raise` ajouté avant le catch
  générique) pour ne pas l'avaler.
- `_fetch_page()` : même pattern, `if response.status == 403: raise BabelioBlockedError(...)`
  avant le check `!= 200`.
- `verify_author()` et `verify_book()` : nouveau bloc `except BabelioBlockedError:` qui renvoie
  `status='blocked_403'` avec un `error_message` explicite, **avant** le catch générique
  `except Exception`.

**Piège critique** : `verify_book()` a 4 méthodes de scraping (`fetch_publisher_from_url`,
`fetch_full_title_from_url`, `fetch_author_url_from_page`, `_scrape_author_from_book_page`)
chacune avec son propre `try/except Exception` **interne** (pour ne pas faire échouer tout
`verify_book()` si un enrichissement optionnel échoue). Sans `except BabelioBlockedError: raise`
ajouté dans CES méthodes aussi, l'exception était avalée silencieusement avant même d'atteindre
le catch de `verify_book()`. Il a fallu ajouter `except BabelioBlockedError: raise` dans :
- Les 3 blocs `try` locaux dans `verify_book()` autour des appels d'enrichissement
  (`babelio_service.py:724-766` zone éditeur/titre/URL auteur)
- Les 4 méthodes de scraping elles-mêmes (chacune avait son propre `except Exception` interne)

### 2. Frontend `LivresAuteurs.vue` : bannière + confirmation + badge expiration

- `babelioBlocked` (bool) : affiche une bannière rouge `data-test="babelio-blocked-banner"` quand
  `autoValidateAndSendResults()` détecte `validationResult.status === 'blocked_403'`. Reset à
  `false` dans `saveBabelioCookie()`.
- `babelioCookieSavedAt` / `babelioCookieJustSaved` : confirmation "✓ Cookie enregistré"
  affichée 3s après clic sur Enregistrer (`setTimeout`, nettoyé dans `beforeUnmount`).
- `babelioCookieLikelyExpired` (computed) : badge "⏰ probablement expiré" si
  `Date.now() - babelioCookieSavedAt > 5min`. **Important** : reste `false` si
  `babelioCookieSavedAt` est `null` (cookie restauré d'une session précédente sans date connue)
  — évite un faux "expiré" non fondé.

### 3. Frontend `BabelioMigration.vue` : alignement UX + fix propagation manquante

- Ajout `babelio_cookies: this.babelioCookies || null` dans le POST `submitUrl()` vers
  `/api/babelio-migration/update-from-url` (`BabelioMigration.vue:790`) — **1 ligne**, c'était
  tout le bug de propagation manquante.
- Backend : `update_from_babelio_url()` (`babelio_migration_service.py:720-727`) gagne le
  paramètre `babelio_cookies: str | None = None`, propagé à `fetch_full_title_from_url()` et
  `fetch_author_url_from_page()`. Endpoint `app.py` (`UpdateFromBabelioUrlRequest`) gagne le champ
  `babelio_cookies`.
- **Demande utilisateur explicite** : remplacer le pattern auto-save-on-input
  (`@input="saveCookies"`) par le pattern explicite Enregistrer/Effacer de `LivresAuteurs.vue`,
  pour cohérence UX entre les deux pages. Renommé `saveCookies()` → `saveBabelioCookie()` +
  `clearBabelioCookie()`, ajout `babelioCookieInput` (brouillon) vs `babelioCookies` (valeur
  sauvegardée réellement envoyée aux appels API).
- **Demande utilisateur explicite** : déplacer le bloc cookie en haut de page (juste après le
  titre `<h2>Migration Babelio</h2>`), avant la section stats "📚 Livres" — précédemment il était
  enterré après 3 sections de stats + légendes.

## Fichiers modifiés

- `src/back_office_lmelp/services/babelio_service.py` — `BabelioBlockedError`, `search()`,
  `_fetch_page()`, `verify_author()`, `verify_book()`, User-Agent bump Firefox/142→151
- `src/back_office_lmelp/services/babelio_migration_service.py` — `update_from_babelio_url()`
  gagne `babelio_cookies`
- `src/back_office_lmelp/app.py` — `UpdateFromBabelioUrlRequest.babelio_cookies`
- `frontend/src/views/LivresAuteurs.vue` — bannière 403, confirmation save, badge expiration
- `frontend/src/views/BabelioMigration.vue` — boutons Enregistrer/Effacer, propagation cookie,
  repositionnement du bloc en haut de page
- `tests/test_babelio_403_detection.py` (nouveau, 7 tests)
- `tests/test_babelio_cookies_propagation.py` — `test_fetch_page_returns_none_on_non_200` changé
  de 403→503 (403 a maintenant son propre comportement dédié testé ailleurs)
- `tests/test_update_from_babelio_url.py` — nouveau test propagation + assertions existantes
  mises à jour avec `babelio_cookies=None`
- `tests/test_update_from_url_endpoint.py` — nouveau test + assertions mises à jour
- `frontend/tests/integration/LivresAuteurs.babelio403.test.js` (nouveau, 9 tests)
- `frontend/tests/BabelioMigration.cookieButtons.test.js` (nouveau, 5 tests)
- `frontend/tests/BabelioMigration.cookiePropagation.test.js` (nouveau, 2 tests)

## Pièges rencontrés

1. **Exceptions avalées par des `try/except Exception` imbriqués** : toujours vérifier TOUS les
   niveaux d'imbrication des try/except quand on introduit une nouvelle exception à propager.
   `verify_book()` avait 3 try/except locaux + 4 méthodes avec leur propre try/except = 7 points
   où `except BabelioBlockedError: raise` était nécessaire avant le catch générique.

2. **Tests existants à mettre à jour, pas seulement nouveaux tests** : changer le comportement
   sur 403 a cassé `test_fetch_page_returns_none_on_non_200` (qui utilisait justement un mock à
   403 pour tester le chemin générique "non-200"). Reflexe TDD : un changement de comportement
   featuré a un coût sur les tests existants qui testaient l'ancien comportement par accident.

3. **`git stash` + commande longue dans le même appel Bash** : `git stash && pytest ... && git
   stash pop` chaîné en une seule commande peut donner l'impression que le stash pop n'a pas eu
   lieu si la commande pytest est longue (le `git status` lancé en parallèle dans un autre appel
   voit l'état stashé). Toujours attendre la fin réelle de la commande chaînée avant de vérifier
   l'état git.

4. **Tests réseau réels non mockés ralentissent `pytest tests/`** : `tests/test_radiofrance_pagination.py`
   (classe `TestRadioFrancePaginationForOldEpisodes`, 4 tests) fait de vrais appels HTTP vers
   radiofrance.fr, jusqu'à 150s+ par test. Découvert en attendant ~8 min qu'une suite complète
   se termine. Tracé séparément dans l'issue #252 (à traiter plus tard, hors scope #251).

## Vérification manuelle effectuée

- Diagnostic confirmé en conditions réelles avec VPN + devcontainer sur la même IP (requis pour
  que le cookie Babelio soit valide), logs `BABELIO_DEBUG_LOG=1` observés en direct.
- Reproduit le 403 sans cookie, confirmé la résolution avec cookie frais, sur la page
  LivresAuteurs.
- Reproduit le bug de propagation manquante sur la page BabelioMigration ("Voir venir" + Lucile
  Novat, erreur "Babelio 403 scraping" visible dans le popup "Entrer URL Babelio").
- Validation finale par l'utilisateur sur les deux pages après tous les fix : "c'est parfait".

## Issue connexe créée

#252 — Tests `test_radiofrance_pagination.py` font de vrais appels réseau (lents/flaky), à
traiter dans un futur cycle séparé.

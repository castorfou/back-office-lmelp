# Issue #299 — SIGHUP tue start-dev.sh sans cleanup, laissant des process orphelins

## Problème

`scripts/start-dev.sh` ne trappait que `SIGINT SIGTERM`. Quand le script est lancé en arrière-plan simple (`./scripts/start-dev.sh &`, sans `nohup`/`disown`) depuis un outil dont le shell parent se termine juste après avoir passé la commande — c'est le cas systématique de l'outil Bash de Claude Code — la fin de ce shell parent envoie `SIGHUP` au job resté attaché.

Le comportement par défaut de bash pour `SIGHUP` sur un script non interactif est de le tuer **immédiatement, sans exécuter le trap `cleanup()`**. Les process backend (`python -m back_office_lmelp.app &`) et frontend (`npm run dev &`) que le script avait lui-même backgroundés restent alors vivants, réattachés à init — orphelins, invisibles dans `.dev-ports.json` (qui a été supprimé ou jamais nettoyé), mais toujours actifs sur leurs ports.

**Symptôme observé** : `.claude/get-services-info.sh` / `get-backend-info.sh` répondent "No active backend service found" alors que `ps aux | grep back_office_lmelp.app` montre un process vivant.

Root-cause confirmé par test A/B mené par l'utilisateur avant l'ouverture de l'issue : `./scripts/start-dev.sh &` (sans protection) → orphelins après extinction du shell parent ; `nohup ./scripts/start-dev.sh & disown` → stable.

## Fix appliqué

### 1. `scripts/start-dev.sh`

- **Trap SIGHUP** : `trap cleanup SIGINT SIGTERM SIGHUP` (au lieu de `trap cleanup SIGINT SIGTERM`). Fait exécuter `cleanup()` même en cas de SIGHUP.
- **Suppression conditionnelle de `.dev-ports.json`** dans `cleanup()` : le fichier n'est supprimé qu'après vérification (`kill -0`) que `$BACKEND_PID` et `$FRONTEND_PID` sont réellement morts après le force-kill. Si l'un des deux répond encore, le fichier est conservé avec un `warn` plutôt que supprimé silencieusement — pour qu'un orphelin éventuel reste détectable via `get-services-info.sh` au lieu de disparaître du radar.

Voir `scripts/start-dev.sh:190-215` (fonction `cleanup()`) et la ligne du `trap` juste après.

### 2. Documentation — `CLAUDE.md`

Deux notes ajoutées dans la section "Development Scripts" (après le paragraphe existant sur la vérification post-`kill`) :
- Toujours lancer `start-dev.sh` avec `nohup ./scripts/start-dev.sh > /tmp/start-dev.log 2>&1 & disown`, jamais un simple `&`, quand invoqué depuis un outil dont le shell parent se termine juste après (ex: Bash de Claude Code). Le trap SIGHUP est un filet de sécurité, pas un substitut à cette prévention.
- `.dev-ports.json` a été **volontairement retiré de `.gitignore`** (décision de l'utilisateur, pas de Claude) : le laisser apparaître dans `git status` permet de voir visuellement sa création/suppression, ce qui aide à détecter un cleanup raté. Attention à ne pas le commit par erreur — pas dramatique si ça arrive, mais à éviter.

### 3. Documentation — `docs/dev/start-dev-script.md`

- Section `cleanup()` mise à jour avec le nouveau code et un paragraphe "Pourquoi SIGHUP est trappé" expliquant les deux niveaux de protection (prévention via nohup/disown, filet de sécurité via le trap).
- Nouvelle entrée troubleshooting : "`.dev-ports.json` a disparu mais backend/frontend tournent encore" avec diagnostic et prévention.

### 4. Tests — `tests/test_start_dev_script.py`

Suivent le style existant du fichier (assertions statiques sur le contenu du script, pas d'exécution réelle — cohérent avec `test_script_handles_signal_trapping`) :
- `test_script_handles_sighup_signal` : vérifie que la ligne `trap cleanup ...` contient `SIGHUP`.
- `test_cleanup_checks_process_liveness_before_removing_ports_file` : extrait le corps de la fonction `cleanup()` (entre `cleanup() {` et l'appel `trap cleanup` qui suit) et vérifie qu'un check `kill -0` apparaît **avant** la ligne `rm -f "$PROJECT_ROOT/.dev-ports.json"`.

Cycle RED confirmé (2 tests échouent pour la bonne raison) puis GREEN (9/9 passent) avant de continuer.

## Vérification manuelle en conditions réelles

En plus des tests statiques, simulation réelle du scénario SIGHUP :
1. Lancement du script en arrière-plan (`./scripts/start-dev.sh &`, PID du script capturé).
2. Attente du démarrage effectif de backend + frontend (vérifié via `ps`).
3. `kill -HUP <PID_script>` pour simuler la fin du shell parent.
4. Résultat : log confirme l'exécution de `cleanup()`, `ps aux | grep -E "back_office_lmelp.app|vite"` ne montre **aucun** orphelin, `.dev-ports.json` correctement supprimé.

Cette étape a aussi permis de découvrir et nettoyer un vrai orphelin pré-existant dans l'environnement de dev (process d'une session précédente, PGID 191850) — confirmation en conditions réelles du bug décrit dans l'issue avant même d'appliquer le fix.

## Points pour les futures sessions

- **Toujours** lancer `start-dev.sh` avec `nohup ... & disown` depuis l'outil Bash, jamais un simple `&`. Voir [[precommit_vs_venv_tool_versions]] pour un autre piège d'environnement similaire (ne pas faire confiance aux apparences de succès sans vérification directe).
- `.dev-ports.json` n'est plus dans `.gitignore` : vérifier `git status` avant `git add`/commit sur ce genre de branche pour ne pas l'inclure par erreur.
- Le style de test de `tests/test_start_dev_script.py` (assertions de contenu string sur le script bash, pas d'exécution) est la convention à suivre pour toute évolution future de ce script — pas de framework de test bash dédié dans ce projet.

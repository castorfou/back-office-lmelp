---
name: cruft-update
description: Mise à jour du template PyFoundry dans ce projet (cruft update), avec le CHANGELOG, les migrations et la résolution des rejets. Utiliser quand l'utilisateur demande de mettre à jour le projet depuis le template, ou quand des rejets de cruft sont présents (fichiers .rej, marqueurs de conflit).
---

# Mise à jour du template

Applique au projet les changements du template depuis le commit enregistré dans `.cruft.json`, jusqu'à la tête de `main` (ou la référence donnée en argument). Un **rejet** est un changement que cruft n'a pas pu appliquer seul : un fichier `.rej`, ou des marqueurs de conflit dans le fichier.

Le script `.claude/skills/cruft-update/scripts/template_update.py` donne les faits ; lance-le depuis la racine du projet avec `python3`. Il est la seule source des catégories de fichiers.

**Auto-mise à jour** : si le dossier `{{ cookiecutter.project_slug }}/` existe à la racine, le projet est PyFoundry lui-même. Lis `.claude/skills/cruft-update/AUTO-MISE-A-JOUR.md` avant l'étape 5, et passe `--template-path .` à la sous-commande `changelog`.

## Étapes

### 1. Reprendre ou démarrer

Lance `python3 .claude/skills/cruft-update/scripts/template_update.py rejets`.

- Une sortie non vide : une mise à jour est en cours. Le commit de départ est celui de `.cruft.json` dans `HEAD` (`git show HEAD:.cruft.json`), le commit d'arrivée celui du `.cruft.json` du dossier de travail. Passe à l'étape 4.
- Une sortie vide : note le `commit` de `.cruft.json` (commit de départ) et continue.

### 2. Vérifier que le dépôt est propre

Lance `git status --porcelain` maintenant : l'état git donné au début de la conversation peut être périmé. La sortie doit être vide. Sinon, arrête-toi : montre `git status` et laisse l'utilisateur commiter ou remiser son travail. Ne remise ni ne commite rien à sa place.

### 3. Lancer cruft

1. Commit d'arrivée : `git ls-remote <template de .cruft.json> HEAD` (ou la référence demandée). S'il est égal au commit de départ, le projet est à jour : dis-le et arrête-toi.
2. Crée la branche `chore/template-update-<7 premiers caractères du commit d'arrivée>`.
3. Lance `cruft update -y` (ajoute `--checkout <référence>` si l'utilisateur en a donné une). Si cruft échoue avant d'appliquer quoi que ce soit (accès SSH au template, par exemple), montre l'erreur et arrête-toi. Les messages `patch failed`, `patch does not apply` et `Retrying again with a different update strategy` sont normaux : cruft passe de `git apply -3` à `git apply --reject` et laisse des rejets, que l'étape 5 traite.

Fin de l'étape : `.cruft.json` porte le commit d'arrivée.

### 4. Lire ce qui change

Lance `python3 .claude/skills/cruft-update/scripts/template_update.py changelog <départ> <arrivée>`. Résume les changements pour l'utilisateur, et recopie chaque point des rubriques `### Migration` dans une checklist : tu la dérouleras à l'étape 6.

Regarde aussi `git status` : fichiers ajoutés, supprimés ou modifiés par cruft sans rejet. Ils font partie du récapitulatif final.

### 5. Résoudre chaque rejet

Pour chaque ligne de `template_update.py rejets` (`catégorie`, `forme`, `chemin`), lis le changement voulu par le template (le contenu du `.rej`, ou le bloc entre marqueurs) et applique la règle de sa catégorie :

| Catégorie | Règle |
|-----------|-------|
| `template` | La version du template l'emporte. Si le côté local est une vraie personnalisation, et non une ancienne version du template, demande à l'utilisateur. |
| `projet` | La version locale l'emporte. N'applique pas le changement du template : signale-le à l'utilisateur. |
| `mixte` | Fusionne les deux côtés : garde les ajouts du projet (dépendances, pages, réglages) et prends les nouveautés du template. Pour `uv.lock`, garde la version locale puis lance `uv lock`. |
| `inconnu` | Demande à l'utilisateur. Pour la catégorie d'un autre fichier : `template_update.py categorie <chemin>`. |

Pose toutes tes questions en un seul message, chacune avec ta recommandation. Ensuite :

- un `.rej` : applique la décision dans le fichier, puis supprime le `.rej` ;
- un conflit : retire les marqueurs, puis `git add <chemin>`.

Fin de l'étape : `template_update.py rejets` ne renvoie plus rien, et chaque rejet a une décision notée pour le commit.

### 6. Dérouler les migrations

Pour chaque point de la checklist de l'étape 4 : fais-le s'il se fait dans le conteneur, sinon décris à l'utilisateur ce qu'il doit faire sur l'hôte, avec les commandes, et dans quel ordre par rapport au rebuild. Si `pyproject.toml` a changé, lance `uv sync --active --all-extras`.

Le HOME du conteneur est persistant : une modification de `postCreateCommand.sh` ne s'applique qu'au rebuild, et ne retire pas ce que l'ancienne version a écrit dans le HOME (`~/.zshrc`…). Si une résolution change ce que ce script écrit dans le HOME, signale-le et propose le nettoyage.

Fin de l'étape : chaque point est fait, ou transmis à l'utilisateur.

### 7. Vérifier

Lance `pre-commit run --all-files`, `pytest`, et `mkdocs build --strict` si `mkdocs.yml` existe. Corrige ce que la mise à jour a cassé ; signale ce qui échouait déjà avant. Un `pytest` qui ne trouve aucun test (code de sortie 5) n'est pas un échec.

Si `git diff --stat HEAD -- .devcontainer` n'est pas vide, préviens l'utilisateur qu'un rebuild du devcontainer est nécessaire.

Fin de l'étape : les trois commandes passent, ou chaque échec restant est expliqué à l'utilisateur.

### 8. Commiter, puis demander avant de publier

`git add -A`, puis un commit `chore: cruft update vers <7 premiers caractères du commit d'arrivée>`. Son corps contient un tableau des rejets (fichier, catégorie, décision), les changements signalés mais non appliqués, et les migrations laissées à l'utilisateur. Si un hook pre-commit modifie des fichiers, ajoute-les et recommence le commit.

Demande ensuite à l'utilisateur s'il faut pousser la branche et ouvrir la pull request. Ne pousse rien sans son accord.

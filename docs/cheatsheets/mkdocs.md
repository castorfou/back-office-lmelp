

Cette page détaille la stack technique utilisée pour la documentation du projet, ainsi que les différents packages Python impliqués.

## MkDocs

*   **Usage** : Générateur de site statique rapide et simple, orienté documentation projet. Il construit le site HTML à partir de fichiers Markdown.
*   **Exemple** : Commande `mkdocs serve` pour visualiser le site en local avec rechargement automatique.
*   **Documentation** : [https://www.mkdocs.org/](https://www.mkdocs.org/)

## MkDocs Material

*   **Usage** : Thème de référence pour MkDocs. Il offre un design moderne (Material Design), responsive, et de nombreuses fonctionnalités natives (recherche instantanée, mode sombre, etc.).
*   **Exemple** : Configuration dans `mkdocs.yml` via `theme: name: material`.
*   **Documentation** : [https://squidfunk.github.io/mkdocs-material/](https://squidfunk.github.io/mkdocs-material/)

## MkDocs Git Revision Date Localized Plugin

*   **Usage** : Plugin affichant la date de dernière modification de chaque page en se basant sur l'historique Git, avec un formatage localisé (ex: français).
*   **Exemple** : Ajoute automatiquement "Dernière mise à jour : 24 novembre 2025" au bas des pages de documentation.
*   **Documentation** : [https://github.com/timvink/mkdocs-git-revision-date-localized-plugin](https://github.com/timvink/mkdocs-git-revision-date-localized-plugin)

## Click

*   **Usage** : Bibliothèque Python pour créer des interfaces en ligne de commande (CLI). Elle est ici épinglée en version `8.2.1` pour contourner un problème de compatibilité connu avec MkDocs.
*   **Exemple** : Dépendance transitive technique, pas d'usage direct pour la rédaction de documentation.
*   **Documentation** : [https://click.palletsprojects.com/](https://click.palletsprojects.com/)

## MkDocstrings (Python handler)

*   **Usage** : Permet de générer automatiquement la documentation de référence du code Python à partir des docstrings, et de l'insérer directement dans les pages Markdown.
*   **Exemple** : L'instruction `::: my_package.my_module` dans un fichier Markdown générera la documentation complète du module.
*   **Documentation** : [https://mkdocstrings.github.io/](https://mkdocstrings.github.io/)

## MkDocs Include Markdown Plugin

*   **Usage** : Permet d'inclure le contenu d'un fichier Markdown dans un autre. Très utile pour réutiliser le `README.md` racine dans la documentation sans duplication.
*   **Exemple** : ![Exemple d'include](img/md_include.png) pour insérer le contenu d'un fichier externe (affiché littéralement pour l'exemple).
*   **Documentation** : [https://github.com/twardoch/mkdocs-include-markdown-plugin](https://github.com/twardoch/mkdocs-include-markdown-plugin)

### ⚠️ Conflit avec Cookiecutter

Si vous utilisez la syntaxe ![Exemple d'include](img/md_include.png) dans vos fichiers Markdown au sein du template, elle entre en conflit avec le moteur de template **Cookiecutter** (qui utilise la même syntaxe Jinja2).

Pour éviter que Cookiecutter n'essaie d'interpréter ces inclusions lors de la génération/mise à jour du projet, vous devez les échapper avec ![raw](img/raw.png) :

![Exemple d'échappement raw](img/raw_escape_example.png)



## Annotations de Code

*   **Usage** : Fonctionnalité du thème Material permettant d'ajouter des annotations interactives (tooltips) directement dans les blocs de code ou les listes.
*   **Syntaxe** : Ajoutez un commentaire ` # (1)` à la fin d'une ligne de code, puis définissez l'annotation dans une liste numérotée en dessous du bloc.
*   **Documentation** : [https://squidfunk.github.io/mkdocs-material/reference/annotations/](https://squidfunk.github.io/mkdocs-material/reference/annotations/)


**Exemple :**

Le code:

![code](img/annotations.png)

Le rendu:

```python
def my_function():
    print("Hello")  # (1)
    return True
```

1.  Ceci est une annotation qui s'affichera au survol ou au clic sur le `(1)` dans le code.


## MkDocs Awesome Nav

*   **Usage** : Plugin permettant une gestion plus flexible et avancée de la navigation dans MkDocs.
*   **Exemple** : Permet de structurer le menu de navigation indépendamment de la structure des fichiers.
*   **Documentation** : (Se référer à la documentation du package spécifique utilisé, potentiellement un fork ou un nom similaire à `mkdocs-awesome-pages-plugin`)

## Pymdown Extensions

*   **Usage** : Ensemble d'extensions pour le parseur Python-Markdown, ajoutant des fonctionnalités riches à la syntaxe Markdown standard (admonitions, onglets, touches clavier, etc.).
*   **Exemple** : Utilisation de `!!! note` pour créer des encadrés d'information colorés.
*   **Documentation** : [https://facelessuser.github.io/pymdown-extensions/](https://facelessuser.github.io/pymdown-extensions/)
*   **adminition documentation** : [Supported types (note, warning, ...)](https://squidfunk.github.io/mkdocs-material/reference/admonitions/#supported-types)

## Extensions Markdown Configurées

Voici le détail des extensions activées dans `mkdocs.yml` :

*   **admonition** : Permet de créer des blocs d'avertissement ou de note (ex: `!!! note "Titre"`).
*   **codehilite** : Ajoute la coloration syntaxique aux blocs de code en utilisant Pygments.
*   **pymdownx.details** : Permet de créer des blocs dépliables/repliables (ex: `??? note "Détails"`).
*   **pymdownx.superfences** : Permet d'imbriquer des blocs de code et d'autres éléments complexes dans des listes ou des admonitions.
*   **pymdownx.tabbed** : Crée des onglets de contenu. Configuré avec `alternate_style: true` pour un style visuel alternatif.
*   **toc** : Génère automatiquement la table des matières. Configuré avec `permalink: true` pour ajouter des liens ancrés sur chaque titre.
*   **attr_list** : Permet d'ajouter des attributs HTML (classes, IDs) aux éléments Markdown (ex: `{: .my-class }`).
*   **md_in_html** : Permet d'utiliser de la syntaxe Markdown à l'intérieur de balises HTML brutes.
*   **pymdownx.highlight** : Gestion avancée de la coloration syntaxique. Configuré avec `anchor_linenums: true` (liens sur les numéros de ligne), `line_spans: __spam` (optimisation), et `pygments_lang_class: true`.
*   **pymdownx.inlinehilite** : Permet la coloration syntaxique pour le code en ligne (ex: `#!python print("hello")`).
*   **pymdownx.snippets** : Permet d'inclure des extraits de code provenant d'autres fichiers.
*   **pymdownx.arithmatex** : Support pour le rendu de formules mathématiques (LaTeX). Configuré avec `generic: true` pour une compatibilité large.
*   **pymdownx.emoji** : Permet d'utiliser des emojis via des codes courts (ex: `:smile:`).
*   **pymdownx.magiclink** : Convertit automatiquement les URL et liens bruts en liens cliquables.

## Doc et CICD

Le workflow `.github/workflows/docs.yml` automatise trois choses :

- **build --strict** : à chaque push touchant la doc, `mkdocs build --strict` capte les erreurs de structure au plus tôt.
- **Déploiement automatique sur GitHub Pages** : à chaque push sur `main`.
- **Déploiement manuel depuis une branche** : on lance le workflow à la main pour publier la doc d'une autre branche.

### Activer GitHub Pages (une fois par projet)

`docs.yml` publie avec GitHub Actions : dans **Settings → Pages → Build and deployment**, choisir **Source : GitHub Actions** (et non « Deploy from a branch »). Ce réglage du dépôt ne figure dans aucun fichier :

```bash
# Pages pas encore activé
gh api -X POST "repos/{owner}/{repo}/pages" -f build_type=workflow
# Pages déjà activé avec la mauvaise source
gh api -X PUT "repos/{owner}/{repo}/pages" -f build_type=workflow
# Vérifier : doit afficher workflow
gh api "repos/{owner}/{repo}/pages" --jq .build_type
```

Avec « Deploy from a branch », la doc semble publiée, mais GitHub lance à chaque push un run `pages build and deployment` qui échoue à l'étape « Build with Jekyll ».

### Publier la doc d'une branche

Une seule fois par projet, autoriser les branches à déployer. L'environnement GitHub `github-pages` n'accepte par défaut que la branche par défaut. Ce réglage du dépôt ne figure dans aucun fichier :

```bash
gh api -X POST "repos/{owner}/{repo}/environments/github-pages/deployment-branch-policies" -f name='*'
```

Copier la commande telle quelle, depuis le dossier du projet : `gh` remplace lui-même `{owner}` et `{repo}`. Une réponse `Not Found (HTTP 404)` signale le plus souvent un propriétaire ou un nom de dépôt mal saisi.

Ou dans l'interface : **Settings → Environments → github-pages → Deployment branches and tags → Add deployment branch or tag rule**, motif `*`.

Puis, pour chaque publication :

```bash
gh workflow run docs.yml --ref ma-branche
gh run watch
```

Ou dans l'interface : **Actions → 📚 Deploy Documentation → Run workflow**, en choisissant la branche.

!!! warning "Une seule doc en ligne"
    La doc de la branche remplace celle de `main` jusqu'au prochain déploiement depuis `main` (prochain push touchant la doc, ou `gh workflow run docs.yml --ref main`).

Sans l'autorisation, le job `deploy` échoue avec `Branch "ma-branche" is not allowed to deploy to github-pages due to environment protection rules`.

## Liens relatifs

Il est possible de faire des liens vers d'autres pages de la doc.

Il faut faire des liens relatifs.

Par exemple si je pars de la page `/docs/dev/documentation_tools.md`

Je peux pointer vers la page `/docs/user/README.md`, section "Contenu suggéré" avec

```markdown
[lien vers user README.md section Contenu suggéré](../user/README.md#contenu-suggéré)
```



## lancement sur un autre port

```bash
mkdocs serve -a localhost:8010
```

## markdown

### annotations

![alt text](img/annotations.png)

donne

```bash
uv add --active pandas # (1)
```

1.  le `--active` est essentiel pour utiliser l'env actif, sinon creation d'un nouveau venv


### mermaid

```mermaid
  graph TD;
      A-->B;
      A-->C;
      B-->D;
      C-->D;
```

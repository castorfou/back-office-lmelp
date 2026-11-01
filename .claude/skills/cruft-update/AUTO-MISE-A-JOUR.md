# Auto-mise à jour de PyFoundry

PyFoundry est un projet généré de son propre template : le dossier `{{ cookiecutter.project_slug }}/` est le squelette, la racine est le projet. La règle R1.5 aligne la racine sur le squelette à chaque modification. Lors d'une auto-mise à jour, presque tous les rejets sont donc déjà appliqués, ou visent un contenu qui n'a de sens que dans un projet généré.

À l'étape 5, remplace les règles par catégorie par un **verdict** pour chaque rejet :

| Verdict | Quand | Action |
|---------|-------|--------|
| **déjà appliqué** | La racine contient déjà le changement, éventuellement sous une forme propre à PyFoundry. | Aucune : supprime le `.rej`, ou garde la version locale du conflit. |
| **propre au projet généré** | Le changement concerne un contenu du squelette sans équivalent à la racine (exemple : la doc utilisateur d'un projet généré, son `README.md`). | Aucune : supprime le `.rej`, ou garde la version locale. |
| **trou à combler** | La racine aurait dû recevoir le changement et ne l'a pas. | Applique-le à la racine, comme une omission de R1.5. |

Pour trancher, compare le rejet au fichier de la racine et à son équivalent dans `{{ cookiecutter.project_slug }}/`. En cas de doute entre « déjà appliqué » et « trou à combler », demande à l'utilisateur.

À l'étape 4, le template est le dépôt lui-même : `template_update.py changelog <départ> <arrivée> --template-path .`. Lance d'abord `git fetch` pour avoir le commit d'arrivée.

À l'étape 8, le tableau du commit liste les verdicts. Les auto-mises à jour précédentes en donnent des exemples : `git log --grep "cruft update"`.

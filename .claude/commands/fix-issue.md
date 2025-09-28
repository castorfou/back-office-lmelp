Utilise une todo list pour garder la trace complète de ce travail, et être sûr de ne rater aucune de ces 16 étapes. IMPORTANT : Ne marque jamais une étape comme 'completed' tant que tu n'as pas ENTIÈREMENT terminé cette étape, y compris toutes les sous-actions qu'elle contient. Si une étape contient plusieurs actions (comme 'créer une PR ET demander validation'), elle ne peut être marquée comme terminée que lorsque TOUTES les actions sont accomplies. Reste toujours sur l'étape en cours jusqu'à sa completion totale.
1. Utilise `gh issue view` pour récupérer les détails
2. Create a feature branch from issue using `gh issue develop {issue_number}`, then immediately checkout to that branch locally with `git checkout {branch_name}` before starting any work. Ensure you're working on the feature branch and NOT on main.
3. Comprends le problème décrit. And think deeply about the best approach to solve it
4. Cherche les fichiers concernés dans le codebase
5. Implémente la correction en TDD. Ecris d'abors les tests (qui echouent) puis le code
6. Itere entre code et execution des tests jusqu'a une resolution complete des problemes
7. Vérifie que tout passe (tests, lint, typecheck)
8. Cree les modifications necessaires dans la doc utilisateur et la doc developpeur
9. Demande à l'utilisateur de tester globalement (potentiellement refais une passe entre les points 4 à 9) jusqu'à satisfaction
10. Met à jour README.md et CLAUDE.md si necessaire
11.  Commit de façon atomique avec un message descriptif (precommit te forcera à faire quelques modifications) et push ces modifs
12. Verifie l'etat de la CI/CD (gh run view). Attend jusqu'à la fin de l'execution avant de continuer. Et corrige toutes les erreurs avant d'aller plus loin.
13. Prepare la pull request et demande à l'utilisateur de la valider. Sur cette validation tu utiliseras gh pour la valider et tu vérifieras que c'est effectivement bien le cas.
14. Clos la todo list si elle est bien vide
15. Repasse sur la branche main locale, et recupere les dernieres modifications
16. Finis en appelant la slash-command interne de claude
```claude
/stocke-memoire
```

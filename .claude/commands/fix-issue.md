1. Utilise une todo list pour garder la trace complete de ce travail, et être sûr de ne rater aucune etape
2. Utilise `gh issue view` pour récupérer les détails
3. Crée une PR venant de cette issue, et bascule sur la branche associée
4. Comprends le problème décrit
5. Cherche les fichiers concernés dans le codebase
6. Implémente la correction en TDD. Ecris d'abors les tests (qui echouent) puis le code
7. Itere entre code et execution des tests jusqu'a une resolution complete des problemes
8. Vérifie que tout passe (tests, lint, typecheck)
9. Cree les modifications necessaires dans la doc utilisateur et la doc developpeur
10. Commit de façon atomique avec un message descriptif (precommit te forcera à faire quelques modifications) et push ces modifs
11. Verifie l'etat de la CI/CD (gh run view)
12. Demande à l'utilisateur de tester globalement (potentiellement refais une passe entre les points 3 à 10) jusqu'à satisfaction
13. Met à jour README.md et CLAUDE.md si necessaire
14. Prepare la pull request et demande à l'utilisateur de la valider

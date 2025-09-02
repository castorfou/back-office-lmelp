1. Utilise `gh issue view` pour récupérer les détails
2. Crée une PR venant de cette issue, et bascule sur la branche associée
3. Comprends le problème décrit
4. Cherche les fichiers concernés dans le codebase
5. Implémente la correction en TDD. Ecris d'abors les tests (qui echouent) puis le code
6. Itere entre code et execution des tests jusqu'a une resolution complete des problemes
7. Vérifie que tout passe (tests, lint, typecheck)
8. Cree les modifications necessaires dans la doc utilisateur et la doc developpeur
9. Commit de façon atomique avec un message descriptif (precommit te forcera à faire quelques modifications) et push ces modifs
10. Verifie l'etat de la CI/CD (gh run view)
11. Demande à l'utilisateur de tester globalement (potentiellement refais une passe entre les points 3 à 10) jusqu'à satisfaction
12. Met à jour README.md et CLAUDE.md si necessaire
13. Prepare la pull request et demande à l'utilisateur de la valider

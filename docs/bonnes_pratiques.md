## Recommandations pour une doc de qualité

Pour maintenir une documentation de qualité, voici les recommandations à suivre (par une IA ou pour un humain).

### ✅ Bonnes pratiques de rédaction

**Décrire l'état actuel** du système :

- Expliquer ce que le système **fait maintenant**

- Fournir des spécifications techniques et des exemples d'utilisation

- Documenter les fonctionnalités telles qu'elles existent

**Éviter** :

- ❌ Les références historiques ("L'issue #X a amélioré...")

- ❌ Les récits d'évolution ("Nous avons d'abord implémenté X, puis Y...")

- ❌ Les marqueurs temporels ("Nouvelle fonctionnalité", "Récemment ajouté")

- ❌ Les métriques de tests dans la documentation

### Exemple

**❌ Mauvais** :
> "Nouvelle dans l'issue #75 : La Phase 0 est maintenant bien meilleure grâce à la double confirmation...
> C'est une amélioration majeure par rapport à la version précédente."

**✅ Bon** :
> "La Phase 0 utilise deux mécanismes d'enrichissement : la double confirmation quand Babelio retourne
> un score de confiance entre 0.85 et 0.99, et la correction d'auteur quand les livres ne sont pas trouvés."

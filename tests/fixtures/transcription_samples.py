"""Fixtures avec exemples de transcriptions réelles pour tests."""

TRANSCRIPTION_SAMPLE_1 = """
Jérôme Garcin : Bonjour à tous et bienvenue dans Le Masque et la Plume.
Nous allons commencer cette émission par le courrier de la semaine.

[Section courrier]
Un auditeur nous écrit au sujet du livre dont nous avons parlé la semaine dernière...

[Programme principal]
Et maintenant, passons au programme de ce soir. Le premier livre que nous allons discuter est
"Les Gratitudes" de Delphine de Vigan, publié chez JC Lattès.

Elisabeth Philippe : J'ai adoré ce livre. Delphine de Vigan nous livre une histoire touchante
sur la vieillesse et la perte de la parole. C'est remarquable.

Michel Crépu : Je suis d'accord avec Elisabeth. C'est un très beau roman, sensible et délicat.
Delphine de Vigan maîtrise parfaitement son sujet. J'ai été ému.

Arnaud Viviant : Pour ma part, j'ai trouvé ce livre intéressant mais pas exceptionnel.
C'est bien écrit, mais l'histoire m'a paru un peu convenue.

Jérôme Garcin : Passons maintenant au deuxième livre de la soirée...
"""

TRANSCRIPTION_SAMPLE_2 = """
Jérôme Garcin : Bonsoir à tous. Ce soir, nous avons un programme riche avec plusieurs livres passionnants.

Commençons avec "Civilizations" de Laurent Binet, publié chez Grasset.

Patricia Martin : C'est un roman uchronique absolument génial. Laurent Binet imagine ce qui
se serait passé si les Incas avaient découvert l'Europe. C'est brillant, drôle, et très intelligent.
Un chef-d'œuvre.

Xavier Leherpeur : Je partage totalement l'enthousiasme de Patricia. C'est un livre formidable,
une réussite totale. Laurent Binet est un auteur remarquable.

Judith Perrignon : Oui, c'est très réussi. J'ai beaucoup aimé la façon dont Laurent Binet
renverse les perspectives. C'est très bien construit.

Jérôme Garcin : Et maintenant, le deuxième livre...
"""

EXPECTED_SUMMARY_PHASE1_SAMPLE_1 = """
## 1. LIVRES DISCUTÉS AU PROGRAMME du 15 janvier 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Delphine de Vigan | Les Gratitudes | JC Lattès | **Elisabeth Philippe**: Adoré, histoire touchante, remarquable (9/10) <br>**Michel Crépu**: Très beau roman, sensible et délicat, ému (9/10) <br>**Arnaud Viviant**: Intéressant mais pas exceptionnel, bien écrit (6/10) | <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.0</span> | 3 | Elisabeth Philippe, Michel Crépu | |

## 2. COUPS DE CŒUR DES CRITIQUES du 15 janvier 2025

Aucun coup de cœur supplémentaire mentionné dans cet épisode.
"""

EXPECTED_SUMMARY_PHASE1_SAMPLE_2 = """
## 1. LIVRES DISCUTÉS AU PROGRAMME du 20 janvier 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Laurent Binet | Civilizations | Grasset | **Patricia Martin**: Génial, brillant, drôle, très intelligent, chef-d'œuvre (10/10) <br>**Xavier Leherpeur**: Formidable, réussite totale, remarquable (9/10) <br>**Judith Perrignon**: Très réussi, très bien construit (8/10) | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | 3 | Patricia Martin, Xavier Leherpeur | Patricia Martin |

## 2. COUPS DE CŒUR DES CRITIQUES du 20 janvier 2025

Aucun coup de cœur supplémentaire mentionné dans cet épisode.
"""

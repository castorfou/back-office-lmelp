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

# Episode 678ccfcba414f229887782db: 09/04/2017 - Le masque et la plume livres
# Books: Ma Petite France (P. Péan), Norma (S. Oksanen), Marlène (P. Djian), et autres
# Issue #181: This episode failed with "Format markdown invalide" error
TRANSCRIPTION_EPISODE_2017_04_09 = """ Musique Le masque et la plume Bonsoir à tous et bienvenue en public au studio Sacha Guitry de la Maison de Radio France pour un masque et la plume consacré ce soir à l'actualité littéraire avec la petite France de la critique Nelly Capriélian, des inoccupables Olivia de Lamberie, Duelles, Arnaud Vivian de Transfuge, de Regards et de la Revue Charles avec Michel Crépu de la Nouvelle Revue Française pour parler ce soir. De Ma Petite France de Pierre Péan mais également des romans de Sophie Oxanen, Philippe Djan, Éry Deluca et du journal de Mathieu Gallet. L'écrivain, pas le patron de Radio France, dans le courrier de la semaine à propos du polar. D'Hervé Lecor, Arnaud, prendre les loups pour des chiens chez Rivage, Victor Boiré, signale Arnaud Vivian qu'il fait erreur. Les dix règles d'Elmore Leonard ne sont pas réservées au polar, mais à l'écriture d'un bon livre en général, se focalisant sur l'écriture et non pas sur les ressorts du suspense. En revanche, Borges a édicté quelques règles du roman policier dans son article « Loi de la narration policière », dont je recommande l'excellente explication de Guillermo Martinez. Toujours à propos du même polar d'Hervé Lecor, Olivier Patureau tient à souligner, ça c'est très important, la mauvaise foi de Jean-Louis Aisine, puisque page 11, il n'est pas écrit une espèce d'abrébus, mais l'espèce d'abrébus, ce qui évidemment change tout. Martine Laffont-Bayou, qui habite la Gironde, défend la raison, la vie mécanique de Christian Oster. Les critiques négatives au masque que j'ai entendu m'ont paru imméritées. Quoi ? Il faut désormais un scénario à rebondissement et de l'action pour soutenir l'attention du lecteur. Pourquoi ne pas prendre son temps, débrancher tous les appareils, fermer portes et fenêtres et laisser conduire Auster ? Le lecteur a de la place. Auster l'invite à partager sa route sans bavardage, d'égal à égal. Jean-Philippe Petier est en colère contre Philip"""

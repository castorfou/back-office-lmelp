"""
Fixtures contenant des exemples de summaries réels pour les tests d'extraction d'avis.

Chaque fixture contient:
- summary: Le contenu markdown du summary
- episode_date: La date de l'épisode
- expected_section1_count: Nombre d'avis attendus dans Section 1
- expected_section2_count: Nombre d'avis attendus dans Section 2
- description: Description du cas de test (format de notes, particularités)

Pour ajouter un nouveau summary:
1. Copier SAMPLE_TEMPLATE
2. Remplir les champs depuis les données MongoDB
3. Ajouter à AVIS_SUMMARY_SAMPLES
"""

from dataclasses import dataclass


@dataclass
class AvisSummarySample:
    """Structure pour un échantillon de summary d'avis."""

    summary: str
    episode_date: str
    emission_oid: str
    expected_section1_count: int
    expected_section2_count: int
    description: str
    # Optionnel: détails pour assertions plus fines
    expected_first_avis_section1: dict | None = None
    expected_first_avis_section2: dict | None = None


# =============================================================================
# Sample du 21 décembre 2025 - Format "Note: X"
# =============================================================================
SUMMARY_2025_12_21 = AvisSummarySample(
    episode_date="21 déc. 2025",
    emission_oid="emission_2025_12_21",
    description="Format 'Note: X' pour Section 1, HTML span pour Section 2",
    expected_section1_count=6,  # 4 critiques pour livre 1 + 2 pour livre 2
    expected_section2_count=2,
    summary="""## 1. LIVRES DISCUTÉS AU PROGRAMME du 21 décembre 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Rita Bullwinkel | Combats de filles | La Croisée | **Elisabeth Philippe**: Très belle découverte, original, divertissant, poétique. Note: 9 <br> **Arnaud Viviant**: Impressionnant, trouvailles stylistiques. Note: 8 <br> **Philippe Trétiack**: Magnifique, suspense, poignant. Note: 9 <br> **Patricia Martin**: Bien fichu, mais manque quelque chose. Note: 7 | <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.3</span> | 4 | Elisabeth Philippe, Philippe Trétiack | |
| Guillaume Poix | Perpétuité | Gallimard | **Arnaud Viviant**: Parfaitement instructif, dévorant. Note: 9 <br> **Elisabeth Philippe**: Sensoriel, précis, sans jugement. Note: 8 | <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.5</span> | 2 | Arnaud Viviant | |

## 2. COUPS DE CŒUR DES CRITIQUES du 21 décembre 2025

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Rachel Coquerel | 22 Masbury Road | Quai Voltaire | Philippe Trétiack | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">10</span> | Absolument passionnant, réussite |
| Esther Williams | La sirène d'Hollywood | Séguier | Elisabeth Philippe | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">10</span> | Très drôle, franc, pur délice |
""",
    expected_first_avis_section1={
        "livre_titre_extrait": "Combats de filles",
        "auteur_nom_extrait": "Rita Bullwinkel",
        "editeur_extrait": "La Croisée",
        "critique_nom_extrait": "Elisabeth Philippe",
        "note": 9,
        "section": "programme",
    },
    expected_first_avis_section2={
        "livre_titre_extrait": "22 Masbury Road",
        "auteur_nom_extrait": "Rachel Coquerel",
        "editeur_extrait": "Quai Voltaire",
        "critique_nom_extrait": "Philippe Trétiack",
        "note": 10,
        "section": "coup_de_coeur",
    },
)


# =============================================================================
# Sample du 26 octobre 2025 - Format "(X)" pour les notes
# =============================================================================
SUMMARY_2025_10_26 = AvisSummarySample(
    episode_date="26 oct. 2025",
    emission_oid="690081839e560935fc339083",  # pragma: allowlist secret
    description="Format '(X)' pour les notes en Section 1 (entre parenthèses), HTML span pour Section 2",
    expected_section1_count=20,  # 5 livres × 4 critiques = 20
    expected_section2_count=4,
    summary="""## 1. LIVRES DISCUTÉS AU PROGRAMME du 26 oct. 2025



| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Laura Vazquez | Les Forces | Éditions du Sous-Sol | **Jean-Marc Proust**: "C'est plutôt un bon livre, très beau, drôle, adhère au discours" (9) <br>**Elisabeth Philippe**: "Magnifique, force des images, hanter avec les images" (10) <br>**Philippe Trétiac**: "Très très beau livre, force énorme, images extraordinaires" (10) <br>**Patricia Martin**: "Sombre et somptueux, pensée raisonnée" (9) | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.5</span> | 4 | Elisabeth Philippe, Philippe Trétiac | Elisabeth Philippe, Philippe Trétiac |
| Anne Berest | Finistère | Albin Michel | **Elisabeth Philippe**: "Roman très ample, dommage, excès de pudeur" (6) <br>**Patricia Martin**: "Très touchant, portrait de la France, incarné" (8) <br>**Jean-Marc Proust**: "Problème géographique, pas convaincu" (5) <br>**Philippe Trétiac**: "Séduit au départ, roman territorial, faiblit" (7) | <span style="background-color: #CDDC39; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">6.5</span> | 4 | Patricia Martin | |
| Paul Gasnier | La Collision | Gallimard | **Philippe Trétiac**: "Trop de retenue, trop propre, bon journaliste" (6) <br>**Elisabeth Philippe**: "Démarche vertueuse, déséquilibre, cliché journalistique" (5) <br>**Jean-Marc Proust**: "Supériorité morale, parcours de deuil difficile" (5) <br>**Patricia Martin**: "Descente aux enfers, extrêmement compliqué" (7) | <span style="background-color: #CDDC39; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">5.8</span> | 4 | | |
| Javier Cercas | Le Fou de Dieu au bout du monde | Actes Sud | **Patricia Martin**: "Littéralement emballé, homme formidable" (8) <br>**Jean-Marc Proust**: "Complaisant, lénifiant, rien appris" (3) <br>**Philippe Trétiac**: "Déçu, manque de distance, rate la grâce" (4) <br>**Elisabeth Philippe**: "Tiédeur, étouffe chrétien" (4) | <span style="background-color: #FF9800; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">4.8</span> | 4 | | |
| Cédric Sapin-Defour | Où les étoiles tombent | Stock | **Elisabeth Philippe**: "Écriture chantournée, écran à l'émotion" (3) <br>**Philippe Trétiac**: "Livre absolument nul, mal écrit" (2) <br>**Patricia Martin**: "Justesse du récit, bien sentie" (6) <br>**Jean-Marc Proust**: "Catastrophe, débauche de platitude" (2) | <span style="background-color: #F44336; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">3.3</span> | 4 | | |
## 2. COUPS DE CŒUR DES CRITIQUES du 26 oct. 2025


| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Fabrice Gaignault | Un livre | Arléa | Philippe Trétiac | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.5</span> | "Formidable, déclenche un ouragan" |
| Anne Serre | Vertu et Rosalinde | Mercure de France | Elisabeth Philippe | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | "Pur délice, écriture ciselée, diamantine" |
| Aurore Vincenti | Pour une érotique du sensible | La Découverte | Patricia Martin | <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.0</span> | "Livre très joyeux, original et singulier" |
| Xavier Chapuis | L'Histoire de la littérature | Do | Jean-Marc Proust | <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.0</span> | "Assez drôle, rire, iconoclaste" |""",
    expected_first_avis_section1={
        "livre_titre_extrait": "Les Forces",
        "auteur_nom_extrait": "Laura Vazquez",
        "editeur_extrait": "Éditions du Sous-Sol",
        "critique_nom_extrait": "Jean-Marc Proust",
        "note": 9,
        "section": "programme",
    },
    expected_first_avis_section2={
        "livre_titre_extrait": "Un livre",
        "auteur_nom_extrait": "Fabrice Gaignault",
        "editeur_extrait": "Arléa",
        "critique_nom_extrait": "Philippe Trétiac",
        "note": 10,  # 9.5 arrondi à 10
        "section": "coup_de_coeur",
    },
)


# =============================================================================
# Liste de tous les samples pour les tests paramétrés
# =============================================================================
AVIS_SUMMARY_SAMPLES = [
    SUMMARY_2025_12_21,
    SUMMARY_2025_10_26,
]

# IDs pour pytest.mark.parametrize
AVIS_SUMMARY_IDS = [f"{sample.episode_date}" for sample in AVIS_SUMMARY_SAMPLES]


# =============================================================================
# Template pour ajouter de nouveaux samples
# =============================================================================
SAMPLE_TEMPLATE = """
# Pour ajouter un nouveau sample:
SUMMARY_YYYY_MM_DD = AvisSummarySample(
    episode_date="DD mois YYYY",
    emission_oid="oid_from_mongodb",
    description="Description du format particulier",
    expected_section1_count=0,
    expected_section2_count=0,
    summary=\"\"\"## 1. LIVRES DISCUTÉS AU PROGRAMME du ...
...
\"\"\"
)
# Puis ajouter à AVIS_SUMMARY_SAMPLES
"""

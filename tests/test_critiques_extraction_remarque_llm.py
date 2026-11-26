"""Remarque du LLM dans la colonne Critique des coups de cœur (Issue #406).

Émission du 29/11/2015 : une ligne de la section 2 porte, à la place du nom du
critique, « (Déjà dans le programme principal, ne pas dupliquer) ». Ce n'est
pas un critique : il ne doit pas compter comme critique manquant.
"""

from back_office_lmelp.services.critiques_extraction_service import (
    critiques_extraction_service,
)


# Section 2 telle qu'enregistrée en base pour cette émission (extrait)
SUMMARY = """## 2. COUPS DE CŒUR DES CRITIQUES du 29 novembre 2015

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Françoise Frenkel | Rien où poser sa tête | Gallimard (L'Arbalète) | (Déjà dans le programme principal, ne pas dupliquer) |  |  |
| Sempé | Sincères amitiés | Denoël | Olivia de Lamberterie | 10 | Absolument génial. |
"""


def test_llm_remark_in_critique_column_is_not_a_critic():
    names = critiques_extraction_service.extract_critiques_from_summary(SUMMARY)

    assert names == ["Olivia de Lamberterie"]

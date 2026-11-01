"""Service de génération d'avis critiques en 2 phases LLM."""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any

import openai


logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 8000

TABLE_FORMAT_RULE = (
    "⚠️ TABLEAUX COMPACTS: N'aligne JAMAIS les colonnes. Mets un seul espace de "
    'chaque côté de chaque "|", sans aucun espace de remplissage dans les cellules '
    "ni dans les en-têtes, même si les colonnes ne sont plus alignées."
)

# Un retry à température identique reproduit le même débordement d'espaces.
# Ne pas utiliser frequency_penalty: il déforme "**Nom**: ... Note: X", et
# l'extraction des avis perd alors ces critiques sans erreur.
PHASE1_ATTEMPT_TEMPERATURES = (0.1, 0.3)


class AvisCritiquesGenerationService:
    """Service pour générer avis critiques en 2 phases LLM."""

    def __init__(self):
        """Initialise le service de génération."""
        # Réutilisation config Azure OpenAI existante (mêmes noms que lmelp)
        self.azure_endpoint = os.getenv("AZURE_ENDPOINT")
        self.api_key = os.getenv("AZURE_API_KEY")
        self.api_version = os.getenv("AZURE_API_VERSION", "2024-09-01-preview")
        self.deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")

        # Configuration client
        if (
            self.azure_endpoint
            and self.api_key
            and self.azure_endpoint.strip()
            and self.api_key.strip()
        ):
            try:
                logger.info(
                    f"Initialisation Azure OpenAI client: endpoint={self.azure_endpoint}, "
                    f"deployment={self.deployment_name}, api_version={self.api_version}"
                )
                self.client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.azure_endpoint,
                )
                logger.info("✅ Azure OpenAI client initialisé avec succès")
            except Exception as e:
                logger.error(
                    f"❌ Erreur initialisation Azure OpenAI client: {type(e).__name__}: {e}"
                )
                self.client = None
        else:
            logger.warning(
                "⚠️ Azure OpenAI client non configuré - variables d'environnement manquantes ou vides"
            )
            logger.warning(f"  - AZURE_ENDPOINT: {'✓' if self.azure_endpoint else '✗'}")
            logger.warning(f"  - AZURE_API_KEY: {'✓' if self.api_key else '✗'}")
            logger.warning(f"  - AZURE_DEPLOYMENT_NAME: {self.deployment_name}")
            logger.warning(f"  - AZURE_API_VERSION: {self.api_version}")
            self.client = None

        self._debug_log_enabled = os.getenv(
            "AVIS_CRITIQUES_DEBUG_LOG", "0"
        ).lower() in (
            "1",
            "true",
        )

    async def generate_summary_phase1(
        self, transcription: str, episode_date: str
    ) -> str:
        """
        Phase 1: Génère summary depuis transcription.

        Args:
            transcription: Texte complet de la transcription
            episode_date: Date de l'épisode au format YYYY-MM-DD

        Returns:
            Markdown string avec structure 2 tableaux

        Raises:
            ValueError: Si format markdown invalide
            TimeoutError: Si timeout après retry
        """
        if not self.client:
            raise ValueError("Client Azure OpenAI non configuré")

        if not transcription or not transcription.strip():
            raise ValueError("Transcription vide")

        # Format date pour prompt (en français)
        try:
            date_obj = datetime.strptime(episode_date, "%Y-%m-%d")

            # Mapper les mois en français
            mois_fr = {
                1: "janvier",
                2: "février",
                3: "mars",
                4: "avril",
                5: "mai",
                6: "juin",
                7: "juillet",
                8: "août",
                9: "septembre",
                10: "octobre",
                11: "novembre",
                12: "décembre",
            }

            date_str = f" du {date_obj.day} {mois_fr[date_obj.month]} {date_obj.year}"
        except Exception:
            date_str = ""

        # Prompt EXACT du lmelp frontend
        prompt = self._get_phase1_prompt(transcription, date_str)

        # Retry logic
        max_retries = len(PHASE1_ATTEMPT_TEMPERATURES) - 1
        timeout = 120  # 2 minutes

        for attempt, temperature in enumerate(PHASE1_ATTEMPT_TEMPERATURES):
            try:
                if self._debug_log_enabled:
                    logger.info(
                        f"Phase 1 génération (tentative {attempt + 1}/{max_retries + 1})"
                    )

                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.chat.completions.create,
                        model=self.deployment_name,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=MAX_OUTPUT_TOKENS,
                        temperature=temperature,
                    ),
                    timeout=timeout,
                )

                summary = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason

                # Log raw output BEFORE validation (for diagnosis)
                if self._debug_log_enabled:
                    from pathlib import Path

                    # Créer répertoire de debug si nécessaire
                    debug_dir = Path("/tmp/avis_critiques_debug")
                    debug_dir.mkdir(exist_ok=True)

                    # Écrire le contenu dans un fichier
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    debug_file = debug_dir / f"phase1_raw_{timestamp}.md"
                    debug_file.write_text(summary, encoding="utf-8")

                    logger.info("=" * 80)
                    logger.info("📄 PHASE 1 - RAW LLM OUTPUT (BEFORE VALIDATION)")
                    logger.info(f"   Length: {len(summary)} chars")
                    logger.info(f"   Has header: {'## 1. LIVRES DISCUT' in summary}")
                    logger.info(f"   Has tables: {'|' in summary}")
                    logger.info(f"   📁 Fichier debug: {debug_file}")
                    logger.info("=" * 80)

                # Une réponse coupée reste souvent un markdown bien formé
                if finish_reason == "length":
                    diagnostic = self._describe_llm_output(summary)
                    logger.error(f"❌ PHASE 1 - RÉPONSE TRONQUÉE: {diagnostic}")
                    raise ValueError(
                        f"Réponse LLM tronquée: limite de {MAX_OUTPUT_TOKENS} tokens "
                        f"atteinte ({diagnostic}). Si l'échec persiste, vérifier la "
                        "transcription de l'épisode."
                    )

                # Validation format markdown
                validation = self._validate_markdown_format(summary)

                if not validation["valid"]:
                    error_details = "\n  - ".join(validation["errors"])
                    logger.error("❌ PHASE 1 - VALIDATION FAILED")
                    logger.error(f"  Erreurs: {len(validation['errors'])}")
                    for i, err in enumerate(validation["errors"], 1):
                        logger.error(f"    {i}. {err}")
                    logger.error(f"  Aperçu: {validation['summary_preview']}...")

                    raise ValueError(
                        f"Format markdown invalide:\n  - {error_details}\n\n"
                        f"Aperçu du contenu reçu:\n{validation['summary_preview']}..."
                    )

                if self._debug_log_enabled:
                    logger.info(
                        f"✅ Phase 1 réussie: {len(summary)} caractères générés"
                    )

                return summary  # type: ignore[no-any-return]

            except TimeoutError as e:
                if attempt < max_retries:
                    logger.warning(
                        f"Timeout Phase 1, retry {attempt + 1}/{max_retries}"
                    )
                    await asyncio.sleep(2)
                    continue
                logger.error("Timeout Phase 1 après retries")
                raise TimeoutError(f"Timeout génération Phase 1: {e}") from e

            except ValueError as e:
                if attempt < max_retries:
                    logger.warning(
                        f"Validation Phase 1 échouée, retry {attempt + 1}/{max_retries}: {e}"
                    )
                    await asyncio.sleep(2)
                    continue
                logger.error(f"Validation Phase 1 échouée après retries: {e}")
                raise

            except Exception as e:
                logger.error(f"Erreur Phase 1: {e}")
                raise

        # Fallback explicite pour satisfaire MyPy (jamais atteint en pratique)
        raise RuntimeError("generate_summary_phase1: échec après toutes les tentatives")

    def _get_phase1_prompt(self, transcription: str, date_str: str) -> str:
        """Retourne le prompt Phase 1 exact du lmelp frontend."""
        return f"""Tu es un expert en critique littéraire qui analyse la transcription de l'émission "Le Masque et la Plume" sur France Inter.

⚠️ STRUCTURE DE L'ÉMISSION (3 temps séquentiels, JAMAIS mélangés):

1. **COURRIER DES LECTEURS** (~5 min) - À IGNORER COMPLÈTEMENT
   L'animateur lit des réactions d'auditeurs sur des livres d'émissions PRÉCÉDENTES.
   CES LIVRES NE FONT PAS PARTIE DU PROGRAMME DE CETTE ÉMISSION.

2. **LIVRES AU PROGRAMME** (~30-40 min) - TABLEAU 1
   Introduits après le courrier avec des phrases comme "Et on commence avec...", "Pour commencer ce soir..."
   TOUS les livres de cette section sont discutés par PLUSIEURS critiques (3-5 critiques donnent leur avis).

3. **COUPS DE CŒUR** (~10 min, en fin d'émission) - TABLEAU 2
   Chaque critique recommande UN livre personnel. UN SEUL critique s'exprime par livre.

⚠️ IMPORTANT: Ces 3 sections se suivent TOUJOURS dans cet ordre. Il n'y a JAMAIS de mélange (pas de coup de cœur au milieu des livres au programme).

IMPORTANT: Cette émission porte TOUJOURS sur des livres (type "livres").
Il y a TOUJOURS au moins un livre discuté au programme principal.
EXIGENCE ABSOLUE: Tu DOIS retourner les deux tableaux markdown.
Si tu ne trouves pas de livres après le courrier, relis attentivement la transcription.

Voici la transcription:
{transcription}

CONSIGNE PRINCIPALE:
Identifie TOUS les livres discutés AU PROGRAMME DE CETTE ÉMISSION (pas ceux du courrier) et crée 2 tableaux détaillés et complets:

1. **LIVRES DU PROGRAMME PRINCIPAL**: Tous les livres qui font l'objet d'une discussion approfondie entre plusieurs critiques
2. **COUPS DE CŒUR PERSONNELS**: UNIQUEMENT les livres mentionnés rapidement par un critique comme recommandation personnelle (différents du programme principal)

⚠️ RÈGLE SIMPLE ET CLAIRE:
- Si un livre est discuté par PLUSIEURS critiques (discussion approfondie) → Tableau 1 (programme)
- Si un livre est recommandé rapidement par UN SEUL critique en fin d'émission → Tableau 2 (coup de cœur)

⚠️ ATTENTION - LIVRES TRAITÉS RAPIDEMENT:
Même si l'animateur dit "on va aller très vite" ou "en quelques minutes", si PLUSIEURS critiques donnent leur avis sur le livre, c'est un livre AU PROGRAMME (tableau 1).
Le manque de temps ne change PAS la nature du livre.

⚠️ PARCOURIR TOUTE LA TRANSCRIPTION:
Tu DOIS lire la transcription JUSQU'À LA FIN pour capturer tous les livres, y compris ceux traités en fin d'émission par manque de temps.

⚠️ CONSIGNE CRUCIALE: NE RETOURNE QUE LES DEUX TABLEAUX, SANS AUCUNE PHRASE D'EXPLICATION, SANS COMMENTAIRE, SANS PHRASE INTRODUCTIVE. COMMENCE DIRECTEMENT PAR "## 1. LIVRES DISCUTÉS AU PROGRAMME" et termine par le dernier tableau.

---

## 1. LIVRES DISCUTÉS AU PROGRAMME{date_str}

Format de tableau markdown OBLIGATOIRE avec HTML pour les couleurs:

{TABLE_FORMAT_RULE}

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| [Nom auteur] | [Titre livre] | [Éditeur] | **[Nom COMPLET critique 1]**: [avis détaillé]. Note: X <br>**[Nom COMPLET critique 2]**: [avis détaillé]. Note: X <br>**[Nom COMPLET critique 3]**: [avis détaillé]. Note: X | [Note colorée] | [Nombre] | [Noms si note ≥9] | [Noms si note=10] |

⚠️ IMPORTANT: CLASSE LES LIVRES PAR NOTE DÉCROISSANTE (meilleure note d'abord, pire note en dernier).

RÈGLES DE NOTATION STRICTES:
- Note 1-2: Livres détestés, "purges", "ennuyeux", "raté"
- Note 3-4: Livres décevants, "pas terrible", "problématique"
- Note 5-6: Livres moyens, "correct sans plus", "mitigé"
- Note 7-8: Bons livres, "plaisant", "réussi", "bien écrit"
- Note 9: Excellents livres, "formidable", "remarquable", "coup de cœur"
- Note 10: Chefs-d'œuvre, "génial", "exceptionnel", "chef-d'œuvre"

⚠️ FORMAT OBLIGATOIRE POUR LES NOTES INDIVIDUELLES:
Chaque avis de critique DOIT se terminer par "Note: X" (avec deux-points).
Exemples corrects:
- **Elisabeth Philippe**: Très belle découverte, original et poétique. Note: 9
- **Arnaud Viviant**: Impressionnant, trouvailles stylistiques. Note: 8
Exemples INCORRECTS (à éviter):
- **Patricia Martin**: Bien fichu, 7  ← MAUVAIS (pas de "Note:")
- **Michel Crépu**: Remarquable, note 8  ← MAUVAIS (minuscule, pas de deux-points)

COULEURS HTML OBLIGATOIRES pour la Note moyenne:
- 9.0-10.0: <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 8.0-8.9: <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 7.0-7.9: <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 6.0-6.9: <span style="background-color: #CDDC39; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 5.0-5.9: <span style="background-color: #FFEB3B; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 4.0-4.9: <span style="background-color: #FF9800; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 3.0-3.9: <span style="background-color: #FF5722; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>
- 1.0-2.9: <span style="background-color: #F44336; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">X.X</span>

INSTRUCTIONS DÉTAILLÉES POUR EXTRAIRE TOUS LES AVIS:
1. Identifie TOUS les critiques qui parlent de chaque livre: Jérôme Garcin, Elisabeth Philippe, Frédéric Beigbeder, Michel Crépu, Arnaud Viviant, Judith Perrignon, Xavier Leherpeur, Patricia Martin, Olivia de Lamberterie, Jean-Claude Raspiengeas, etc.
2. Pour chaque critique, capture son NOM COMPLET (Prénom + Nom)
3. Cite leurs avis EXACTS avec leurs mots-clés d'appréciation
4. Attribue une note individuelle basée sur leur vocabulaire (entre 1 et 10) AU FORMAT EXACT: "Note: X" (avec deux-points, ex: "Note: 8")
5. Calcule la moyenne arithmétique précise (ex: 7.3, 8.7)
6. Identifie les "coups de cœur" (critiques très enthousiastes, note ≥9)
7. **CLASSE OBLIGATOIREMENT PAR NOTE DÉCROISSANTE** (meilleure note d'abord)

⚠️ RÈGLE UN LIVRE = UNE LIGNE:
Chaque livre DOIT avoir sa propre ligne dans le tableau, même si un même auteur a plusieurs livres.
JAMAIS de regroupement de plusieurs livres sur une même ligne (ex: "Titre 1 & Titre 2" est INTERDIT).
Si un auteur a 2 livres discutés, crée 2 lignes séparées avec le même nom d'auteur.

⚠️ VÉRIFICATION FINALE OBLIGATOIRE:
Avant de terminer, RELIS la transcription et COMPTE tous les livres mentionnés en dehors du courrier.
Si tu trouves N livres dans la transcription, tu DOIS avoir N livres dans tes tableaux.

⚠️ RAPPEL: Ignore complètement les livres mentionnés dans le "courrier de la semaine" au début de l'émission.

---

## 2. COUPS DE CŒUR DES CRITIQUES{date_str}

⚠️ ATTENTION: Ce tableau contient UNIQUEMENT les livres recommandés par **UN SEUL critique** comme son choix personnel.
CRITÈRE ABSOLU: Si plusieurs critiques donnent leur avis sur un livre, il va dans le tableau 1 (programme), PAS ici.
Ce sont des ouvrages DIFFÉRENTS de ceux discutés au programme principal ci-dessus.

⚠️ RÈGLE DE NON-DUPLICATION ENTRE TABLEAUX:
Un livre qui apparaît déjà dans le Tableau 1 (programme) ne doit JAMAIS apparaître dans le Tableau 2 (coups de cœur).
Si un critique donne un livre du programme comme coup de cœur, son avis est DÉJÀ capturé dans le Tableau 1 — NE PAS le dupliquer ici.
Exemple: Si "Lettres à Véra" est discuté au programme (Tableau 1) → NE PAS le remettre en coup de cœur (Tableau 2), même si un critique le recommande.

INCLUT TOUS TYPES D'OUVRAGES : romans, essais, BD, guides, biographies, etc.

Format de tableau pour ces recommandations personnelles:

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| [Nom] | [Titre] | [Éditeur] | [Nom COMPLET critique] | [Note colorée] | [Raison du coup de cœur] |

⚠️ IMPORTANT:
- CLASSE LES COUPS DE CŒUR PAR NOTE DÉCROISSANTE AUSSI
- N'INCLUS QUE les livres mentionnés comme recommandations PERSONNELLES, PAS ceux du programme principal (AUCUN doublon avec le Tableau 1)
- CHERCHE SPÉCIALEMENT en fin de transcription les sections "coups de cœur", "conseils de lecture", "recommandations"

EXIGENCES QUALITÉ:
- Noms COMPLETS de TOUS les critiques (Prénom + Nom)
- Citations exactes des avis les plus marquants
- Éditeurs mentionnés quand disponibles
- Tableaux markdown parfaitement formatés
- Couleurs HTML correctement appliquées
- **CLASSEMENT OBLIGATOIRE PAR NOTE DÉCROISSANTE**
- Capture de TOUS les avis individuels (pas seulement Elisabeth Philippe)
- **RECHERCHE ACTIVE des coups de cœur en fin de transcription** : cherche "coups de cœur", "conseil de lecture", "je recommande", "mon choix"

⚠️ SPÉCIAL COUPS DE CŒUR: Les critiques mentionnent souvent leurs recommandations personnelles vers la fin de l'émission. SCRUTE ATTENTIVEMENT la fin de la transcription pour ne pas les manquer !

⚠️ FORMAT DE RÉPONSE: Retourne UNIQUEMENT les 2 tableaux markdown avec leurs titres. N'ajoute AUCUNE explication, phrase introductive, ou commentaire sur la méthode de génération. Commence directement par "## 1. LIVRES DISCUTÉS AU PROGRAMME" et termine par le dernier tableau.

RAPPEL FINAL:
- IGNORE les livres du courrier de la semaine
- NE RETOURNE AUCUN TEXTE EXPLICATIF AVANT OU APRÈS LES TABLEAUX
- AUCUNE PHRASE COMME "voici l'analyse" ou "en résumé"
- COMMENCE IMMÉDIATEMENT PAR LE PREMIER TITRE DE TABLEAU

Sois EXHAUSTIF et PRÉCIS. Capture TOUS les livres DU PROGRAMME, TOUS les critiques, et TOUS les avis individuels."""

    def _describe_llm_output(self, summary: str) -> str:
        """Décrit une sortie LLM rejetée: taille et plus longue suite d'espaces."""
        longest = max(
            re.finditer(r" +", summary), key=lambda m: len(m[0]), default=None
        )
        if longest is None:
            return f"{len(summary)} caractères, aucune suite d'espaces"
        line = summary.count("\n", 0, longest.start()) + 1
        return (
            f"{len(summary)} caractères, plus longue suite d'espaces: "
            f"{len(longest[0])} en ligne {line}"
        )

    def _validate_markdown_format(self, summary: str) -> dict[str, Any]:
        """
        Valide le format markdown avec diagnostic détaillé.

        Returns:
            Dict avec:
            - valid (bool): True si valide
            - errors (list[str]): Liste des problèmes détectés
            - summary_preview (str): Premiers 200 caractères
        """
        errors = []

        # Check 1: Section principale manquante
        if not re.search(r"## 1\. LIVRES DISCUT", summary):
            errors.append(
                "Section principale manquante: '## 1. LIVRES DISCUTÉS AU PROGRAMME' "
                "non trouvée"
            )

        # Check 2: Tableaux markdown absents
        if "|" not in summary:
            errors.append("Aucun tableau markdown détecté (pipe '|' absent)")

        # Check 3: Contenu trop court
        if len(summary) < 200:
            errors.append(
                f"Contenu trop court: {len(summary)} caractères (minimum: 200)"
            )

        # Check 4: Détection message "no books" incorrect
        if "Aucun livre discuté" in summary:
            errors.append(
                "ERREUR: Message 'Aucun livre discuté' détecté - "
                "prompt incorrect (tous les épisodes ont des livres)"
            )

        # Check 5: Espaces consécutifs anormaux (bug LLM fréquent)
        if re.search(r" {10000,}", summary):
            errors.append(
                f"Espaces consécutifs anormaux détectés (bug LLM) - "
                f"taille totale: {len(summary)} caractères"
            )

        # Check 6: Contenu trop long (hallucination LLM)
        if len(summary) > 50000:
            errors.append(
                f"Contenu anormalement long: {len(summary)} caractères (maximum: 50000)"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "summary_preview": summary[:200] if summary else "(vide)",
        }

    async def enhance_summary_phase2(
        self,
        summary_phase1: str,
        episode_metadata: dict[str, Any],
        page_content: str = "",
    ) -> str:
        """
        Phase 2: Corrige noms avec contenu complet page RadioFrance.

        Args:
            summary_phase1: Summary généré en Phase 1
            episode_metadata: Métadonnées RadioFrance
                {animateur, critiques, date, image_url}
            page_content: Contenu HTML complet de la page RadioFrance (optionnel)

        Returns:
            Summary corrigé (fallback Phase 1 si erreur)
        """
        if not self.client:
            logger.warning("Client Azure OpenAI non configuré, skip Phase 2")
            return summary_phase1

        if not episode_metadata or not episode_metadata.get("critiques"):
            logger.info("Métadonnées insuffisantes, skip Phase 2")
            return summary_phase1

        try:
            prompt = self._get_phase2_prompt(
                summary_phase1, episode_metadata, page_content
            )

            if self._debug_log_enabled:
                logger.info("Phase 2 correction démarrée")

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.deployment_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Tu es un correcteur orthographique pour émission littéraire.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=MAX_OUTPUT_TOKENS,
                    temperature=0.1,
                ),
                timeout=60,  # 1 minute
            )

            summary_phase2 = response.choices[0].message.content

            if response.choices[0].finish_reason == "length":
                diagnostic = self._describe_llm_output(summary_phase2)
                logger.warning(f"⚠️  Phase 2 tronquée, retour à Phase 1: {diagnostic}")
                return summary_phase1

            # Validation: structure préservée
            validation = self._validate_markdown_format(summary_phase2)

            if not validation["valid"]:
                logger.warning("⚠️  Phase 2 a cassé le format, retour à Phase 1")
                logger.warning(f"  Problèmes: {', '.join(validation['errors'])}")
                return summary_phase1

            if self._debug_log_enabled:
                logger.info(f"✅ Phase 2 réussie: {len(summary_phase2)} caractères")
                # Log extrait Phase 2 pour debug (premiers 500 chars)
                logger.info(f"📄 PHASE 2 OUTPUT (extrait):\n{summary_phase2[:500]}...")

            return summary_phase2  # type: ignore[no-any-return]

        except Exception as e:
            logger.warning(f"Erreur Phase 2, fallback Phase 1: {e}")
            return summary_phase1

    def _get_phase2_prompt(
        self, summary_phase1: str, metadata: dict[str, Any], page_content: str = ""
    ) -> str:
        """Retourne le prompt Phase 2 avec contenu complet page RadioFrance."""
        animateur = metadata.get("animateur", "")
        critiques = metadata.get("critiques", [])
        date = metadata.get("date", "")

        critiques_list = ", ".join(critiques) if critiques else "non disponibles"

        # Si page_content disponible, l'inclure dans le prompt
        if page_content and len(page_content.strip()) > 0:
            page_section = f"""
Page RadioFrance complète (contenu textuel):
{page_content[:3000]}...
"""
        else:
            page_section = ""

        return f"""Résumé initial (à corriger):
{summary_phase1}

Métadonnées officielles RadioFrance:
- Animateur: {animateur}
- Critiques présents: {critiques_list}
- Date: {date}

voici le contenu de la page RadioFrance
===== DEBUT DE LA PAGE RADIOFRANCE =====
{page_section}
===== FIN DE LA PAGE RADIOFRANCE =====

CONSIGNE DE CORRECTION:
Corrige UNIQUEMENT les noms propres (auteurs, critiques, animateur, éditeurs, titres de livres) en utilisant les informations ci-dessus.

⚠️ IMPORTANT - COMMENT UTILISER LA PAGE RADIOFRANCE:
1. Pour les LIVRES DU PROGRAMME PRINCIPAL: Cherche dans la page les sections qui commencent par des guillemets et titres de livres (ex: "« Encre sympathique », de Patrick Modiano")
2. Pour les COUPS DE CŒUR: Cherche vers la fin de la page la section "Les conseils de lecture des critiques" ou "Coups de cœur"
   - Cette section liste les recommandations personnelles avec le format: "Nom Critique: Titre, de Auteur (Éditeur)"
   - Exemple: "Patricia Martin : L'Œil du paon, de Lilia Hassaine (Gallimard)"
3. Utilise ces informations pour corriger les orthographes des noms d'auteurs et titres de livres

EXEMPLES DE CORRECTIONS À FAIRE:
- "Lilia à Seine" → "Lilia Hassaine" (si trouvé dans la page)
- "L'œil du pan" → "L'Œil du paon" (si trouvé dans la page)
- "Françoise Sagan" → vérifier l'orthographe exacte dans la page

PRÉSERVE EXACTEMENT:
- La structure markdown (titres, tableaux)
- Les avis des critiques et leurs notes
- L'ordre des livres
- Les couleurs HTML des notes

⚠️ FORMAT DE SORTIE OBLIGATOIRE:
Retourne UNIQUEMENT les 2 tableaux markdown:
1. "## 1. LIVRES DISCUTÉS AU PROGRAMME" (tableau complet avec tous les livres)
2. "## 2. COUPS DE CŒUR DES CRITIQUES" (tableau avec coups de cœur)

{TABLE_FORMAT_RULE}

N'AJOUTE AUCUN texte explicatif, aucune phrase introductive, aucun commentaire.
COMMENCE DIRECTEMENT PAR "## 1. LIVRES DISCUTÉS AU PROGRAMME" et termine par le dernier tableau."""

    async def generate_full_summary(
        self,
        transcription: str,
        episode_date: str,
        episode_page_url: str | None,
        episode_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrateur: Phase 1 + Fetch URL + Phase 2.

        Workflow:
        1. Lancer Phase 1 + Fetch URL EN PARALLÈLE avec asyncio.gather()
        2. Attendre que les 2 se terminent
        3. Lancer Phase 2 (correction avec métadonnées)
        4. Tracker corrections appliquées

        Args:
            transcription: Texte de transcription
            episode_date: Date de l'épisode (YYYY-MM-DD)
            episode_page_url: URL RadioFrance (peut être None si fetch en cours)
            episode_id: ID de l'épisode (pour re-fetch URL si nécessaire)

        Returns:
            {
                "summary": str,  # Final (Phase 2)
                "summary_phase1": str,  # Backup
                "metadata": dict,  # RadioFrance metadata
                "corrections_applied": list[dict],
                "warnings": list[str]
            }
        """
        import asyncio

        from .mongodb_service import mongodb_service
        from .radiofrance_service import radiofrance_service

        warnings = []

        # Si URL déjà présente, juste Phase 1
        if episode_page_url:
            logger.info("✅ URL RadioFrance déjà présente, fetch inutile")
            logger.info(f"   URL: {episode_page_url}")
            summary_phase1 = await self.generate_summary_phase1(
                transcription, episode_date
            )
        elif episode_id:
            # Lancer Phase 1 + Fetch URL EN PARALLÈLE
            logger.info("🔄 Lancement parallèle: Phase 1 + Fetch URL RadioFrance")

            async def fetch_episode_url():
                """Fetch URL RadioFrance et met à jour MongoDB."""
                logger.info("🔍 Démarrage fetch URL RadioFrance...")
                try:
                    episode = mongodb_service.get_episode_by_id(episode_id)
                    if not episode:
                        logger.warning(f"❌ Épisode {episode_id} non trouvé")
                        return None

                    titre = episode.get("titre")
                    date = episode.get("date")

                    if not titre or not date:
                        logger.warning(
                            f"⚠️ Titre ou date manquant pour épisode {episode_id}"
                        )
                        return None

                    # Rechercher l'URL via RadioFrance
                    url = await radiofrance_service.search_episode_page_url(titre, date)

                    if url:
                        logger.info(f"✅ URL RadioFrance trouvée: {url}")
                        # Mettre à jour MongoDB
                        from bson import ObjectId

                        mongodb_service.episodes_collection.update_one(
                            {"_id": ObjectId(episode_id)},
                            {"$set": {"episode_page_url": url}},
                        )
                        logger.info("💾 MongoDB mis à jour avec l'URL")
                    else:
                        logger.warning("❌ URL RadioFrance non trouvée")

                    return url

                except Exception as e:
                    logger.error(f"❌ Erreur fetch URL: {e}")
                    return None

            # Lancer les 2 tâches en parallèle avec asyncio.gather()
            summary_phase1, fetched_url = await asyncio.gather(
                self.generate_summary_phase1(transcription, episode_date),
                fetch_episode_url(),
            )

            logger.info("✅ Phase 1 et Fetch URL terminés")

            if fetched_url:
                episode_page_url = fetched_url
            else:
                logger.warning(
                    "⚠️ Fetch URL n'a pas retourné d'URL, Phase 2 sera skippée"
                )
        else:
            # Ni URL ni episode_id
            logger.warning("⚠️ Pas d'URL et pas d'episode_id, Phase 2 sera skippée")
            summary_phase1 = await self.generate_summary_phase1(
                transcription, episode_date
            )

        # Extraction métadonnées (après que fetch URL soit terminé si applicable)
        page_content = ""
        if episode_page_url:
            logger.info(f"🔍 Extraction métadonnées depuis: {episode_page_url}")
            metadata = await radiofrance_service.extract_episode_metadata(
                episode_page_url
            )
            if metadata:
                logger.info(
                    f"✅ Métadonnées extraites: animateur={metadata.get('animateur')}, "
                    f"critiques={len(metadata.get('critiques', []))} critiques"
                )
                # Extraire le contenu textuel de la page pour Phase 2
                page_content = metadata.get("page_text", "")
                if page_content:
                    logger.info(
                        f"📄 Contenu page RadioFrance: {len(page_content)} caractères"
                    )
            else:
                logger.warning("⚠️ Aucune métadonnée extraite de l'URL")
        else:
            metadata = {}
            warnings.append("Pas d'URL RadioFrance, Phase 2 skippée")
            logger.info("⏭️ Phase 2 skippée (pas d'URL RadioFrance)")

        # Phase 2
        logger.info(
            "🔄 Démarrage Phase 2 (correction avec métadonnées + contenu page)..."
        )
        summary_phase2 = await self.enhance_summary_phase2(
            summary_phase1, metadata, page_content
        )
        logger.info("✅ Phase 2 terminée")

        # Detect corrections (simple diff)
        corrections_applied = self._detect_corrections(summary_phase1, summary_phase2)

        if corrections_applied:
            logger.info(
                f"📝 {len(corrections_applied)} correction(s) détectée(s) entre Phase 1 et Phase 2"
            )
        else:
            logger.info("ℹ️ Aucune correction détectée entre Phase 1 et Phase 2")

        # Log comparaison Phase 1 vs Phase 2 pour debug
        if self._debug_log_enabled:
            logger.info("=" * 80)
            logger.info("🔍 COMPARAISON PHASE 1 vs PHASE 2:")
            logger.info("📄 summary_phase1 (brut) - CONTENU COMPLET:")
            logger.info(summary_phase1)
            logger.info("-" * 80)
            logger.info("📄 summary (phase2, corrigé) - CONTENU COMPLET:")
            logger.info(summary_phase2)
            logger.info("=" * 80)

        return {
            "summary": summary_phase2,
            "summary_phase1": summary_phase1,
            "metadata": metadata,
            "corrections_applied": corrections_applied,
            "warnings": warnings,
        }

    def _detect_corrections(
        self, summary_phase1: str, summary_phase2: str
    ) -> list[dict[str, str]]:
        """Détecte les corrections appliquées (diff simple)."""
        # Simple diff: comparer lignes par lignes
        corrections = []

        lines1 = summary_phase1.split("\n")
        lines2 = summary_phase2.split("\n")

        for i, (line1, line2) in enumerate(zip(lines1, lines2)):
            if line1 != line2:
                # Extraire les différences de noms (simple heuristique)
                words1 = set(line1.split())
                words2 = set(line2.split())

                removed = words1 - words2
                added = words2 - words1

                if removed and added:
                    corrections.append(
                        {
                            "field": f"ligne {i + 1}",
                            "before": " ".join(removed)[:50],
                            "after": " ".join(added)[:50],
                        }
                    )

        return corrections[:10]  # Limiter à 10 corrections affichées


# Singleton instance
avis_critiques_generation_service = AvisCritiquesGenerationService()

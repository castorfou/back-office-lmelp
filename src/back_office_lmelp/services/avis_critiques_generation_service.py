"""Service de génération d'avis critiques en 2 phases LLM."""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any

import openai


logger = logging.getLogger(__name__)


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
        max_retries = 1
        timeout = 120  # 2 minutes

        for attempt in range(max_retries + 1):
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
                        max_tokens=8000,
                        temperature=0.1,
                    ),
                    timeout=timeout,
                )

                summary = response.choices[0].message.content

                # Validation format markdown
                if not self._is_valid_markdown_format(summary):
                    raise ValueError(
                        "Format markdown invalide: structure attendue non trouvée"
                    )

                if self._debug_log_enabled:
                    logger.info(f"Phase 1 réussie: {len(summary)} caractères générés")
                    # Log extrait Phase 1 pour debug (premiers 500 chars)
                    logger.info(f"📄 PHASE 1 OUTPUT (extrait):\n{summary[:500]}...")

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

            except Exception as e:
                logger.error(f"Erreur Phase 1: {e}")
                raise

        # Fallback explicite pour satisfaire MyPy (jamais atteint en pratique)
        raise RuntimeError("generate_summary_phase1: échec après toutes les tentatives")

    def _get_phase1_prompt(self, transcription: str, date_str: str) -> str:
        """Retourne le prompt Phase 1 exact du lmelp frontend."""
        return f"""Tu es un expert en critique littéraire qui analyse la transcription de l'émission "Le Masque et la Plume" sur France Inter.

⚠️ ATTENTION IMPORTANTE:
L'émission commence souvent par une section "courrier de la semaine" où l'animateur lit des réactions d'auditeurs sur des livres d'émissions PRÉCÉDENTES.
CES LIVRES DU COURRIER NE FONT PAS PARTIE DU PROGRAMME DE CETTE ÉMISSION.
Tu dois IGNORER complètement cette section du courrier.

Les livres du programme principal sont introduits APRÈS le courrier, généralement après des phrases comme:
- "Et on commence avec..."
- "Pour commencer ce soir..."
- "Parlons maintenant de..."
- "Le premier livre de ce soir..."

IMPORTANT: Si après avoir ignoré le courrier de la semaine, cette transcription ne contient PAS de discussions sur des livres, réponds simplement:
"Aucun livre discuté dans cet épisode. Cette émission semble porter sur d'autres sujets (cinéma, théâtre, musique)."

Voici la transcription:
{transcription}

CONSIGNE PRINCIPALE:
Identifie TOUS les livres discutés AU PROGRAMME DE CETTE ÉMISSION (pas ceux du courrier) et crée 2 tableaux détaillés et complets:

1. **LIVRES DU PROGRAMME PRINCIPAL**: Tous les livres qui font l'objet d'une discussion approfondie entre plusieurs critiques
2. **COUPS DE CŒUR PERSONNELS**: UNIQUEMENT les livres mentionnés rapidement par un critique comme recommandation personnelle (différents du programme principal)

⚠️ CONSIGNE CRUCIALE: NE RETOURNE QUE LES DEUX TABLEAUX, SANS AUCUNE PHRASE D'EXPLICATION, SANS COMMENTAIRE, SANS PHRASE INTRODUCTIVE. COMMENCE DIRECTEMENT PAR "## 1. LIVRES DISCUTÉS AU PROGRAMME" et termine par le dernier tableau.

---

## 1. LIVRES DISCUTÉS AU PROGRAMME{date_str}

Format de tableau markdown OBLIGATOIRE avec HTML pour les couleurs:

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| [Nom auteur] | [Titre livre] | [Éditeur] | **[Nom COMPLET critique 1]**: [avis détaillé et note] <br>**[Nom COMPLET critique 2]**: [avis détaillé et note] <br>**[Nom COMPLET critique 3]**: [avis détaillé et note] | [Note colorée] | [Nombre] | [Noms si note ≥9] | [Noms si note=10] |

⚠️ IMPORTANT: CLASSE LES LIVRES PAR NOTE DÉCROISSANTE (meilleure note d'abord, pire note en dernier).

RÈGLES DE NOTATION STRICTES:
- Note 1-2: Livres détestés, "purges", "ennuyeux", "raté"
- Note 3-4: Livres décevants, "pas terrible", "problématique"
- Note 5-6: Livres moyens, "correct sans plus", "mitigé"
- Note 7-8: Bons livres, "plaisant", "réussi", "bien écrit"
- Note 9: Excellents livres, "formidable", "remarquable", "coup de cœur"
- Note 10: Chefs-d'œuvre, "génial", "exceptionnel", "chef-d'œuvre"

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
1. Identifie TOUS les critiques qui parlent de chaque livre: Jérôme Garcin, Elisabeth Philippe, Frédéric Beigbeder, Michel Crépu, Arnaud Viviant, Judith Perrignon, Xavier Leherpeur, Patricia Martin, etc.
2. Pour chaque critique, capture son NOM COMPLET (Prénom + Nom)
3. Cite leurs avis EXACTS avec leurs mots-clés d'appréciation
4. Attribue une note individuelle basée sur leur vocabulaire (entre 1 et 10)
5. Calcule la moyenne arithmétique précise (ex: 7.3, 8.7)
6. Identifie les "coups de cœur" (critiques très enthousiastes, note ≥9)
7. **CLASSE OBLIGATOIREMENT PAR NOTE DÉCROISSANTE** (meilleure note d'abord)

⚠️ RAPPEL: Ignore complètement les livres mentionnés dans le "courrier de la semaine" au début de l'émission.

---

## 2. COUPS DE CŒUR DES CRITIQUES{date_str}

⚠️ ATTENTION: Ce tableau contient UNIQUEMENT les livres/ouvrages mentionnés rapidement par les critiques comme recommandations personnelles supplémentaires (souvent en fin d'émission avec "mon coup de cœur", "je recommande", etc.).
Ce sont des ouvrages DIFFÉRENTS de ceux discutés au programme principal ci-dessus.
INCLUT TOUS TYPES D'OUVRAGES : romans, essais, BD, guides, biographies, etc.

Format de tableau pour ces recommandations personnelles:

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| [Nom] | [Titre] | [Éditeur] | [Nom COMPLET critique] | [Note colorée] | [Raison du coup de cœur] |

⚠️ IMPORTANT:
- CLASSE LES COUPS DE CŒUR PAR NOTE DÉCROISSANTE AUSSI
- N'INCLUS QUE les livres mentionnés comme recommandations PERSONNELLES, PAS ceux du programme principal
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

    def _is_valid_markdown_format(self, summary: str) -> bool:
        """Valide le format markdown du summary."""
        # Vérifier présence des titres de section (accepter variantes accentuées)
        if not re.search(r"## 1\. LIVRES DISCUT", summary):
            return False

        # Vérifier présence de tableaux markdown
        if "|" not in summary:
            return False

        # Longueur minimale
        return len(summary) >= 200

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
                    max_tokens=8000,
                    temperature=0.1,
                ),
                timeout=60,  # 1 minute
            )

            summary_phase2 = response.choices[0].message.content

            # Validation: structure préservée
            if not self._is_valid_markdown_format(summary_phase2):
                logger.warning(
                    "Phase 2 a cassé la structure markdown, fallback Phase 1"
                )
                return summary_phase1

            if self._debug_log_enabled:
                logger.info(f"Phase 2 réussie: {len(summary_phase2)} caractères")
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
            logger.info("🔍 COMPARAISON PHASE 1 vs PHASE 2 (premiers 500 chars):")
            logger.info("📄 summary_phase1 (brut):")
            logger.info(summary_phase1[:500] + "...")
            logger.info("-" * 80)
            logger.info("📄 summary (phase2, corrigé):")
            logger.info(summary_phase2[:500] + "...")
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

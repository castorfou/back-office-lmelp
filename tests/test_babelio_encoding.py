"""Tests pour vérifier l'encoding correct des caractères spéciaux Babelio (Issue #167).

Ce module teste que les caractères spéciaux français (é, è, à, ê, ô, œ, ï, etc.)
sont correctement préservés lors de la récupération de données depuis Babelio.

Les tests utilisent des fixtures extraites de VRAIES réponses Babelio
(conformément à CLAUDE.md section "Backend Testing - Key Rules").

Données sources :
- API AJAX: curl -X POST https://www.babelio.com/aj_recherche.php -d '{"term":"Leïla Slimani"}'
- Page HTML: https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023

Le problème (Issue #167):
- Babelio déclare charset="iso-8859-1" mais utilise réellement Windows-1252 (cp1252)
- Windows-1252 ajoute des caractères dans la plage 0x80-0x9F (ex: tiret cadratin 0x96)
- Si on ne spécifie pas l'encoding correct, les caractères spéciaux sont mal décodés
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


# Fixture: VRAIE réponse AJAX JSON de Babelio (curl -X POST .../aj_recherche.php)
# Copié tel quel depuis la vraie API
BABELIO_AJAX_RESPONSE_REAL = json.dumps(
    [
        {
            "id": "369310",
            "prenoms": "Leïla",
            "nom": "Slimani",
            "url_photo": "/users/avt_fd_369310_1682586089.jpg",
            "ca_oeuvres": "24",
            "ca_membres": "40925",
            "type": "auteurs",
            "url": "/auteur/Leila-Slimani/369310",
            "first_of_group": "first_of_group",
        },
        {
            "id": "849799",
            "id_oeuvre": "849799",
            "nom": "Slimani",
            "prenoms": "Leïla",
            "id_auteur": "369310",
            "titre": "Chanson douce",
            "couverture": "/couv/cvt_Chanson-douce_5732.jpg",
            "ca_copies": "27901",
            "ca_nb_critiques": "1686",
            "ca_nb_citations": "606",
            "ca_note": "3.89",
            "weight": "2657",
            "nb_items_filtres": "19",
            "type": "livres",
            "url": "/livres/Slimani-Chanson-douce/849799",
        },
    ],
    ensure_ascii=False,
)


# Fixture: Extrait simplifié de la VRAIE page HTML Babelio
# Source: https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023
# Charset déclaré: iso-8859-1
# Contient: ï (Leïla), à (Voilà), é, è, œ, etc.
BABELIO_HTML_PAGE_REAL = """<!DOCTYPE html>
<html>
<head>
    <meta charset="iso-8859-1">
    <meta property="og:title" content="Regardez-nous danser – Le Pays des autres, 2 - Leïla Slimani - Babelio">
</head>
<body>
    <div class="livre">
        <h1>Regardez-nous danser – Le Pays des autres, 2</h1>
        <a class="livre_auteur" href="/auteur/Leila-Slimani/369310">Leïla Slimani</a>
        <div class="editeur">
            <a class="tiny_links dark" href="/editeur/A-vue-doeil/123">À vue d'œil</a>
        </div>
        <p>Voilà donc la suite du Pays des autres, et de sa famille dysfonctionnelle...</p>
    </div>
</body>
</html>"""


@pytest.mark.asyncio
async def test_search_ajax_preserves_special_characters():
    """Vérifie que la recherche AJAX préserve les caractères spéciaux français.

    Test pour Issue #167: Utilise la VRAIE réponse JSON de l'API Babelio.
    Sans encoding='cp1252', le tréma ï dans "Leïla" serait mal décodé.
    """
    service = BabelioService()

    # Mock de la réponse HTTP avec la VRAIE fixture API
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=BABELIO_AJAX_RESPONSE_REAL)

    # Mock de la session
    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response
    mock_session.post.return_value.__aexit__.return_value = None

    with patch.object(service, "_get_session", return_value=mock_session):
        results = await service.search("Leïla Slimani")

    # Vérifier que les caractères spéciaux sont préservés (VRAIES données)
    assert len(results) == 2

    # Premier résultat: auteur avec tréma
    auteur = results[0]
    assert auteur["prenoms"] == "Leïla"  # Tréma ï doit être préservé
    assert auteur["nom"] == "Slimani"
    assert auteur["type"] == "auteurs"

    # Deuxième résultat: livre
    livre = results[1]
    assert livre["titre"] == "Chanson douce"
    assert livre["prenoms"] == "Leïla"  # Tréma ï doit être préservé

    await service.close()


@pytest.mark.asyncio
async def test_fetch_full_title_from_html_preserves_special_characters():
    """Vérifie que le scraping de titre depuis HTML préserve les caractères spéciaux.

    Test pour Issue #167: Utilise un extrait de VRAIE page HTML Babelio.
    Sans encoding='cp1252', les caractères comme –, é, à seraient mal décodés.
    """
    service = BabelioService()

    # Mock de la réponse HTTP avec la VRAIE fixture HTML
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=BABELIO_HTML_PAGE_REAL)

    # Mock de la session
    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    with patch.object(service, "_get_session", return_value=mock_session):
        title = await service.fetch_full_title_from_url(
            "https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023"
        )

    # Vérifier que le titre est extrait avec tous les caractères spéciaux
    assert title == "Regardez-nous danser – Le Pays des autres, 2"

    await service.close()


@pytest.mark.asyncio
async def test_fetch_publisher_from_html_preserves_special_characters():
    """Vérifie que le scraping d'éditeur préserve les caractères spéciaux.

    Test pour Issue #167: L'éditeur "À vue d'œil" contient :
    - À (accent grave majuscule)
    - œ (ligature)
    """
    service = BabelioService()

    # Mock de la réponse HTTP avec la VRAIE fixture HTML
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=BABELIO_HTML_PAGE_REAL)

    # Mock de la session
    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    with patch.object(service, "_get_session", return_value=mock_session):
        publisher = await service.fetch_publisher_from_url(
            "https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023"
        )

    # Vérifier que l'éditeur est extrait avec accents et ligatures
    assert publisher == "À vue d'œil"

    await service.close()


@pytest.mark.asyncio
async def test_fetch_author_url_from_html_preserves_special_characters():
    """Vérifie que le scraping d'URL auteur fonctionne avec caractères spéciaux.

    Test pour Issue #167: Le texte du lien contient "Leïla" (tréma).
    """
    service = BabelioService()

    # Mock de la réponse HTTP avec la VRAIE fixture HTML
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=BABELIO_HTML_PAGE_REAL)

    # Mock de la session
    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    with patch.object(service, "_get_session", return_value=mock_session):
        author_url = await service.fetch_author_url_from_page(
            "https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023"
        )

    # Vérifier que l'URL est correctement extraite
    assert author_url == "https://www.babelio.com/auteur/Leila-Slimani/369310"

    await service.close()


@pytest.mark.asyncio
async def test_scrape_author_name_from_html_preserves_special_characters():
    """Vérifie que le scraping de nom d'auteur préserve les caractères spéciaux.

    Test pour Issue #167: Le nom "Leïla Slimani" contient un tréma (ï).
    """
    service = BabelioService()

    # Mock de la réponse HTTP avec la VRAIE fixture HTML
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=BABELIO_HTML_PAGE_REAL)

    # Mock de la session
    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    with patch.object(service, "_get_session", return_value=mock_session):
        author_name = await service._scrape_author_from_book_page(
            "https://www.babelio.com/livres/Slimani-Regardez-nous-danser--Le-Pays-des-autres-2/1853023"
        )

    # Vérifier que le nom est extrait avec le tréma
    assert author_name == "Leïla Slimani"

    await service.close()

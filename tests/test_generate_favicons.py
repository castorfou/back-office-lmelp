"""Tests du générateur d'icônes de la PWA lmelp (Issue #315).

Une icône « maskable » doit remplir tout le cercle du launcher Android :
fond plein bord à bord (aucun pixel transparent) et motif contenu dans la
safe zone, le disque central de 80 % du côté.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "generate_favicons.py"
PUBLIC_DIR = ROOT / "frontend" / "public"

_spec = importlib.util.spec_from_file_location("generate_favicons", SCRIPT)
assert _spec is not None and _spec.loader is not None
generate_favicons = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generate_favicons)

# Écart maximal toléré (par canal) avec la couleur de fond hors safe zone
_BACKGROUND_TOLERANCE = 8


def _assert_is_maskable(icon: Image.Image, size: int) -> None:
    rgba = np.asarray(icon.convert("RGBA")).astype(np.int32)
    assert icon.size == (size, size)

    # Fond plein bord à bord : aucun coin transparent ni arrondi
    assert rgba[..., 3].min() == 255, "l'icône maskable contient de la transparence"

    # Hors du disque de 80 % : uniquement la couleur de fond
    ys, xs = np.mgrid[0:size, 0:size]
    center = (size - 1) / 2
    outside = np.hypot(xs - center, ys - center) > 0.4 * size
    background = np.array(generate_favicons.BACKGROUND_COLOR)
    deviation = np.abs(rgba[..., :3] - background).max(axis=2)
    assert deviation[outside].max() <= _BACKGROUND_TOLERANCE, (
        "le motif déborde de la safe zone (disque central de 80 %)"
    )

    # Le motif (masque + plume) est bien présent au centre
    inside = np.hypot(xs - center, ys - center) <= 0.4 * size
    assert (deviation[inside] > 60).mean() > 0.15, "motif absent de l'icône"


def _database_ratio(icon: Image.Image) -> float:
    """Part des pixels carmin de la base de données (marque du back-office)."""
    rgba = np.asarray(icon.convert("RGBA")).astype(np.int32)
    r, g, b = rgba[..., 0], rgba[..., 1], rgba[..., 2]
    crimson = (r > 130) & (g < 70) & (b > 40) & (b < 120) & (rgba[..., 3] > 0)
    return float(crimson.mean())


@pytest.mark.parametrize(
    "filename", ["maskable-icon-512x512.png", "android-chrome-512x512.png"]
)
def test_icons_keep_back_office_database(filename):
    """La base de données de l'ancienne icône rose reste dans le motif."""
    assert _database_ratio(Image.open(PUBLIC_DIR / filename)) > 0.03


def test_build_maskable_icon_keeps_back_office_database():
    assert _database_ratio(generate_favicons.build_maskable_icon(512)) > 0.03


@pytest.mark.parametrize("size", [192, 512])
def test_build_maskable_icon_fills_launcher_circle(size):
    """L'icône générée est pleine et son motif tient dans la safe zone."""
    _assert_is_maskable(generate_favicons.build_maskable_icon(size), size)


@pytest.mark.parametrize("size", [192, 512])
def test_committed_maskable_icons_are_maskable(size):
    """Les PNG maskable servis par la PWA respectent les mêmes contraintes."""
    path = PUBLIC_DIR / f"maskable-icon-{size}x{size}.png"
    assert path.exists(), f"{path.name} absent de frontend/public"
    _assert_is_maskable(Image.open(path), size)

#!/usr/bin/env python3
"""Génère les icônes de la PWA lmelp : masque, plume et base de données sur fond vert.

Sources (``frontend/public/gimp_favicon/``, même composition, 1327×1328) :

- ``favicon.png`` : icône verte historique de lmelp (masque + plume, ombre
  portée vert foncé) ;
- ``favicon_back-office-lmelp.png`` : même icône sur fond rose, avec une base
  de données carmin derrière la plume. Seule la base de données en est
  reprise : elle marque le rôle de back-office de l'application.

Fichiers produits dans ``frontend/public/`` :

- icônes « any » (carré vert arrondi avec ombre portée) :
  favicon-16x16/32x32/48x48, favicon.ico, apple-touch-icon (180),
  android-chrome-192x192/512x512 ;
- icônes « maskable » (192 et 512) : fond vert plein bord à bord, motif
  détouré et recentré dans la safe zone (disque central de 80 % du côté),
  pour que l'icône remplisse tout le cercle du launcher Android.

Le détourage reprend celui de ``scripts/generate_launcher_icon.py`` du repo
castorfou/lmelp-mobile, qui part de la même source.

Usage :
    python scripts/generate_favicons.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import ConvexHull


PUBLIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public"
SOURCE_IMAGE = PUBLIC_DIR / "gimp_favicon" / "favicon.png"
DATABASE_SOURCE_IMAGE = PUBLIC_DIR / "gimp_favicon" / "favicon_back-office-lmelp.png"

# Vert uni du fond de l'icône historique lmelp
BACKGROUND_COLOR = (0x0F, 0xAE, 0x63)

# Rayon du disque contenant le motif, en fraction du côté : la safe zone
# maskable est un disque de rayon 0,4 ; on garde une petite marge.
_MOTIF_RADIUS = 0.38
_WORK_SIZE = 1024

# Pixels « verts » (fond + ombre) : G dépasse max(R, B)
_GREEN_OPAQUE_BELOW = 5
_GREEN_TRANSPARENT_ABOVE = 35
_PEEL_ITERATIONS = 25
# Base de données de l'icône rose : carmin et bandes violet foncé ont un vert
# très faible, contrairement au fond rose et à son ombre (G > 75)
_DATABASE_GREEN_MAX = 60
# Liseré rose/magenta (R et B nettement au-dessus de G), pelé depuis les bords
_MAGENTA_MARGIN = 10

ANY_SIZES = {
    "favicon-16x16.png": 16,
    "favicon-32x32.png": 32,
    "favicon-48x48.png": 48,
    "apple-touch-icon.png": 180,
    "android-chrome-192x192.png": 192,
    "android-chrome-512x512.png": 512,
}
MASKABLE_SIZES = (192, 512)
ICO_SIZES = [(16, 16), (32, 32), (48, 48)]


def extract_foreground(img: Image.Image) -> Image.Image:
    """Détoure le masque et la plume : les pixels verts deviennent transparents.

    L'alpha décroît progressivement avec la « verdeur » (G - max(R, B)) pour
    garder des bords anti-aliasés. Seul le plus grand ensemble connexe
    (masque + plume) est conservé, ce qui élimine l'ombre vert foncé.
    """
    rgba = np.asarray(img.convert("RGBA")).astype(np.int32)
    r, g, b, a = rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3]
    greenness = g - np.maximum(r, b)

    span = _GREEN_TRANSPARENT_ABOVE - _GREEN_OPAQUE_BELOW
    keep = np.clip((_GREEN_TRANSPARENT_ABOVE - greenness) / span, 0.0, 1.0)
    alpha = (a * keep).round().astype(np.int32)

    # Pelage : les pixels teintés (vert résiduel d'un flou, liseré rose) qui
    # touchent la transparence sont retirés de proche en proche. Les yeux et
    # la bouche, enclos dans le masque jaune, sont épargnés.
    magenta = np.minimum(r, b) - g > _MAGENTA_MARGIN
    tinted = (greenness > 0) | magenta
    for _ in range(_PEEL_ITERATIONS):
        touching = ndimage.binary_dilation(alpha == 0) & (alpha > 0) & tinted
        if not touching.any():
            break
        alpha[touching] = 0

    labels, count = ndimage.label(alpha > 0)
    if count > 1:
        sizes = ndimage.sum_labels(
            np.ones_like(labels), labels, index=range(1, count + 1)
        )
        alpha[labels != int(np.argmax(sizes)) + 1] = 0

    out = rgba.copy()
    out[..., 1] = np.where(greenness > 0, np.maximum(r, b), g)
    out[..., 3] = alpha
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def extract_database(img: Image.Image) -> Image.Image:
    """Détoure la base de données de l'icône rose (reste transparent).

    Elle est le plus grand ensemble connexe de pixels à vert faible, élargi à
    son enveloppe convexe pour boucher les encoches laissées par l'ombre de
    la plume. Sa partie cachée par la plume reste absente, la plume étant
    recollée par-dessus.
    """
    rgba = np.asarray(img.convert("RGBA")).astype(np.int32)
    candidates = (rgba[..., 3] > 0) & (rgba[..., 1] < _DATABASE_GREEN_MAX)
    labels, count = ndimage.label(candidates)
    sizes = ndimage.sum_labels(np.ones_like(labels), labels, index=range(1, count + 1))
    ys, xs = np.nonzero(labels == int(np.argmax(sizes)) + 1)
    points = np.column_stack([xs, ys])
    hull = points[ConvexHull(points).vertices]
    shape = Image.new("L", img.size, 0)
    ImageDraw.Draw(shape).polygon([tuple(p) for p in hull.tolist()], fill=255)
    database = np.asarray(shape) > 0

    out = rgba.copy()
    out[..., 3] = np.where(database, 255, 0)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def build_motif() -> Image.Image:
    """Base de données, puis masque et plume par-dessus (repère des sources)."""
    database = extract_database(Image.open(DATABASE_SOURCE_IMAGE))
    mask_and_feather = extract_foreground(Image.open(SOURCE_IMAGE))
    motif = np.asarray(Image.alpha_composite(database, mask_and_feather)).copy()

    # L'encoche de la plume forme une poche transparente entre la plume et la
    # base de données : on la comble avec la couleur de la base la plus proche.
    opaque = motif[..., 3] > 127
    holes = ndimage.binary_fill_holes(opaque) & ~opaque
    if holes.any():
        db_alpha = np.asarray(database)[..., 3] > 0
        _, (iy, ix) = ndimage.distance_transform_edt(~db_alpha, return_indices=True)
        motif[holes, :3] = np.asarray(database)[iy[holes], ix[holes], :3]
        motif[holes, 3] = 255
    return Image.fromarray(motif, "RGBA")


def build_any_icon() -> Image.Image:
    """Icône « any » : carré arrondi vert uni de la source, motif par-dessus.

    L'ombre portée d'origine n'est pas reprise : sa silhouette ne correspond
    pas à celle de la base de données.
    """
    source = np.asarray(Image.open(SOURCE_IMAGE).convert("RGBA"))
    flat = np.zeros_like(source)
    flat[..., :3] = BACKGROUND_COLOR
    flat[..., 3] = source[..., 3]
    return Image.alpha_composite(Image.fromarray(flat, "RGBA"), build_motif())


def build_maskable_icon(size: int) -> Image.Image:
    """Icône maskable : fond vert plein, motif centré dans la safe zone."""
    motif = build_motif()
    alpha = np.asarray(motif)[..., 3]
    ys, xs = np.nonzero(alpha)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    radius = float(np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2).max())

    work = _WORK_SIZE
    scale = work * _MOTIF_RADIUS / radius
    scaled = motif.resize(
        (round(motif.width * scale), round(motif.height * scale)),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (work, work), BACKGROUND_COLOR + (255,))
    canvas.alpha_composite(
        scaled, (round(work / 2 - cx * scale), round(work / 2 - cy * scale))
    )
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def generate_favicons(output_dir: Path = PUBLIC_DIR) -> None:
    """Génère toutes les icônes de la PWA dans ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    img = build_any_icon()

    for filename, size in ANY_SIZES.items():
        img.resize((size, size), Image.Resampling.LANCZOS).save(
            output_dir / filename, "PNG", optimize=True
        )
        print(f"Créé : {filename} ({size}x{size})")

    ico_images = [img.resize(s, Image.Resampling.LANCZOS) for s in ICO_SIZES]
    ico_images[0].save(
        output_dir / "favicon.ico",
        format="ICO",
        sizes=ICO_SIZES,
        append_images=ico_images[1:],
    )
    print("Créé : favicon.ico (multi-tailles)")

    for size in MASKABLE_SIZES:
        filename = f"maskable-icon-{size}x{size}.png"
        build_maskable_icon(size).save(output_dir / filename, "PNG", optimize=True)
        print(f"Créé : {filename} (maskable)")


if __name__ == "__main__":
    generate_favicons()

"""
Utilitaire de préparation du dataset pour les notebooks de collaborative filtering.

Usage dans un notebook Jupyter :
    %run dataset_avis.py

Variables disponibles après exécution :
    df          : DataFrame (critique_oid, livre_oid, note, critique_nom, livre_titre)
    df_train    : DataFrame train (80%)
    df_test     : DataFrame test (20%)
    critique_names : dict {critique_oid -> nom}
    livre_titles   : dict {livre_oid -> titre}
    n_critiques, n_livres, n_avis : statistiques
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pymongo import MongoClient
from sklearn.model_selection import GroupShuffleSplit


# ── 1. Connexion MongoDB ────────────────────────────────────────────────────

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/masque_et_la_plume")
client = MongoClient(MONGODB_URL)
db = client.get_default_database()

print(f"✅ Connecté à MongoDB : {MONGODB_URL}")

# ── 2. Extraction de la collection avis ─────────────────────────────────────

avis_raw = list(
    db.avis.find(
        {},
        {
            "critique_oid": 1,
            "livre_oid": 1,
            "note": 1,
            "critique_nom_extrait": 1,
            "livre_titre_extrait": 1,
        },
    )
)

df_masque = pd.DataFrame(avis_raw)
df_masque = df_masque.rename(
    columns={
        "critique_nom_extrait": "critique_nom",
        "livre_titre_extrait": "livre_titre",
    }
)
df_masque = df_masque[
    ["critique_oid", "livre_oid", "note", "critique_nom", "livre_titre"]
].copy()

# Filtrer les notes manquantes ou hors échelle 1-10
df_masque = df_masque.dropna(subset=["note", "critique_oid", "livre_oid"])
df_masque = df_masque[df_masque["note"].between(1, 10)]

print(f"📊 Masque & la Plume : {len(df_masque)} avis")

# ── 3. Injection des notes Calibre (utilisateur comme 30ème critique) ────────

CALIBRE_USER_OID = "calibre_user"
CALIBRE_USER_NOM = "Moi (Calibre)"
df_calibre = pd.DataFrame()  # vide si Calibre indisponible

try:
    # Ajouter le chemin src au sys.path pour importer les services
    src_path = os.path.join(os.path.dirname(os.path.abspath(".")), "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # Ajouter depuis /workspaces si dans notebooks/
    workspace_src = "/workspaces/back-office-lmelp/src"
    if workspace_src not in sys.path:
        sys.path.insert(0, workspace_src)

    from back_office_lmelp.services.calibre_matching_service import (
        CalibreMatchingService,
    )
    from back_office_lmelp.services.calibre_service import CalibreService
    from back_office_lmelp.services.mongodb_service import MongoDBService

    calibre_svc = CalibreService()
    if calibre_svc.is_available():
        mongodb_svc = MongoDBService()
        matching_svc = CalibreMatchingService(calibre_svc, mongodb_svc)

        # Récupérer l'index Calibre (titre normalisé → livre Calibre)
        calibre_index = matching_svc.get_calibre_index()

        # Récupérer tous les livres MongoDB pour le mapping titre → livre_oid
        livres_mongo = list(db.livres.find({}, {"_id": 1, "titre": 1}))

        from back_office_lmelp.utils.text_utils import normalize_for_matching

        mongo_index = {
            normalize_for_matching(livre["titre"]): str(livre["_id"])
            for livre in livres_mongo
            if livre.get("titre")
        }

        # Construire les avis Calibre
        calibre_rows = []
        for norm_titre, calibre_book in calibre_index.items():
            rating = calibre_book.get("rating")
            if not rating or rating == 0:
                continue  # pas de note
            # Calibre stocke 0-10 par pas de 2 (2=1★, 4=2★, ..., 10=5★)
            # Convertir en scale 1-10 : rating × 1 (déjà en base 10, juste exclure 0)
            # 2→2, 4→4, 6→6, 8→8, 10→10 — cohérent avec la scale Masque
            note_calibre = int(rating)

            # Trouver le livre_oid MongoDB correspondant
            livre_oid = mongo_index.get(norm_titre)
            if not livre_oid:
                continue

            titre = calibre_book.get("title", norm_titre)
            calibre_rows.append(
                {
                    "critique_oid": CALIBRE_USER_OID,
                    "livre_oid": livre_oid,
                    "note": note_calibre,
                    "critique_nom": CALIBRE_USER_NOM,
                    "livre_titre": titre,
                }
            )

        df_calibre = pd.DataFrame(calibre_rows)
        print(f"📚 Calibre : {len(df_calibre)} livres notés par l'utilisateur")
    else:
        print("⚠️  Calibre non disponible (base introuvable) — utilisateur ignoré")

except ImportError as e:
    print(f"⚠️  Import services impossible : {e} — Calibre ignoré")
except Exception as e:
    print(f"⚠️  Erreur Calibre : {e} — Calibre ignoré")

# ── 4. Fusion des deux sources ───────────────────────────────────────────────

df = (
    pd.concat([df_masque, df_calibre], ignore_index=True)
    if len(df_calibre) > 0
    else df_masque.copy()
)
df["note"] = df["note"].astype(float)

# ── 5. Statistiques et indices ───────────────────────────────────────────────

n_avis = len(df)
n_critiques = df["critique_oid"].nunique()
n_livres = df["livre_oid"].nunique()
sparsity = 1 - (n_avis / (n_critiques * n_livres))

# Dictionnaires de lookup
critique_names = dict(
    df.drop_duplicates("critique_oid").set_index("critique_oid")["critique_nom"]
)
livre_titles = dict(
    df.drop_duplicates("livre_oid").set_index("livre_oid")["livre_titre"]
)

print("\n📈 Dataset final :")
print(f"   • {n_avis} avis")
print(f"   • {n_critiques} critiques")
print(f"   • {n_livres} livres")
print(f"   • Remplissage : {(1 - sparsity) * 100:.1f}% ({sparsity * 100:.1f}% creux)")

# ── 6. Train / Test split (80/20 stratifié par critique) ────────────────────

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(df, groups=df["critique_oid"]))
df_train = df.iloc[train_idx].reset_index(drop=True)
df_test = df.iloc[test_idx].reset_index(drop=True)

print("\n✂️  Split train/test :")
print(f"   • Train : {len(df_train)} avis ({len(df_train) / n_avis * 100:.0f}%)")
print(f"   • Test  : {len(df_test)} avis ({len(df_test) / n_avis * 100:.0f}%)")

# ── 7. Visualisation distribution des notes ──────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(14, 4))

# Distribution des notes
note_counts = df["note"].value_counts().sort_index()
axes[0].bar(note_counts.index, note_counts.values, color="steelblue", edgecolor="white")
axes[0].set_xlabel("Note (1-10)")
axes[0].set_ylabel("Nombre d'avis")
axes[0].set_title("Distribution des notes")
axes[0].set_xticks(range(1, 11))

# Nombre d'avis par critique (top 15)
avis_par_critique = (
    df.groupby("critique_nom").size().sort_values(ascending=False).head(15)
)
axes[1].barh(
    avis_par_critique.index[::-1], avis_par_critique.to_numpy()[::-1], color="coral"
)
axes[1].set_xlabel("Nombre d'avis")
axes[1].set_title("Top 15 critiques par volume d'avis")

plt.tight_layout()
plt.show()

print(
    "\n✅ Dataset prêt — variables disponibles : df, df_train, df_test, critique_names, livre_titles"
)

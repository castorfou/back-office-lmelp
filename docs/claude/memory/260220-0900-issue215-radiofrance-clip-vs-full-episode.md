# Issue #215 - Bug: lien RadioFrance retourne un clip au lieu de l'émission complète

## Contexte

RadioFrance crée deux types d'URLs pour une même émission :
1. **Émission complète** (~47 min) : `le-masque-et-la-plume-du-dimanche-15-fevrier-2026-8246986`
2. **Clip livre** (~9 min) : `aqua-de-gaspard-koenig-3030201`

Pour l'épisode du 13/02/2026, le système retournait le clip "Aqua de Gaspard Kœnig" au lieu de l'émission complète.

## Analyse des vraies données RadioFrance

**Découverte critique** : Les pages RadioFrance n'ont PAS `timeRequired` dans le JSON-LD. La durée est dans `mainEntity.duration`.

Structure JSON-LD réelle (RadioEpisode) :
```json
{
  "@type": "RadioEpisode",
  "dateCreated": "2026-02-15T09:12:30.000Z",
  "mainEntity": {
    "@type": "AudioObject",
    "duration": "P0Y0M0DT0H47M40S"
  }
}
```

**Autre découverte** : L'émission complète a `dateCreated=2026-02-15` alors que l'épisode en DB a `date=2026-02-13` (diff=2 jours). Le clip lui a `dateCreated=2026-02-13` (correspond exactement à la DB).

## Racine du bug

Le filtre par date exacte acceptait le clip (même date) et rejetait l'émission complète (date diff=2j).

## Solution implémentée

### Critère de match double
**durée >= min_duration_seconds ET |date_page - date_épisode| ≤ 7 jours**

- Clip (13/02, 596s) → rejeté : 596s < 1430s ✓
- Émission complète (15/02, 2860s) → acceptée : 2860s ≥ 1430s ET diff=2j ≤ 7j ✓
- Émission autre semaine (18/01, 2800s) → rejetée : diff=26j > 7j ✓

### Fichiers modifiés

`src/back_office_lmelp/services/radiofrance_service.py` :
- `_parse_iso_duration()` : ajout support format `P0Y0M0DT0H47M40S` (format réel RadioFrance) en plus de `PT47M25S`
- `_extract_episode_date_and_duration()` : lit `dateCreated` + `mainEntity.duration` (pas `timeRequired`)
- `search_episode_page_url()` : filtre date ±7 jours + durée minimale (au lieu de date exacte seule)
- Import `timedelta` supprimé (pas nécessaire, `.days` suffit)

`src/back_office_lmelp/app.py` :
- `fetch_episode_page_url` : passe `min_duration_seconds = episode_duree // 2` au service

`tests/test_radiofrance_service.py` :
- Classe `TestRadioFranceDurationFilter` avec 9 tests (dont `test_parse_iso_duration_full_format_from_radiofrance`)
- Fixtures HTML mises à jour avec vraie structure RadioFrance

`tests/fixtures/radiofrance/` :
- `episode_2026_02_13_clip_aqua.html` : JSON-LD avec `mainEntity.duration=P0Y0M0DT0H9M56S`
- `episode_2026_02_13_full_episode.html` : JSON-LD avec `mainEntity.duration=P0Y0M0DT0H47M40S`, `dateCreated=2026-02-15`
- `search_2026_02_13_with_clip_and_full.html` : page de résultats avec les 2 URLs

## Leçons apprises

1. **Toujours inspecter les vraies données** avant d'implémenter (voir données réelles vs assumptions)
2. **RadioFrance JSON-LD** : durée dans `mainEntity.duration`, pas `timeRequired`
3. **RadioFrance publie les émissions 1-2 jours après diffusion** : fenêtre de tolérance nécessaire
4. **Ne pas ignorer la date complètement** : une fenêtre ±7j filtre les autres semaines
5. **Format ISO 8601 complet** : `P0Y0M0DT0H47M40S` ≠ `PT47M25S` (même sens, format différent)
6. **Les résultats de recherche RadioFrance** incluent des clips ET d'autres émissions — la combinaison durée+date est essentielle

## Comportement gracieux

Si `min_duration_seconds=None` (épisode sans durée en DB) : filtre par date ±7j seulement, comportement inchangé vs avant.

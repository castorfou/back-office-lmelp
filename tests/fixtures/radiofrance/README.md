# RadioFrance Fixtures

This directory contains real HTML captures from RadioFrance website for testing purposes.

## Files

### search_with_results.html
- **Captured**: 2025-11-07
- **URL**: `https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume?search=CRITIQUE+I+Anne+Berest%2C+Laura+Vazquez%2C+C%C3%A9dric+Sapin-Defour%2C+Javier+Cercas%2C+Paul+Gasnier%2C+que+lire+cette+semaine+%3F`
- **Description**: Real RadioFrance search page with results
- **Contains**:
  - JSON-LD Schema.org ItemList with 10 episode results
  - HTML links to episodes
  - First result: "le-masque-et-la-plume-du-dimanche-26-octobre-2025-7900946"

### search_no_results.html
- **Captured**: 2025-11-07
- **URL**: `https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume?search=Episode+inexistant+XYZ123`
- **Description**: Real RadioFrance search page with no results
- **Contains**:
  - JSON-LD Schema.org structures (but no episode results)
  - No episode links in HTML

## Why Real Fixtures?

Following the lesson from Issue #85: **NEVER invent mock structures**.

These fixtures were captured from real RadioFrance responses to ensure:
- Tests validate against actual API behavior
- Changes in RadioFrance HTML structure are detected
- No false positives from invented mock data

## Updating Fixtures

If RadioFrance changes their HTML structure, re-capture fixtures:

```bash
# Capture with results
curl -s "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume?search=CRITIQUE+I+Anne+Berest%2C+Laura+Vazquez%2C+C%C3%A9dric+Sapin-Defour%2C+Javier+Cercas%2C+Paul+Gasnier%2C+que+lire+cette+semaine+%3F" \
  -H "User-Agent: Mozilla/5.0" \
  > tests/fixtures/radiofrance/search_with_results.html

# Capture no results
curl -s "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume?search=Episode+inexistant+XYZ123" \
  -H "User-Agent: Mozilla/5.0" \
  > tests/fixtures/radiofrance/search_no_results.html
```

## Related

- Service: [src/back_office_lmelp/services/radiofrance_service.py](../../../src/back_office_lmelp/services/radiofrance_service.py)
- Tests: [tests/test_radiofrance_service.py](../../test_radiofrance_service.py)
- Issue: #89 - Add link to RadioFrance episode page

# Fix Episode Dropdown Titles - Issue #29

**Date**: 2025-09-06 05:20
**Context**: Complete TDD implementation to fix episode title display in dropdown selection list
**Issue**: [#29 - Corriger les titres dans la liste déroulante de selection des episodes](https://github.com/castorfou/back-office-lmelp/issues/29)
**PR**: [#32 - Fix: Améliore l'affichage des titres dans la liste déroulante d'épisodes](https://github.com/castorfou/back-office-lmelp/pull/32)

## Problem Summary

The episode dropdown selection list had multiple issues:
- Date format: numeric `24/08/2025` instead of literary French `24 août 2025`
- Wrong titles: showed original titles instead of corrected titles (`titre_corrige`)
- Type display: unwanted `[livres]` tags appeared in dropdown
- No dynamic updates: dropdown didn't refresh when titles were modified

## Root Causes Discovered

Through user testing and debugging, I identified 3 distinct problems:

### 1. Frontend Display Format (EpisodeSelector.vue)
- Method `formatEpisodeOption()` used wrong format and fields
- Missing French date formatting with `toLocaleDateString('fr-FR')`
- No dynamic refresh mechanism for title updates

### 2. Backend API Data (Episode Model)
- `Episode.to_summary_dict()` method missing `titre_corrige` field
- Frontend received incomplete data structure
- This caused fallback to original titles even when corrections existed

### 3. MongoDB Service Projection (Critical Issue)
- `mongodb_service.get_all_episodes()` projection was incomplete
- Missing `"titre_corrige": 1` in MongoDB `find()` projection
- **Root cause**: Database had corrected titles but service didn't retrieve them
- API returned `"titre_corrige": null` for all episodes despite database containing values

## TDD Implementation Journey

### Phase 1: Initial Frontend Implementation
```javascript
// EpisodeSelector.vue - New formatting logic
formatEpisodeOption(episode) {
  const date = episode.date ? this.formatDateLitteraire(episode.date) : 'Date inconnue';
  const titre = episode.titre_corrige || episode.titre;
  return `${date} - ${titre}`;
}

formatDateLitteraire(dateStr) {
  const date = new Date(dateStr);
  const options = {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  };
  return date.toLocaleDateString('fr-FR', options);
}
```

### Phase 2: Event-Driven Architecture
```javascript
// EpisodeEditor.vue - Title update events
this.$emit('title-updated', {
  episodeId: this.episode.id,
  newTitle: this.correctedTitle
});

// HomePage.vue - Event handling
async onTitleUpdated(data) {
  if (this.$refs.episodeSelector) {
    await this.$refs.episodeSelector.refreshEpisodesList();
  }
}
```

### Phase 3: Backend API Fix
```python
# Episode model - Include titre_corrige in summary
def to_summary_dict(self) -> dict[str, Any]:
    return {
        "id": self.id,
        "titre": self.titre,
        "titre_corrige": self.titre_corrige,  # CRITICAL ADDITION
        "date": self.date.isoformat() if self.date else None,
        "type": self.type,
    }
```

### Phase 4: MongoDB Service Fix (TDD Critical Fix)
```python
# FAILING TEST FIRST (Red Phase)
def test_get_all_episodes_includes_titre_corrige_field(self, mongodb_service):
    # Test expects projection to include titre_corrige
    mongodb_service.episodes_collection.find.assert_called_once_with(
        {}, {"titre": 1, "titre_corrige": 1, "date": 1, "type": 1, "_id": 1}
    )

# IMPLEMENTATION (Green Phase)
episodes = list(
    self.episodes_collection.find(
        {}, {"titre": 1, "titre_corrige": 1, "date": 1, "type": 1, "_id": 1}
    ).sort("date", -1)
)
```

## User Testing Debug Process

**User Issue**: "la liste deroulante ne semble pas utiliser les titres corriges mais les titres d'origine"

**Debug Steps**:
1. Verified frontend code was correct (`episode.titre_corrige || episode.titre`)
2. Checked API response: `curl http://localhost:54326/api/episodes | head -20`
3. **Discovery**: All episodes returned `"titre_corrige": null` despite database having values
4. **Root cause**: MongoDB projection in `get_all_episodes()` was missing the field
5. **User provided database entry** showing `titre_corrige` existed in MongoDB
6. **TDD Fix**: Wrote failing test, then fixed projection

## Technical Architecture

### Frontend Components
- **EpisodeSelector.vue**: Main dropdown component with formatting logic
- **EpisodeEditor.vue**: Title editing component with event emission
- **HomePage.vue**: Parent component orchestrating updates

### Backend Components
- **Episode Model**: Data serialization with `to_dict()` and `to_summary_dict()`
- **MongoDB Service**: Database queries with proper field projections
- **FastAPI Routes**: API endpoints serving formatted data

### Event Flow
```
1. User modifies title in EpisodeEditor
2. EpisodeEditor.saveTitle() saves via API
3. Emits 'title-updated' event → HomePage
4. HomePage.onTitleUpdated() calls refreshEpisodesList() → EpisodeSelector
5. EpisodeSelector reloads data with updated titles
6. User sees immediate change in dropdown
```

## Test Coverage Achieved

**Total: 166 tests passing**
- **Backend**: 118 tests (including new TDD regression test)
- **Frontend**: 48 tests (updated for new formatting)

### Key Tests Added
- `test_episode_to_summary_dict_with_titre_corrige()` - Backend API response
- `test_get_all_episodes_includes_titre_corrige_field()` - MongoDB projection
- Frontend tests for new date formatting and event handling

## Final Result

**Before**: `"24/08/2025 [livres] - Episode automatiquement transcrit par IA..."`
**After**: `"24 août 2025 - Les nouveaux livre de Simon Chevrier, Sylvain Tesson, Gaël Octavia..."`

## Files Modified

### Frontend (Vue.js)
- `frontend/src/components/EpisodeSelector.vue` - Display formatting + dynamic refresh
- `frontend/src/components/EpisodeEditor.vue` - Event emission on title save
- `frontend/src/views/HomePage.vue` - Event handling and component coordination
- `frontend/tests/unit/EpisodeSelector.test.js` - Updated test suite
- `frontend/tests/integration/HomePage.test.js` - New integration tests

### Backend (FastAPI/Python)
- `src/back_office_lmelp/models/episode.py` - Include titre_corrige in to_summary_dict()
- `src/back_office_lmelp/services/mongodb_service.py` - Add titre_corrige to projection
- `tests/test_models_validation.py` - Updated tests for new field
- `tests/test_mongodb_service_simple.py` - New TDD regression test

### Documentation
- `docs/dev/episode-title-display-improvement.md` - Complete implementation guide
- `docs/commands.md` - Updated command reference

## Key Learnings

1. **User Testing is Critical**: The real issue was only discovered through user feedback
2. **API Response Debugging**: Always verify actual API responses, not just code logic
3. **MongoDB Projections**: Field projections must match frontend expectations
4. **TDD for Complex Issues**: Writing failing tests first helped catch the root cause
5. **Full Stack Debugging**: Issues can span multiple layers (frontend, API, database)

## Commands for Future Reference

### Testing
```bash
# Backend tests
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v

# Frontend tests
cd /workspaces/back-office-lmelp/frontend && npm test -- --run

# API debugging
curl -s http://localhost:54321/api/episodes | head -20
```

### Development
```bash
# Start unified dev environment
./scripts/start-dev.sh

# Branch management
gh issue develop 29
git checkout feature-branch-name
```

This implementation successfully resolved issue #29 with a comprehensive TDD approach, addressing frontend display, backend API, and database service layers.

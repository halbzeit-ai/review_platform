# DeckViewer Visual Analysis Data Mapping Fix

**Date**: 2025-07-29  
**Issue**: DeckViewer not displaying visual analysis text for 4-digit project IDs  
**Root Cause**: Data mapping disconnect between legacy and new database systems  
**Status**: ✅ RESOLVED

## Problem Description

### User Report
- Fresh dojo decks were processed through all steps (visual analysis, extraction, template processing)
- Decks were added as projects via "add dojo companies" button
- DeckViewer showed slide images correctly but no visual analysis text
- Issue appeared to affect "4-digit project IDs" but root cause was different

### Initial Hypothesis (Incorrect)
- Assumed 4-digit deck IDs weren't getting visual analysis data
- Thought it was a processing pipeline issue

### Actual Root Cause
**Database System Mismatch**: The platform has two coexisting database systems:

1. **Legacy System**: `pitch_decks` table (used for dojo processing and visual analysis cache)
2. **New System**: `project_documents` table (used for gallery and project management)

The issue was in the **data mapping** between these systems in the DeckViewer backend.

## Technical Investigation

### Database Analysis
```sql
-- Found that "4-digit project IDs" don't exist as deck IDs
SELECT pd.id as deck_id FROM pitch_decks pd WHERE pd.id > 1000;
-- Result: No results (no 4-digit deck IDs exist)

-- Found actual current dojo projects (3-digit project IDs, 4-digit document IDs)
SELECT p.id, pd.id, pd.file_name FROM projects p 
JOIN project_documents pd ON p.id = pd.project_id 
WHERE p.company_id LIKE '%dojo%';
-- Result: Project IDs 347-356, Document IDs 5948-5957

-- Found visual analysis data exists in legacy system
SELECT pd.id, vac.pitch_deck_id FROM pitch_decks pd 
JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id 
WHERE pd.data_source = 'dojo';
-- Result: All dojo decks have visual analysis (pitch_deck_ids 58-198)
```

### Data Flow Mapping
```
User Action: Access /project/kianova/deck-viewer/5950

Frontend → Backend DeckViewer API
  ↓
get_deck_analysis(company_id="kianova", deck_id=5950)
  ↓
Query project_documents table: deck_id=5950 → filename="Kianava_Teaser.pdf"
  ↓
BEFORE FIX: Query visual_analysis_cache WHERE pitch_deck_id = 5950 → No results
AFTER FIX:  Find pitch_decks WHERE filename="Kianava_Teaser.pdf" → pitch_deck_id=198
           Query visual_analysis_cache WHERE pitch_deck_id = 198 → ✅ Data found
```

## Root Cause Analysis

### The Disconnect
1. **New project system** creates projects with `project_documents` entries (IDs 5948-5957)
2. **Dojo processing** stores visual analysis linked to `pitch_decks` entries (IDs 58-198)  
3. **DeckViewer backend** was only looking for direct ID matches instead of filename-based mapping

### Why This Happened
- The dojo processing system uses the legacy `pitch_decks` table for visual analysis caching
- The "add dojo companies" feature creates entries in the new `project_documents` system
- The DeckViewer was updated to handle both systems but lacked proper mapping logic

## Solution Implementation

### Backend Fix Location
**File**: `/home/ramin/halbzeit-ai/review_platform/backend/app/api/projects.py`  
**Function**: `get_deck_analysis()` - lines ~192-249

### Fix Logic
```python
# BEFORE: Direct ID lookup (broken for project_documents)
cache_query = text("""
    SELECT analysis_result_json, vision_model_used, created_at
    FROM visual_analysis_cache 
    WHERE pitch_deck_id = :deck_id  # This fails for project_documents
""")

# AFTER: Filename-based mapping for project_documents
if source_table == 'project_documents':
    # 1. Get filename from project_documents
    filename = get_filename_from_project_documents(deck_id)
    
    # 2. Find matching pitch_deck by filename
    pitch_deck_id = find_pitch_deck_by_filename(filename)
    
    # 3. Query visual_analysis_cache with correct pitch_deck_id
    cache_query = text("""
        SELECT analysis_result_json, vision_model_used, created_at
        FROM visual_analysis_cache 
        WHERE pitch_deck_id = :pitch_deck_id  # Now uses correct ID
    """)
```

### Code Changes
- Added filename-based lookup for `project_documents` entries
- Maintained backward compatibility for legacy `pitch_decks` entries
- Added proper error handling and logging
- Used database queries to map between the two systems

## Key Learnings

### 1. Database System Evolution
- **Legacy systems don't disappear immediately** - they coexist with new systems
- **Data mapping between systems** is critical and often breaks
- **Always trace data flow** from UI → Backend → Database when debugging

### 2. Investigation Methodology
- **Follow the data, not assumptions** - "4-digit IDs" was a red herring
- **Database queries reveal truth** - actual project/deck IDs were different than expected
- **System architecture understanding** is crucial for complex issues

### 3. Debugging Strategy
```
1. Reproduce issue → DeckViewer shows no text
2. Trace data flow → Frontend → Backend → Database  
3. Verify data existence → Visual analysis data EXISTS
4. Find the gap → ID mapping between systems
5. Implement mapping → Filename-based lookup
6. Test fix → ✅ Text displays correctly
```

### 4. Code Patterns for Dual Systems
```python
if source_table == 'new_system':
    # Map from new system ID to legacy system ID
    legacy_id = find_legacy_mapping(new_system_id)
    query_legacy_data(legacy_id)
else:
    # Direct lookup for legacy system
    query_legacy_data(legacy_id)
```

## Prevention Strategies

### 1. Data Migration Planning
- When introducing new database systems, plan data migration carefully
- Ensure all existing data access patterns still work
- Create proper mapping/bridging logic between systems

### 2. Testing Strategy
- Test data access after system changes
- Verify both new and legacy data paths work
- Test with real production data scenarios

### 3. Documentation
- Document system transitions and dual-system periods
- Map data relationships between old and new systems
- Keep architecture diagrams updated

## Related Files
- `/backend/app/api/projects.py` - DeckViewer backend (FIXED)
- `/frontend/src/pages/DeckViewer.js` - DeckViewer frontend
- Database tables: `pitch_decks`, `project_documents`, `visual_analysis_cache`, `projects`

## Future Considerations
- Consider migrating visual analysis cache to use project_documents IDs
- Plan eventual deprecation of pitch_decks table
- Ensure other parts of system handle dual-system architecture correctly

---

**Resolution**: Filename-based mapping successfully bridges legacy and new database systems, allowing DeckViewer to display visual analysis text for all dojo projects.
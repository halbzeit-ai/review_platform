# Dojo File Organization Improvement Proposal

## Current Issues

1. **Duplicate ZIP Upload Handling**: No detection of existing files, always creates new entries
2. **Inconsistent File Structure**: Two dojo locations (`/mnt/CPU-GPU/dojo/` and `/mnt/CPU-GPU/projects/dojo/`)

## Analysis of Current Structure

### Regular Projects
- Path: `/mnt/CPU-GPU/projects/{project-uuid}/`
- Structure:
  ```
  projects/
  ├── 27af88b2-0157-41dc-a064-278112af51fd/
  │   ├── analysis/     # AI analysis results
  │   ├── exports/      # Exported data
  │   └── uploads/      # Original files
  ```

### Current Dojo (Inconsistent)
- Path 1: `/mnt/CPU-GPU/dojo/` (backend saves here)
- Path 2: `/mnt/CPU-GPU/projects/dojo/` (exists but not used)

## Proposed Solution

### 1. Unified File Structure
Move dojo to follow project pattern:
```
projects/
├── dojo/
│   ├── analysis/     # AI analysis results for all dojo files
│   ├── exports/      # Extracted data exports
│   └── uploads/      # Original PDF files
```

### 2. Intelligent Duplicate Handling

#### Database Schema Addition
```sql
ALTER TABLE pitch_decks ADD COLUMN file_hash VARCHAR(64);
CREATE INDEX idx_pitch_decks_file_hash ON pitch_decks(file_hash);
```

#### Upload Process Enhancement
1. **Extract ZIP** to temporary directory
2. **Calculate file hashes** (SHA-256) for each PDF
3. **Check existing files** by comparing:
   - Original filename (`file_name`)
   - File hash (`file_hash`)
4. **Skip duplicates** and log them
5. **Add only new files** to database
6. **Return detailed report** of added/skipped files

#### Response Format
```json
{
  "success": true,
  "summary": {
    "total_files": 15,
    "new_files": 3,
    "duplicate_files": 12
  },
  "new_files": [
    "NewFile1.pdf",
    "NewFile2.pdf", 
    "UpdatedFile.pdf"
  ],
  "duplicates": [
    "ExistingFile1.pdf",
    "ExistingFile2.pdf"
  ]
}
```

## Implementation Plan

### Phase 1: Migration Script
```python
def migrate_dojo_to_projects():
    # 1. Create /mnt/CPU-GPU/projects/dojo/uploads/
    # 2. Move files from /mnt/CPU-GPU/dojo/* to new location
    # 3. Update pitch_decks.file_path in database
    # 4. Add file_hash column and populate it
```

### Phase 2: Enhanced Upload Logic
```python
def process_dojo_zip_enhanced(zip_file, uploaded_by, db):
    # 1. Extract to temp directory
    # 2. Calculate hashes for all PDFs
    # 3. Check for duplicates (by filename OR hash)
    # 4. Only process new files
    # 5. Return detailed report
```

### Phase 3: Frontend Updates
- Show duplicate handling results to user
- Allow user to force re-upload specific files if needed
- Display file count statistics

## Benefits

1. **Consistent Structure**: Dojo follows same pattern as regular projects
2. **No Duplicate Errors**: Intelligent detection prevents conflicts
3. **User Transparency**: Clear reporting of what happened
4. **Incremental Updates**: ZIP archives can grow over time
5. **Future-Proof**: Hash-based detection works even with renamed files

## Migration Impact

- **Existing Data**: All current files preserved
- **Database Changes**: Only addition of file_hash column
- **API Changes**: Enhanced response format (backward compatible)
- **Frontend Changes**: Improved user feedback
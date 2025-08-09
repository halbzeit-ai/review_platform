# API Data Mappings Reference

This document maps data field names between different layers of the application. **Critical for debugging data display issues.**

## Classification Data Mappings

### Storage → API → Frontend Flow

```
Database (extraction_experiments.classification_results_json)
├── classification_result.primary_sector
├── classification_result.confidence_score
├── classification_result.reasoning
├── classification_result.secondary_sector
└── classification_result.subcategory

Backend API Processing
├── /projects/extraction-results → maps to "classification"
├── /dojo/extraction-test/experiments/{id} → uses "primary_sector"
└── /internal/classify → returns full classification object

Frontend Components
├── StartupDashboard.js → expects "result.classification" (string)
├── DojoManagement.js → expects "result.primary_sector" (string)
└── ProjectDashboard.js → expects "result.classification" (string)
```

### Field Name Translations

| Database Field | API Endpoint | Frontend Field | Component |
|---|---|---|---|
| `classification_result.primary_sector` | `/projects/extraction-results` | `classification` | StartupDashboard |
| `classification_result.primary_sector` | `/dojo/experiments/{id}` | `primary_sector` | DojoManagement |
| `classification_result.confidence_score` | `/dojo/experiments/{id}` | `confidence_score` | DojoManagement |
| `classification_result.reasoning` | `/dojo/experiments/{id}` | `classification_reasoning` | DojoManagement |

## Company Data Mappings

### Company Name Extraction

```
Database: company_name_results_json
├── [].company_name_extraction → Frontend: company_name
├── pitch_decks.ai_extracted_startup_name → Frontend: company_name (fallback)
└── pitch_decks.file_name → Frontend: deck_name
```

### Company Offering Extraction

```
Database: results_json  
├── [].offering_extraction → Frontend: company_offering
├── [].deck_id → Frontend: deck_id
└── [].processing_status → Frontend: status
```

## Funding Data Mappings

```
Database: funding_amount_results_json
├── [].funding_amount_extraction → Frontend: funding_amount
├── [].confidence_score → Frontend: funding_confidence
└── [].reasoning → Frontend: funding_reasoning
```

## Date Data Mappings

```
Database: deck_date_results_json
├── [].deck_date_extraction → Frontend: deck_date  
├── [].confidence_score → Frontend: date_confidence
└── [].reasoning → Frontend: date_reasoning
```

## Visual Analysis Mappings

```
Database: visual_analysis_cache.analysis_result_json
├── visual_analysis_results[] → Frontend: visual_analysis
├── [].page_number → Frontend: page_number
├── [].content → Frontend: page_content
└── [].image_analysis → Frontend: image_description
```

## API Endpoint Data Contracts

### `/api/projects/extraction-results`
**Used by**: StartupDashboard.js
**Authentication**: Required (Bearer token)
**Returns**: Array of extraction results for user's decks

```typescript
interface ExtractionResult {
  deck_id: number;
  deck_name: string;           // from pitch_decks.file_name
  company_name?: string;       // from company_name_results_json
  company_offering?: string;   // from results_json
  classification?: string;     // from classification_results_json.primary_sector
  funding_amount?: string;     // from funding_amount_results_json
  deck_date?: string;         // from deck_date_results_json  
  extracted_at: string;       // from extraction_experiments.created_at
}
```

### `/api/dojo/extraction-test/experiments/{id}`
**Used by**: DojoManagement.js
**Authentication**: Required (GP role only)
**Returns**: Detailed experiment results with all extraction data

```typescript
interface ExperimentDetails {
  id: number;
  experiment_name: string;
  pitch_deck_ids: number[];
  results: Array<{
    deck_id: number;
    offering_extraction: string;
    primary_sector?: string;        // from classification_results_json
    confidence_score?: number;      // from classification_results_json  
    classification_reasoning?: string; // from classification_results_json
    secondary_sector?: string;      // from classification_results_json
    deck_info: {
      filename: string;
      company_name?: string;
      page_count?: number;
    }
  }>;
  classification_results: any[];
  company_name_results: any[];
  funding_amount_results: any[];
  deck_date_results: any[];
}
```

### `/api/internal/classify`
**Used by**: GPU processing, internal tools
**Authentication**: None (internal only)
**Returns**: Raw classification result

```typescript
interface ClassificationResult {
  primary_sector: string;
  subcategory: string;
  confidence_score: number;
  reasoning: string;
  secondary_sector: string;
  keywords_matched: string[];
  recommended_template?: number;
}
```

## Database Schema Mappings

### Key Tables and Relationships

```sql
-- Pitch decks (user uploads)
pitch_decks
├── id (referenced everywhere as deck_id)
├── file_name → Frontend: deck_name
├── ai_extracted_startup_name → Frontend: company_name (fallback)
├── company_id (links to user's company)
└── processing_status → Frontend: status

-- Extraction experiments (AI processing results) 
extraction_experiments
├── id (experiment identifier)
├── pitch_deck_ids (PostgreSQL array of deck IDs)
├── results_json (company offering extractions)
├── classification_results_json (sector classifications)
├── company_name_results_json (company name extractions)
├── funding_amount_results_json (funding extractions)
├── deck_date_results_json (date extractions)
└── created_at → Frontend: extracted_at

-- Visual analysis cache (PDF page analysis)
visual_analysis_cache  
├── pitch_deck_id (links to pitch_decks.id)
├── analysis_result_json (page-by-page analysis)
├── vision_model_used
└── created_at
```

## Common Field Name Issues

### 1. Classification Field Mismatches
**Problem**: Backend stores `primary_sector` but endpoint returns `classification`
**Solution**: Check API endpoint implementation for field mapping logic

### 2. Null vs Empty String Handling
**Problem**: Database has `null`, API returns `""`, frontend expects specific format
**Solution**: Check null handling in both backend processing and frontend display

### 3. Array vs Object Structure
**Problem**: Some endpoints return `{results: [...]}`, others return `[...]` directly
**Solution**: Check API endpoint documentation for exact structure

### 4. ID Type Mismatches
**Problem**: Database uses integers, some APIs expect strings
**Solution**: Ensure consistent type handling across all layers

## Debugging Field Mappings

### 1. Check Database Content
```bash
# View raw database content:
./scripts/debug-api.sh table extraction_experiments
./scripts/debug-api.sh deck DECK_ID
```

### 2. Test API Response
```bash
# Check what API actually returns:
curl -s "http://localhost:8000/api/projects/extraction-results" | jq '.[0]'
curl -s "http://localhost:8000/api/dojo/extraction-test/experiments/1" | jq '.results[0]'
```

### 3. Check Frontend Expectations
```bash
# Find field usage in component:
grep -n "fieldname\|\.field" frontend/src/pages/ComponentName.js
grep -A3 -B3 "field.*map\|field.*?" frontend/src/pages/ComponentName.js
```

### 4. Trace Data Flow
```bash
# Follow data from database to display:
echo "1. Database field name:"
./scripts/debug-api.sh table extraction_experiments | grep field_name

echo "2. API endpoint processing:"
grep -A10 -B5 "field_name" backend/app/api/endpoint.py

echo "3. Frontend usage:"
grep -n "field_name" frontend/src/pages/Component.js
```

## Field Mapping Checklist

When adding new data fields:

- [ ] Database schema includes the field
- [ ] Backend API processes and maps the field correctly  
- [ ] Frontend component expects the field with correct name/type
- [ ] Null/empty value handling is consistent across all layers
- [ ] Field is documented in this mapping reference
- [ ] Debug endpoints include the field for troubleshooting
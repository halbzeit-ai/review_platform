Idea behind the dojo part of the system:
the goal of the dojo processing is that a GP can view a processing result as if they are a startup 
and to see what the startup for this deck would experience. 
when changing a prompt or a model, the GP would see that the texts are shorter, have a different quality or the scoring changes.

the idea is that the GP is "impersonating" a startup and can use all of the ui and workflows that a startup has, 
not only the results viewer but really the whole project. 
in the future, we will have more document types than only pitchdecks, for example financial reports and research papers. 
so we need to be able to view all of these like a startup does.

- This part is intended for GPs to work on a large number of decks to improve prompts.
- for this, the GP can upload zip files and will then have a lot of pdf files. this is done in the "training data & management" tab of dojo
- step 1: next the GP can generate a random sub-sample of the PDF pool
- steps 2, 3 and 4 run on the GPU and it communicates with the CPU server via HTTP, the CPU has a postgresql database where all info about PDFs and results is stored-
- step 2: subsequent steps work on text only. step 2 turns the pdf into single images and interprets these images,  turning them into text descriptions per page.
- as step 2 takes quite a while, we have introduced caching so that the translation from images to text is stored in the database on the CPU.
- the user may clear the cache to do the visual analysis of step 2 again, maybe with a better and slower LLM
- step 2 should and must do exactly only this. get an image interpretation prompt and the selected model from the database and generate visual results to be stored in the database
- step 3 extracts via multiple prompts and possibly different LLM the following informations from the deck: the company's offering, the class, the name of the company, the funding amount and the date of the deck. these are obligatory and need to be extracted for every deck as they do not relate to the sub-vertical / class the startup is in.
- step 4 finally, gets a template (one that the user selected) from the database, this template consists roughly of a couple of chapters, each chapter has a couple questions and a corresponding scoring criterion.
- step 4 generates a results report that has the identical structure as the results.json that is generated when startups upload their deck via the web upload mechanism. this structure is stored in the database.
- finally, the user can look at the some key information of such an experimental run in the extraction experiment history: company name, number of pages in the deck, class, offering.
- here, the user can add these companies as fake companies to the startup database and look at these dojo companies through the eyes of a startup founder.
- the dojo companies can be accessed via the GP dashboard in the gallery, that shows the fist image of the deck, company name, funding sought and company offering, i.e. mostly information from step 3.
- clicking on "open project" of a dojo company will show the startup view on a project.
- here, the GP can click on the deck viewer that will view the visual analysis from step 2 together with the images extracted from the deck.
- the GP can also open the results viewer to see all results from step 4.
- finally, the GP can remove the experimental dojo companies again in the "training data & management" tab of dojo

here's another description from the discussion with claude code:
- dojo is built in a way that selecting a sample generates a new experiment. 
- when one or more processing steps are done, the user can to the experiments history tab, 
- there, he can select an exeriment leading him to the experiment results. 
- the experiment results are a modal that shows each company of the sample incl company name, class, funding sought and the offering. 
- this is very handy to understand whether the obligatory extractions work. 
- if the user likes the results of the experiment overview, he can click "add dojo companies" on the right lower side. 
- this function will add the companies of this experiment as projects to the gallery view. 
- thus, dojo is not automatically populating the gallery, the user is in control and will only do so when the table of experiment results is satisfactory. 
- in the GP dashboard, you see the piechart that shows the distribution of the companies in the project database. 
- there, the user can select whether to see dojo companies ("include test data", we should rename that to "include dojo companies"). 
- if this is done, the gallery view will show legit startups as well as dojo companies. 
- finally, when the user is done with this dojo sample and companies, he can remove all the dojo companies by going to the dojo ui, navigating to "training  data & management" and hitting "clean up dojo projects"
- this will remove the dojo companies from the project database. 

---

## DOJO REFACTORING & CLEANUP PLAN (Next Phase)

### 1. UNIFIED DOCUMENT PROCESSING ARCHITECTURE

**Goal**: Create single, consistent codebase for both Dojo batch processing and startup single-deck processing.

**Current Problems**:
- Duplicate processing logic between dojo and startup workflows
- Inconsistent API contracts (`deck_ids` vs `document_id`)
- Legacy naming confusion (`pitch_deck` → `document`)
- Different queue systems for batch vs single processing

**Unified Architecture**:
```
Core Processing Engine
├── Document Classification (on upload)
├── Type-Specific Processing Pipelines
│   ├── pitch_deck → HealthcarePitchDeckPipeline
│   ├── patent → PatentAnalysisPipeline  
│   ├── scientific_paper → ScientificReviewPipeline
│   └── financial_report → FinancialAnalysisPipeline
└── Unified Queue System (4-layer architecture)
```

### 2. DOCUMENT TYPE SYSTEM

**Current**: Only `pitch_deck` type
**Future**: Multi-document type support

**Database Schema**:
```sql
project_documents:
- id (document_id)
- document_type ("pitch_deck", "patent", "scientific_paper", "financial_report")
- document_class_config (JSON with type-specific metadata)
- processing_pipeline (which pipeline to use)
```

**Processing Flow**:
1. **Upload** → Document type classification/detection
2. **Pipeline Selection** → Choose appropriate processing pipeline
3. **Queue Creation** → Create type-specific processing tasks
4. **Processing** → Use unified 4-layer architecture
5. **Results** → Store in unified result format

### 3. API STANDARDIZATION

**Current Inconsistencies**:
- `{"deck_ids": [24]}` (legacy batch)
- `{"document_id": 24}` (single document)

**Unified API Contract**:
```json
// Single document processing
{
  "document_id": 24,
  "document_type": "pitch_deck"
}

// Batch processing  
{
  "document_ids": [24, 25, 26],
  "document_type": "pitch_deck"
}
```

**Endpoints to Standardize**:
- `/api/internal/get-cached-visual-analysis` ✅ (partially done)
- `/api/internal/cache-visual-analysis` 
- `/api/dojo/process-batch`
- `/api/documents/process-single`

### 4. UNIFIED 4-LAYER PROCESSING PIPELINE

**Current**: Separate implementations for dojo vs startup
**Future**: Single pipeline that works for both

**Layer Architecture**:
```
Layer 1: Visual Analysis (Vision Container)
├── Converts PDF pages to visual descriptions
├── Caches results in visual_analysis_cache table
└── Works identically for all document types

Layer 2: Slide Feedback (Vision Container)  
├── Generates slide-by-slide feedback
├── Parallel to Layer 1 (no dependencies)
└── Document-type specific prompts

Layer 3: Core Extractions (Text Container)
├── Company offering, classification, name, funding, date
├── Depends on Layer 1 visual analysis
└── Type-specific extraction prompts

Layer 4: Specialized Analysis (Text Container)
├── Clinical, regulatory, scientific analysis
├── Depends on Layer 3 extractions
└── Highly type-specific (pitch_deck only initially)
```

### 5. QUEUE SYSTEM UNIFICATION

**Current Problems**:
- Dojo: Custom batch processing queue
- Startup: processing_queue table system
- Different task dependency handling

**Unified Solution**:
- Single `processing_queue` table for all processing
- Batch processing creates multiple related tasks
- Same dependency resolution for both workflows
- Unified task status tracking and retry logic

### 6. DOJO-SPECIFIC IMPROVEMENTS

**6.1 Training Data Management**:
- Unified document upload (ZIP support)
- Document type detection on upload
- Batch document classification

**6.2 Experiment Management**:
- Link experiments to document types
- Type-specific experiment results views
- Cross-document-type experiment comparison

**6.3 Results Analysis**:
- Unified results viewer for all document types
- Type-specific results templates
- Performance comparison across document types

### 7. REFACTORING PHASES

**Phase 1: API Standardization** (1-2 days)
- [ ] Update all endpoints to use `document_id` + `document_type`
- [ ] Remove legacy `deck_ids` support
- [ ] Standardize response formats

**Phase 2: Pipeline Unification** (2-3 days)  
- [ ] Create unified ProcessingPipeline base class
- [ ] Migrate dojo processing to use processing_queue table
- [ ] Implement DocumentTypeFactory for pipeline selection
- [ ] Unify visual analysis caching logic

**Phase 3: Document Type Framework** (1-2 days)
- [ ] Add document_type detection on upload
- [ ] Create type-specific processing configurations
- [ ] Update frontend to handle multiple document types
- [ ] Add document type filtering to dojo UI

**Phase 4: Queue System Unification** (2-3 days)
- [ ] Migrate dojo batch processing to unified queue
- [ ] Implement batch task creation for experiments
- [ ] Unify task dependency resolution
- [ ] Update dojo progress tracking

**Phase 5: Multi-Document Type Support** (3-4 days)
- [ ] Implement PatentAnalysisPipeline
- [ ] Implement ScientificReviewPipeline  
- [ ] Add document type upload detection
- [ ] Create type-specific UI components

### 8. SUCCESS CRITERIA

**Technical**:
- Single codebase for all document processing
- Zero code duplication between dojo and startup workflows
- Clean `document_id` + `document_type` architecture throughout
- Unified queue system handling all processing types

**User Experience**:
- GPs can process any document type in dojo
- Consistent processing experience across document types
- Easy addition of new document types
- Seamless startup impersonation for all document types

**Future-Proofing**:
- Ready for patent applications, scientific papers, financial reports
- Extensible pipeline architecture
- Scalable batch processing
- Clean separation of concerns

### 9. IMPLEMENTATION NOTES

**Database Migrations Needed**:
- Add `document_type` column to all relevant tables
- Update foreign key relationships
- Migrate existing `pitch_deck` data

**Backward Compatibility**:
- Maintain support for existing pitch deck processing
- Graceful migration of existing dojo experiments
- No disruption to current startup workflows

**Testing Strategy**:
- Unit tests for each document type pipeline
- Integration tests for unified queue system
- End-to-end dojo workflow testing
- Performance testing for batch processing

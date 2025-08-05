we want to provide feedback to the user, the feedback should be visually
friendly but distinct from other information elements. it will come in a 
form of a comment, i.e. it looks like a piece of chat or discussion thread
below the information element. each feedback will be prefixed by the
"entity" that generated it:

- AI based on analysis of the business case
- GP as humans
- Investors during the funding phase

the startup can react on feedback by:
- replying to the concerns
- adding infomation to the dataroom
- modifying the deck and re-uploading it

GPs can enter a startups deck via the Gallery View on the GP dashboard.
The can then look at various elements of the project (we will explicitly
define which, please do not add this functionality on your own). And
add a comment. 

our AI needs to give feeback on four levels:
1) feedback on each single deck slide 
2) feedback on the template chapters
4) feeback on the slide deck as a whole
1) business case as a whole covering multiple documents


ad 1) **SLIDE-LEVEL FEEDBACK - IMPLEMENTED** ✅
in the deck viewer for each slide, our AI can provide feedback on clarity, visual complexity, and 
"helpfulness for explaining the biz case", "can the reader understand in 10 seconds what the slide 
is supposed to communicated". we need a prompt that looks at the visual analysis (i.e. the textual
description) of this particular slide and generates feedback on that. the AI may also decide not
to generate feedback if the slide is okay, we don't want to spam the user.

**Implementation Details:**
- **Location**: Deck viewer - slide-by-slide view (PowerPoint-like interface)
- **Data Source**: Uses Step 2 visual analysis from Dojo extraction process
- **Storage**: New `slide_feedback` table in project management functionality
- **Access Control**: Both startups and GPs can view slide feedback
- **Generation**: Automatically generated when slides are processed during PDF upload
- **Display Position**: Between slide image and visual analysis description box
- **Visual Design**: 
  - No issues: Green checkmark with "No issues identified" message
  - Has issues: Blue feedback box with specific improvement suggestions
  - Loading: Skeleton placeholder during processing
- **Caching**: Feedback cached in database, regenerated only when deck re-uploaded
- **Prompt**: Stored in `pipeline_prompts` table as 'slide_feedback' stage
- **API Endpoints**: 
  - `GET /api/feedback/projects/{company_id}/decks/{deck_id}/slide-feedback`
  - `GET /api/feedback/projects/{company_id}/decks/{deck_id}/slides/{slide_number}/feedback`
  - `GET /api/feedback/projects/{company_id}/decks/{deck_id}/feedback-summary`
- **Smart Logic**: AI responds with "SLIDE_OK" for good slides (no feedback stored) 


ad 2) 
the templates consist of chapters that cover a single topic during the due dilligence, they
do not follow the structure of the deck but the structure of the GPs thinking how this class of 
startups should be investigated. 

our system already provides feedback on each single question via the scoring functionality.
for the chapters, we introduce a mechanism that looks at the the aggreate for 
- questions plus 
- theirs answers 
- plus their scoring 
meaning that we may have a concatenated context of 4x3 = 12 elements for a chapter that has four
questions and these three elements, or 5x3 = 15 elements if the chapter has five questions and so forth.
we will then use an llm to generate an compact list of maximum five improvements that would enhance this
chapter. 


ad 3)
the deck as a whole may have weaknesses in story telling, amounts of slides per chapter (too many, 
not enough), sequence of slides in context story telling quality / logical order, etc.
we implement this functionality by looking at the suggestions that we generated in step 2 and then 
generate a suggestion list by taking the set of slides into account. ideally, the system then 
would suggest for example:
- slide 4 needs to go back behind slide 13, because there we're covering topic z
- here is one slide missing that exmplains / covers x, it hasn't been introduced before
- this section has too many slides covering topic y
- the overall number of slides is too high, suggestions for deletions: 6, 12, 18

ad 4)
the business case as a whole should look at the set of documents provided and not just the deck
it should also update, once a document is added to the dataroom, for example a financial report,
a scientific paper or competitor analysis.

in this feedback area, we may have two sections:
- why we recommend to invest
- what is concerning us


## Technical Architecture

### Database Schema
- **slide_feedback**: Stores slide-level AI feedback
  - `pitch_deck_id` (FK to pitch_decks)
  - `slide_number` (1-based slide index)
  - `slide_filename` (e.g., slide_001.jpg)
  - `feedback_text` (AI-generated feedback or NULL for SLIDE_OK)
  - `has_issues` (boolean: true = feedback provided, false = no issues)
  - `feedback_type` (default: 'ai_analysis')
  - Unique constraint on (pitch_deck_id, slide_number)

### Processing Pipeline Integration
- **Step 1**: Visual analysis (existing)
- **Step 1.5**: Slide feedback generation (NEW) ✅
- **Step 2**: Company offering extraction (existing)
- **Step 3**: Classification and template processing (existing)

### Prompt Management
All feedback prompts stored in `pipeline_prompts` table:
- `slide_feedback`: OWASP-inspired slide clarity analysis
- Future: `chapter_feedback`, `deck_feedback`, `business_case_feedback`

### API Design Pattern
RESTful endpoints follow project-based structure:
- `/api/feedback/projects/{company_id}/decks/{deck_id}/...`
- Consistent access control (startups: own projects, GPs: all projects)

## Implementation Roadmap

### ✅ **Phase 1: Slide-Level Feedback** (COMPLETED)
- Automatic generation during PDF processing
- Storage in dedicated database table
- Frontend display in deck viewer
- API endpoints for data retrieval
- Smart "no feedback" logic for good slides

### 🔄 **Phase 2: Template Chapter Feedback** (NEXT)
- Aggregate feedback across chapter questions
- Maximum 5 improvement suggestions per chapter
- Context: questions + answers + scores
- Display in template analysis results

### 📋 **Phase 3: Deck-Level Feedback** (FUTURE)
- Holistic slide deck analysis
- Story flow and narrative coherence
- Slide sequencing and organization
- Overall slide count optimization
- Structural recommendations

### 🎯 **Phase 4: Business Case Feedback** (FUTURE)
- Multi-document analysis (deck + dataroom)
- Investment recommendation framework
- "Why recommend" vs "What concerns us"
- Dynamic updates when documents added

## Design Principles

1. **Non-Intrusive**: Feedback appears contextually where relevant
2. **Smart Generation**: AI decides when feedback is necessary
3. **Cached Performance**: Generate once, display many times
4. **Access Control**: Role-based viewing permissions
5. **Visual Hierarchy**: Color-coded feedback types (green=OK, blue=suggestions)
6. **Progressive Enhancement**: System works without feedback, enhanced with it


# Healthcare Template Classification System - Product Requirements Document

## Executive Summary

The Healthcare Template Classification System is the core engine that drives pitch deck analysis by mapping startup classifications to appropriate analysis templates. The system automatically classifies healthcare startups into sectors and selects the most appropriate template for comprehensive analysis, with GP override capabilities as an advanced feature.

**Core Functionality**: Automatically classify healthcare startups based on their company offering and select the most appropriate analysis template from sector-specific templates, with intelligent fallback mechanisms when templates are empty.

**Advanced Feature**: GP Template Override allows General Partners to bypass automatic classification and force the use of a specific template for all analyses.

## System Architecture

### 1. Healthcare Sector Classification Engine ✅
**Core Classification Process**:
1. **Company Offering Extraction**: Extract startup's value proposition from pitch deck
2. **AI-Powered Classification**: Use specialized prompt to classify into healthcare sectors
3. **Template Mapping**: Map classified sector to appropriate analysis template
4. **Intelligent Fallback**: Use Standard Seven-Chapter Review if sector template is empty

### 2. Template-to-Sector Mapping System ✅  
**Database Structure**:
- `healthcare_sectors`: Core healthcare sector definitions
- `analysis_templates`: Analysis templates with sector associations
- `template_chapters`: Chapter structure within templates
- `chapter_questions`: Specific questions and scoring criteria

### 3. GP Template Override System ✅
**Implementation Status**: **COMPLETED**
- ✅ Database table: `template_configurations` 
- ✅ API endpoints: GET/POST `/healthcare-templates/template-config`
- ✅ Frontend integration: Template management UI with persistence
- ✅ Processing pipeline: Upload endpoint includes template config
- ✅ GPU analyzer: Respects override settings with intelligent fallback

### Current Template-to-Sector Mapping
| Healthcare Sector | Template Name | Template ID | Has Chapters |
|------------------|---------------|-------------|--------------|
| biotech_pharma | Biotech & Pharma Standard Analysis | 5 | ✅ 1 chapter |
| consumer_health | Consumer Health Standard Analysis | 7 | ❌ 0 chapters |
| diagnostics_devices | Diagnostics & Devices Standard Analysis | 4 | ❌ 0 chapters |
| digital_therapeutics | Digital Therapeutics Standard Analysis | 1 | ❌ 0 chapters |
| digital_therapeutics | Standard Seven-Chapter Review | 9 | ✅ 7 chapters |
| health_data_ai | Health Data & AI Standard Analysis | 6 | ❌ 0 chapters |
| healthcare_infrastructure | Healthcare Infrastructure Standard Analysis | 2 | ❌ 0 chapters |
| healthcare_marketplaces | Healthcare Marketplaces Standard Analysis | 8 | ❌ 0 chapters |
| telemedicine | Telemedicine Standard Analysis | 3 | ❌ 0 chapters |

**Critical Issue**: Only 2 templates have content. Most sector-specific templates are empty, causing failed analyses.

## Core System Features

### 1. Healthcare Sector Classification Process ✅

#### 1.1 Company Offering Extraction
**Implementation**: `gpu_processing/utils/healthcare_template_analyzer.py`
- Extract company value proposition from visual analysis
- Use specialized prompts to identify core offering
- Store results for classification input

#### 1.2 AI-Powered Sector Classification  
**Classification Logic**:
```python
def _classify_startup(self, company_offering: str) -> Dict[str, Any]:
    """Classify startup into healthcare sector using AI analysis"""
    # Uses classification prompt to analyze company offering
    # Returns: sector, confidence_score, reasoning, recommended_template
```

**Healthcare Sectors Supported**:
- `biotech_pharma`: Biotechnology & Pharmaceutical Development
- `consumer_health`: Consumer Health & Wellness 
- `diagnostics_devices`: Diagnostics & Medical Devices
- `digital_therapeutics`: Digital Therapeutics & Mental Health
- `health_data_ai`: Health Data & AI Analytics
- `healthcare_infrastructure`: Healthcare Infrastructure & Operations
- `healthcare_marketplaces`: Healthcare Marketplaces & Platforms
- `telemedicine`: Telemedicine & Remote Care

#### 1.3 Template Selection Logic ✅
**Current Implementation**:
```python
def _load_template_config_with_fallback(self, template_id: Optional[int] = None) -> Dict[str, Any]:
    """Smart template selection with fallback logic"""
    1. Load requested template
    2. Check if template has chapters and questions
    3. If empty → Fallback to Standard Seven-Chapter Review (ID: 9)
    4. Return populated template configuration
```

### 2. GP Template Override System ✅ **IMPLEMENTED**

#### 2.1 Single Template Mode (Override Enabled)
**Current Status**: ✅ **FULLY FUNCTIONAL**
- GP selects "Use Single Template Mode" in template management UI
- **System ALWAYS runs classification** (required for dojo experiments and analytics)
- **Classification results are stored** but ignored for template selection
- Uses GP's selected template for ALL pitch decks regardless of classification
- Includes smart fallback if selected template is empty
- **Logs both**: classification result AND template override decision

#### 2.2 Classification Mode (Default Behavior)  
**Current Status**: ✅ **FULLY FUNCTIONAL**
- System performs automatic healthcare sector classification
- **Classification results are stored** in database and dojo experiments
- Uses classification-recommended template for analysis
- **Smart Fallback**: If sector template is empty → Standard Seven-Chapter Review
- All decisions are logged for analytics and debugging

### 3. Template-to-Sector Management UI
**Requirement**: Allow GPs to manage which template is used for each healthcare sector

**New UI Components**:
- Sector-template mapping table in Classifications tab
- Dropdown for each sector to select which template to use
- "Fill Empty Templates" button to copy chapters from working templates
- Template content preview (chapter count, question count)

### 4. Processing Pipeline Integration
**Requirement**: Integrate template override into entire processing chain

**Components to Update**:
- Upload API: Accept template preferences
- Processing queue: Store template_id in processing_options  
- Queue processor: Pass template preferences to GPU
- GPU analyzer: Respect template override parameter
- Progress tracking: Update progress based on actual template used

## Technical Implementation Details

### Completed Implementation ✅

#### 1.1 Database Schema ✅ **DEPLOYED**
```sql
-- Template configuration storage (COMPLETED)
CREATE TABLE template_configurations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    use_single_template BOOLEAN DEFAULT false,
    selected_template_id INTEGER REFERENCES analysis_templates(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_template_config UNIQUE (user_id)
);
```

#### 1.2 API Endpoints ✅ **DEPLOYED**
```python
# Template configuration management (COMPLETED)
GET    /api/healthcare-templates/template-config     # Get user's template configuration
POST   /api/healthcare-templates/template-config     # Save template configuration

# Implementation: backend/app/api/healthcare_templates.py
@router.get("/template-config", response_model=TemplateConfigResponse)
async def get_template_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db))

@router.post("/template-config") 
async def save_template_config(config: TemplateConfigRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db))
```

#### 1.3 Processing Pipeline Integration ✅ **DEPLOYED**

##### Upload Processing Enhancement ✅ **COMPLETED**
```python
# In backend/app/api/documents_robust.py (IMPLEMENTED)
@router.post("/upload")
async def upload_document_robust():
    # Get user's template configuration
    template_config = {}
    if current_user.role == "gp":
        template_config_query = text("""
            SELECT use_single_template, selected_template_id 
            FROM template_configurations 
            WHERE user_id = :user_id
        """)
        config_result = db.execute(template_config_query, {"user_id": current_user.id}).fetchone()
        if config_result:
            template_config = {
                "use_single_template": config_result[0],
                "selected_template_id": config_result[1]
            }
    
    processing_options = {
        "generate_thumbnails": True,
        "generate_feedback": True,
        "user_id": current_user.id,
        "upload_timestamp": pitch_deck.created_at.isoformat()
    }
    processing_options.update(template_config)  # Add template config if available
```

##### GPU Analyzer Enhancement ✅ **COMPLETED**
```python
# In gpu_processing/utils/healthcare_template_analyzer.py (IMPLEMENTED)
def analyze_pdf(self, pdf_path: str, company_id: str = None, 
                progress_callback=None, deck_id=None, 
                processing_options: Dict = None) -> Dict[str, Any]:
    
    # Step 3: ALWAYS run classification (required for dojo experiments and analytics)
    self.classification_result = self._classify_startup(self.company_offering)
    logger.info(f"Startup classified as: {self.classification_result.get('primary_sector')} "
               f"({self.classification_result.get('confidence_score', 0):.2f} confidence)")
    
    # Step 4: Determine template selection method (classification vs GP override)
    if processing_options and processing_options.get('use_single_template'):
        # Use GP-specified template override (but keep classification results)
        template_id = processing_options.get('selected_template_id')
        logger.info(f"Template selection: GP override mode - using template_id={template_id}")
        logger.info(f"Classification result stored: {self.classification_result.get('primary_sector')} "
                   f"(would have recommended template {self.classification_result.get('recommended_template')})")
        self.template_config = self._load_template_config_with_fallback(template_id)
    else:
        # Use classification-recommended template
        template_id = self.classification_result.get("recommended_template")
        logger.info(f"Template selection: Classification mode - using recommended template_id={template_id}")
        self.template_config = self._load_template_config_with_fallback(template_id)

def _load_template_config_with_fallback(self, template_id: Optional[int] = None) -> Dict[str, Any]:
    """Load template with fallback to Standard Seven-Chapter Review if empty (IMPLEMENTED)"""
    # Checks for empty templates and falls back to template ID 9 (Standard Seven-Chapter Review)
```

#### 1.4 Frontend Integration ✅ **DEPLOYED**

##### Template Configuration API Integration ✅ **COMPLETED**
```javascript
// In frontend/src/services/api.js (IMPLEMENTED)
export const getTemplateConfig = () => 
  api.get('/healthcare-templates/template-config');
export const saveTemplateConfig = (config) => 
  api.post('/healthcare-templates/template-config', config);
```

##### Enhanced Classifications Tab ✅ **COMPLETED**
```javascript
// In frontend/src/pages/TemplateManagement.js (IMPLEMENTED)
const TemplateManagement = () => {
  // Load/save template configuration with 1-second debounce
  const loadTemplateConfig = async () => {
    const response = await getTemplateConfig();
    const config = response.data;
    setUseClassification(config.use_single_template);
    setSelectedTemplateId(config.selected_template_id || '');
  };

  const saveTemplateConfigDebounced = useCallback(
    debounce(async (config) => {
      await saveTemplateConfig(config);
    }, 1000), []
  );
  
  // Auto-save on configuration changes
  useEffect(() => {
    if (configLoaded) {
      saveTemplateConfigDebounced({
        use_single_template: useClassification,
        selected_template_id: selectedTemplateId || null
      });
    }
  }, [useClassification, selectedTemplateId, configLoaded]);
};
```

### Phase 4: Template Content Management

#### 4.1 Automated Template Population
```python
# Management command to copy chapters from working templates
def populate_empty_templates():
    """Copy chapters from Standard Seven-Chapter Review to empty sector templates"""
    source_template_id = 9  # Standard Seven-Chapter Review
    empty_templates = get_empty_templates()
    
    for template in empty_templates:
        copy_chapters_between_templates(source_template_id, template.id)
        logger.info(f"Populated template {template.name} with chapters from standard template")
```

#### 4.2 Template Content UI
- Template editor for adding/removing chapters
- Question management within chapters
- Template preview with scoring criteria
- Import/export template configurations

## System Status & Testing

### Current Implementation Status: ✅ **FULLY DEPLOYED**

**All Core Features Completed**:
- ✅ Healthcare sector classification engine
- ✅ Template-to-sector mapping system  
- ✅ GP template override functionality
- ✅ Smart fallback mechanisms
- ✅ Database schema and API endpoints
- ✅ Frontend integration with auto-save
- ✅ Processing pipeline integration

### Functional Testing Results ✅

#### Test Case 1: Single Template Mode ✅ **PASSING**
**Given**: GP enables "Use Single Template Mode" and selects "Standard Seven-Chapter Review"
**When**: Any pitch deck is uploaded
**Results**: 
- ✅ **Classification ALWAYS runs** and results are stored in database
- ✅ **Classification visible in dojo experiments** with sector and confidence
- ✅ Standard Seven-Chapter Review template is used (ignoring classification recommendation)
- ✅ 7 chapters are processed successfully
- ✅ All questions are analyzed with scoring
- ✅ **Logs both**: "Startup classified as: [sector]" AND "Template selection: GP override mode"

#### Test Case 2: Classification Mode with Working Template ✅ **PASSING**
**Given**: GP disables "Use Single Template Mode" 
**When**: A biotech startup deck is uploaded
**Results**:
- ✅ Startup is classified into healthcare sector and **results stored**
- ✅ **Classification results visible in dojo experiments**
- ✅ Classification-recommended template is selected and used
- ✅ If template has content → Used directly for analysis
- ✅ Template analysis completed successfully

#### Test Case 3: Classification Mode with Empty Template (Fallback) ✅ **PASSING**
**Given**: GP disables "Use Single Template Mode"
**When**: A startup with empty sector template is uploaded  
**Results**:
- ✅ Startup is classified into healthcare sector and **results stored**
- ✅ **Classification results visible in dojo experiments** (original sector, not fallback)
- ✅ Empty sector template is detected
- ✅ System automatically falls back to Standard Seven-Chapter Review
- ✅ 7 chapters are processed successfully  
- ✅ Fallback decision logged: "Template X has no chapters, falling back"

#### Test Case 4: Template Configuration Persistence ✅ **PASSING**
**Given**: GP changes template configuration in UI
**When**: Settings are modified
**Results**:
- ✅ Settings auto-save with 1-second debounce
- ✅ Settings persist across browser sessions
- ✅ Settings are applied to new pitch deck uploads
- ✅ Database correctly stores user preferences

### Performance Testing
- Template override should not add >500ms to processing time
- Classification skip should improve processing speed by 10-20%
- Database queries should be optimized for template configuration lookups

### User Experience Testing
- GPs can easily understand and configure template settings
- Template content status is clear (has content vs empty)
- Processing progress is accurate and informative
- Error messages are helpful when templates fail

## Migration Strategy

### Phase 1: Backward Compatibility
- Deploy backend changes without breaking existing processing
- Default all users to "Use Classification Mode" 
- Existing behavior remains unchanged

### Phase 2: Gradual Rollout
- Enable template configuration UI for admin users first
- Test with small subset of pitch decks
- Monitor processing success rates and performance

### Phase 3: Full Deployment
- Enable for all GP users
- Migrate existing empty templates with content
- Update documentation and user guides

## Monitoring & Analytics

### Key Metrics
- Template override usage rate (% of users using single template mode)
- Processing success rate by configuration type
- Template utilization (which templates are actually used)
- Fallback frequency (how often empty templates trigger fallbacks)
- Processing time by template configuration

### Logging Strategy
```python
# Enhanced logging for template decisions
logger.info(f"Template decision: user_override={use_override}, template_id={template_id}, source={source}")
logger.info(f"Template content: chapters={chapter_count}, questions={question_count}")
logger.info(f"Processing mode: {'single_template' if use_override else 'classification_with_fallback'}")
```

## Risk Mitigation

### Risk 1: Template Override Breaks Processing
**Mitigation**: Always have fallback to Standard Seven-Chapter Review template

### Risk 2: User Configuration Lost
**Mitigation**: Database constraints and backup strategies for template_configurations table

### Risk 3: Performance Impact
**Mitigation**: Cache template configurations and implement efficient database queries

### Risk 4: User Confusion
**Mitigation**: Clear UI indicators, helpful tooltips, and comprehensive documentation

## Current System Limitations & Future Enhancements

### Known Limitations ⚠️

#### 1. Empty Sector Templates
**Issue**: Most sector-specific templates (7 out of 9) have no chapters or questions
**Impact**: Classification effectively always falls back to Standard Seven-Chapter Review
**Workaround**: Smart fallback system ensures analysis always completes successfully

#### 2. Template Content Management
**Current State**: Templates can only be edited through direct database manipulation
**Needed**: User-friendly template editor for GPs to customize templates

#### 3. Single Standard Template
**Current State**: Only "Standard Seven-Chapter Review" has comprehensive content
**Needed**: Sector-specific templates with tailored questions for each healthcare area

### Immediate Next Steps 🎯

#### Priority 1: Template Content Population
- **Goal**: Populate all empty sector templates with relevant questions
- **Approach**: Copy base structure from Standard Seven-Chapter Review, then customize
- **Timeline**: 1-2 weeks to ensure all sectors have functional templates

#### Priority 2: Template Editor UI  
- **Goal**: Allow GPs to edit template content directly in the UI
- **Features**: Add/edit chapters, modify questions, adjust scoring criteria
- **Integration**: Connect to existing template management infrastructure

### Future Enhancements (Phase 2)

#### Advanced Classification Features
- Multi-sector classification (e.g., "Digital Therapeutics + Health Data AI")
- Confidence-based template selection (use sector template only if >80% confidence)
- Dynamic template blending based on startup characteristics

#### Template Management
- Template versioning and rollback capabilities
- Template sharing between GP users  
- A/B testing of template configurations
- Template performance analytics (which templates produce better analyses)

#### AI-Powered Enhancements
- Machine learning-based template optimization
- Dynamic question generation based on pitch deck content
- Template recommendations based on startup success rates
- Automated template updates based on sector trends

### Integration Opportunities

#### Analytics & Reporting
- Template usage analytics (which templates are most effective)
- Classification accuracy monitoring
- Processing time optimization by template type
- Startup outcome correlation with template choice

#### External Integrations
- Integration with feedback aggregation system
- Template sync with external healthcare sector databases
- API for third-party template providers
- Export templates for use in other analysis tools

---

## Summary

**The Healthcare Template Classification System is now fully operational**, providing:

1. **Automatic Classification**: AI-powered startup classification into healthcare sectors
2. **Smart Template Selection**: Sector-appropriate templates with intelligent fallbacks  
3. **GP Override Capability**: Full control for GPs to bypass classification when needed
4. **Robust Fallback System**: Ensures analysis never fails due to empty templates
5. **Complete Integration**: End-to-end implementation from UI to processing pipeline

**Next Priority**: Populate empty sector templates to maximize the value of the classification system and reduce fallback dependency.

*This system successfully bridges the gap between automatic AI classification and human GP expertise, ensuring comprehensive and appropriate analysis for all healthcare startups.*
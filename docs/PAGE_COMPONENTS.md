# Frontend Pages & Components Reference

This document maps URLs, components, and functionality to help you quickly locate where issues occur. **Always check this before making UI changes.**

## Primary User Interfaces

### Startup Interface

#### `/startup/journey` - StartupJourney.js
**Note**: StartupDashboard.js has been archived - all startup functionality is now in ProjectDashboard

#### `/funding-journey` - StartupJourney.js  
**Purpose**: 14-stage funding process guidance for startups
**Key Features**:
- Step-by-step funding journey visualization
- Progress tracking through funding stages
- Integration with pitch deck analysis

**Data Sources**:
- `getMyProjects()` → `/api/projects/my-projects`
- Funding stage definitions (hardcoded)

### GP (General Partner) Interface

#### `/dojo` - DojoManagement.js
**Purpose**: Advanced AI testing environment for GPs
**Key Features**:
- Manage extraction experiments with multiple decks
- Detailed classification results with confidence scores
- Visual analysis caching and management
- Template processing with custom prompts
- Model configuration and testing

**Data Sources**:
- `getExtractionExperiments()` → `/api/dojo/extraction-test/experiments`
- `getSampleFromExperiment()` → `/api/dojo/extraction-test/experiments/{id}`
- Multiple internal processing endpoints

**Key UI Elements**:
```javascript
// Unique identifiers:
"Dojo: AI Extraction Testing Environment"
"Individual Extraction Results"
"Step 2: Visual Analysis", "Step 3: Extraction Tests"
classificationData.primary_sector, confidence_score
```

**Common Issues**:
- Experiment results not loading → Check GP role authentication
- Classification chips missing → Check `primary_sector` vs `classification` field mapping  
- Processing stuck → Check GPU server connectivity and processing queue

#### `/gp` - GPDashboard.js
**Purpose**: Overview dashboard for GP users
**Key Features**:
- Portfolio overview and metrics
- Project management and review workflows
- Performance analytics

### Project Management Interface

#### `/project` - ProjectDashboard.js
**Purpose**: Individual project management and review
**Key Features**:
- Project-specific extraction results
- Review workflow management  
- Funding stage tracking
- Team collaboration tools

**Data Sources**:
- Project-specific API endpoints
- Review and feedback APIs

## Authentication & User Management

### `/login` - Login.js
**Purpose**: User authentication
**Key Features**:
- Email/password login
- Role-based redirection (startup vs GP)
- JWT token management

### `/register` - Register.js  
**Purpose**: New user registration
**Key Features**:
- Startup vs GP registration flows
- Email verification workflow
- Company association

### `/change-password` - ChangePassword.js
**Purpose**: Forced password change for invited users
**Key Features**:
- Temporary password validation
- New password creation
- Security compliance

### `/verify-email` - VerifyEmail.js
**Purpose**: Email verification after registration
**Key Features**:
- Token-based email verification
- Account activation
- Welcome messaging

## Configuration & Management

### `/config` - ConfigPage.js
**Purpose**: System configuration (GP access only)
**Key Features**:
- Model selection and configuration
- Pipeline prompt management
- System settings

### `/templates` - TemplateManagement.js
**Purpose**: Healthcare template management (GP access only)  
**Key Features**:
- Template creation and editing
- Chapter and question management
- Template assignment to projects

### `/users` - UserManagement.js
**Purpose**: User and invitation management (GP access only)
**Key Features**:
- GP invitation workflow
- User role management  
- Access control

## Component Architecture

### Shared Components (`src/components/`)

#### `DashboardRedirect.js`
**Purpose**: Route users to correct dashboard based on role
**Logic**: 
- Startup users → `/startup`
- GP users → `/gp`
- Unauthenticated → `/login`

#### `LanguageSwitcher.js`
**Purpose**: Multi-language support (German/English)
**Features**: 
- i18n integration
- Language persistence
- UI text switching

#### `ProjectInvitationManager.js`
**Purpose**: Handle project invitations and participant management
**Features**:
- Send invitations to external participants
- Manage project access permissions
- Integration with email system

### Routing Structure (`src/App.js`)

```javascript
// Public routes (no authentication required)
/login → Login.js
/register → Register.js  
/verify-email → VerifyEmail.js
/change-password → ChangePassword.js
/invitation/accept/:token → InvitationAcceptance.js

// Protected routes (authentication required)
/ → DashboardRedirect.js (role-based routing)
/profile → Profile.js
/project/:companyId → ProjectDashboard.js (ALL startup users go here)
/startup/journey → StartupJourney.js

// GP-only routes (GP role required)
/gp → GPDashboard.js
/dojo → DojoManagement.js
/config → ConfigPage.js
/templates → TemplateManagement.js
/users → UserManagement.js
```

## Data Flow Patterns

### 1. Authentication Flow
```
Login.js → JWT token → localStorage → API headers → Backend validation
```

### 2. Dashboard Data Flow
```
StartupDashboard.js → getExtractionResults() → /api/projects/extraction-results
DojoManagement.js → getExtractionExperiments() → /api/dojo/extraction-test/experiments
```

### 3. File Upload Flow
```
File Input → uploadFile() → /api/projects/upload → Processing Queue → Results Display
```

## Finding Components by User Symptoms

### "I can't see my results"
**Likely pages**: StartupDashboard.js, ProjectDashboard.js
**Check**: API responses, authentication, data field mappings

### "Classification/sector not showing"
**Likely pages**: StartupDashboard.js (basic), DojoManagement.js (detailed)
**Check**: Field name mappings (`classification` vs `primary_sector`)

### "Upload not working" 
**Likely pages**: StartupDashboard.js, DojoManagement.js
**Check**: File upload endpoints, processing queue, file size limits

### "Can't access admin features"
**Likely pages**: Any GP-only route
**Check**: User role, authentication token, route protection

### "Experiment results missing"
**Likely pages**: DojoManagement.js
**Check**: GP role, experiment data, backend processing status

## Component Debugging Workflow

### 1. Identify Component (1 minute)
```bash
# Search for unique text from user's description:
grep -r "exact text from page" frontend/src/pages/
grep -r "button text\|header text" frontend/src/components/
```

### 2. Check Component's Data Sources (2 minutes)
```bash
# Find API calls in component:
grep -n "fetch\|api\.\|get.*(" frontend/src/pages/ComponentName.js
grep -n "useState\|useEffect" frontend/src/pages/ComponentName.js
```

### 3. Test API Endpoints (2 minutes)
```bash
# Test the API the component uses:
curl -s "http://localhost:8000/api/endpoint" | jq '.'
./scripts/debug-api.sh relevant-command
```

### 4. Check Field Mappings (1 minute)
```bash
# Compare API response to component expectations:
grep -A5 -B5 "fieldname" frontend/src/pages/ComponentName.js
# Check for null handling, type mismatches, missing fields
```

## Common Component Issues

### StartupDashboard.js Issues
- **Empty results**: Check `/api/projects/extraction-results` and user authentication
- **Missing classification**: Check `classification` field in API response
- **Upload failures**: Check backend processing queue and file validation

### DojoManagement.js Issues  
- **Access denied**: Check GP role authentication
- **Experiment results missing**: Check experiment ID and backend processing status
- **Classification display missing**: Check `primary_sector` field in experiment data

### Authentication Component Issues
- **Login loops**: Check JWT token validity and storage
- **Role redirection wrong**: Check user role in token and DashboardRedirect logic
- **Password change stuck**: Check temporary token validation and expiration

## Development Guidelines

### Adding New Components
1. Follow existing naming patterns (`PageName.js` for pages, `ComponentName.js` for reusable components)
2. Add route to `App.js` with appropriate authentication protection
3. Update this documentation with component purpose and data sources
4. Add API endpoints to `API_MAPPINGS.md`

### Modifying Existing Components
1. Check this document to understand component's purpose and data flow
2. Test changes with relevant API endpoints
3. Verify field mappings in `API_MAPPINGS.md`
4. Update documentation if behavior changes

### Debugging Unknown Issues
1. Use browser dev tools to identify exact component and error
2. Check this document for component's data sources
3. Test API endpoints independently
4. Compare expected vs actual data structures
5. Check authentication and role requirements
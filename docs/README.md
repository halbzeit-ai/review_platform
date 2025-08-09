# Documentation Index

This directory contains comprehensive documentation for the startup review platform. **Start here for any development, debugging, or deployment work.**

## Essential Reading Order

### 1. **ARCHITECTURE_OVERVIEW.md** - Start Here
Complete system overview including server infrastructure, component relationships, and data flow. Essential for understanding the big picture before making any changes.

### 2. **QUICK_DEBUG.md** - For Immediate Issues  
5-minute checklists for common problems. Use this when something is broken and you need fast resolution.

### 3. **PAGE_COMPONENTS.md** - For UI Issues
Maps URLs to components and functionality. Critical for fixing frontend issues or understanding user-reported problems.

### 4. **API_MAPPINGS.md** - For Data Issues
Field name mappings between database, API, and frontend layers. Essential for debugging data display problems.

### 5. **DEPLOYMENT_CHECKLIST.md** - For System Changes
Systematic deployment and service management procedures. Prevents deployment issues and service conflicts.

## Documentation Structure

```
docs/
├── README.md (this file)           - Documentation index and guide
├── ARCHITECTURE_OVERVIEW.md        - Complete system architecture
├── QUICK_DEBUG.md                  - Fast troubleshooting checklists  
├── PAGE_COMPONENTS.md              - Frontend component mapping
├── API_MAPPINGS.md                 - Data field mappings
└── DEPLOYMENT_CHECKLIST.md         - Deployment procedures
```

## When to Use Each Document

### 🚨 **System is Down / Broken**
→ **QUICK_DEBUG.md** - Get system working again in 5 minutes

### 🔍 **User Reports UI Issue** 
→ **PAGE_COMPONENTS.md** - Find the right component to fix

### 📊 **Data Not Displaying Correctly**
→ **API_MAPPINGS.md** - Check field name mappings

### 🚀 **Deploying Changes**
→ **DEPLOYMENT_CHECKLIST.md** - Systematic deployment process

### 🏗️ **Understanding System Design**
→ **ARCHITECTURE_OVERVIEW.md** - Complete system understanding

### ❓ **New to the Project**  
→ Read **ARCHITECTURE_OVERVIEW.md** first, then skim all others

## Common Scenarios & Documentation Paths

### Scenario: "Classification not showing for startups"
1. **PAGE_COMPONENTS.md** → Find that StartupDashboard.js handles `/startup` 
2. **API_MAPPINGS.md** → Check that `/projects/extraction-results` maps `primary_sector` to `classification`
3. **QUICK_DEBUG.md** → Use "Data Not Showing" checklist to verify API and database
4. **DEPLOYMENT_CHECKLIST.md** → Deploy fix using proper service management

### Scenario: "Can't deploy new features to production"  
1. **DEPLOYMENT_CHECKLIST.md** → Follow production deployment procedure
2. **ARCHITECTURE_OVERVIEW.md** → Understand server roles and capabilities
3. **QUICK_DEBUG.md** → Use service management and troubleshooting sections

### Scenario: "New developer onboarding"
1. **ARCHITECTURE_OVERVIEW.md** → Complete system understanding
2. **PAGE_COMPONENTS.md** → Learn frontend structure and routing
3. **API_MAPPINGS.md** → Understand data flow between layers
4. **DEPLOYMENT_CHECKLIST.md** → Learn proper development workflow
5. **QUICK_DEBUG.md** → Reference for common issues

## Documentation Maintenance

### Adding New Features
When adding new functionality, update:
- **PAGE_COMPONENTS.md** - New routes, components, or UI changes
- **API_MAPPINGS.md** - New data fields or API endpoints  
- **DEPLOYMENT_CHECKLIST.md** - New deployment requirements
- **ARCHITECTURE_OVERVIEW.md** - Significant architectural changes

### After Major Issues
When resolving complex issues, update:
- **QUICK_DEBUG.md** - Add new troubleshooting procedures
- **API_MAPPINGS.md** - Document field mapping corrections
- **DEPLOYMENT_CHECKLIST.md** - Add lessons learned to prevent recurrence

### Documentation Standards
- Keep checklists under 5 minutes for QUICK_DEBUG.md
- Include specific commands and examples
- Update immediately after system changes
- Focus on practical, actionable information
- Include both positive (what to do) and negative (what not to do) guidance

## Project Context Files

Beyond this documentation, also reference:

### `/PRD/` - Product Requirements
- **PRD.md** - Overall product vision and requirements
- **dojo-PRD.md** - Dojo testing environment specifications
- **startup-journey.md** - 14-stage funding process details
- **beta-startup-onboarding.md** - Beta testing procedures

### `/CLAUDE.md` - Development Guidelines
- Comprehensive development instructions for AI assistants
- Environment detection and server capabilities
- Development rules and architectural decisions
- Memory management and debugging capabilities

### Root Level Files
- **README.md** - Basic setup and getting started
- **requirements.txt** / **package.json** - Dependency specifications
- **.env.example** - Environment configuration templates

## Emergency Contacts & Escalation

For issues beyond what these documents can resolve:
- **System Administrator**: For infrastructure, database, or networking issues
- **Product Owner**: For product requirements or user experience decisions  
- **Security Team**: For authentication, authorization, or data security issues

Remember: These documents are designed to resolve 90% of issues quickly. If you're spending more than the stated time limits, escalate rather than continuing to troubleshoot alone.
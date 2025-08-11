# System Architecture Overview

This document provides a comprehensive overview of the startup review platform's architecture, data flow, and component relationships. **Read this first to understand the system before making changes.**

## System Overview

The platform is a distributed AI-powered startup review system with separate CPU and GPU infrastructure, supporting both development and production environments.

```
┌─────────────────────────────────────────────────────────────────┐
│                    STARTUP REVIEW PLATFORM                     │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React)     Backend (FastAPI)     GPU Processing     │
│  ├─ StartupDashboard  ├─ Authentication     ├─ Visual Analysis │ 
│  ├─ DojoManagement    ├─ Document APIs      ├─ Classification  │
│  ├─ ProjectMgmt       ├─ Review Workflow    ├─ Extraction      │
│  └─ Admin Tools       └─ Database Layer     └─ Template Proc.  │
├─────────────────────────────────────────────────────────────────┤
│              Shared NFS Storage & PostgreSQL                   │
└─────────────────────────────────────────────────────────────────┘
```

## Server Infrastructure

### Development Environment
- **dev_cpu** (65.108.32.143): Primary development server
  - Frontend development (React dev server, port 3000)
  - Backend API (FastAPI, port 8000)
  - PostgreSQL database (`review_dev`)
  - Nginx (production builds)

- **dev_gpu** (135.181.71.17): GPU processing development
  - AI model inference and training
  - PDF visual analysis
  - Classification and extraction processing
  - Connected to dev_cpu database and shared storage

### Production Environment
- **prod_cpu** (135.181.63.224/135.181.63.168): Production web server
  - Frontend (served by nginx with SSL)
  - Backend API (systemd service, port 8000)
  - PostgreSQL database (`review-platform`)
  - SSL termination and request routing

- **prod_gpu** (135.181.63.133): Production GPU processing
  - Production AI inference
  - Batch processing capabilities
  - Connected to prod_cpu database and shared storage

### Shared Infrastructure
- **NFS Storage**: Distributed filesystem for uploads, results, and logs
  - Development: `/mnt/dev-shared/`
  - Production: `/mnt/CPU-GPU/`
- **Database**: PostgreSQL with environment-specific instances
- **Networking**: Private network between CPU and GPU servers

## Healthcare Analysis Systems

### Template-Based Chapter Analysis
The platform uses templates to structure startup analysis into chapters. Each template defines:
- **Chapters**: Logical sections of the analysis (e.g., problem_analysis, solution_approach)
- **Questions**: Specific questions within each chapter
- **Scoring**: Criteria and weights for evaluation

Example: Standard Seven-Chapter Review template contains chapters like:
- problem_analysis, solution_approach, product_market_fit, monetization, financials, use_of_funds, organization

### Specialized Healthcare Analysis
Independent of templates, the platform generates three specialized analyses for healthcare startups:
- **clinical_validation**: Analysis of clinical study design, endpoints, statistical significance
- **regulatory_pathway**: FDA/CE mark strategy, regulatory milestones, compliance requirements
- **scientific_hypothesis**: Core scientific assumptions, biological mechanisms, evidence base

These analyses are:
- Generated for ALL healthcare startups regardless of template
- Stored separately in `specialized_analysis_results` table
- Similar to extraction results (company_offering, classification) in nature
- Displayed alongside template results in the UI

### Key Distinction
- **Template Chapters**: Variable based on selected template, stored in `chapter_analysis`
- **Specialized Analysis**: Fixed set of three analyses, stored in `specialized_analysis_results`
- Both are generated during GPU processing but serve different purposes

## Component Architecture

### Frontend (React Application)

```
Frontend Structure:
├── Public Routes
│   ├── /login (Login.js) - Authentication
│   ├── /register (Register.js) - User registration
│   └── /verify-email (VerifyEmail.js) - Email verification
│
├── Startup Interface
│   ├── /startup (StartupDashboard.js) - Main dashboard
│   │   ├─ File upload widget
│   │   ├─ Extraction results display
│   │   └─ Basic classification view
│   └── /startup/journey (StartupJourney.js) - Funding stages
│
├── GP Interface  
│   ├── /gp (GPDashboard.js) - GP overview
│   ├── /dojo (DojoManagement.js) - AI testing environment
│   │   ├─ Experiment management
│   │   ├─ Detailed classification results
│   │   ├─ Visual analysis caching
│   │   └─ Template processing
│   ├── /config (ConfigPage.js) - System configuration
│   ├── /templates (TemplateManagement.js) - Template editing
│   └── /users (UserManagement.js) - User management
│
└── Shared Components
    ├── Authentication & routing
    ├── Language switching (German/English)
    └── Common UI elements
```

### Backend (FastAPI Application)

```
Backend Structure:
├── Authentication Layer
│   ├── JWT token management
│   ├── Role-based access control (startup/gp)
│   └── Email verification system
│
├── API Endpoints (/app/api/)
│   ├── auth.py - Authentication endpoints
│   ├── projects.py - Project and extraction management
│   ├── dojo.py - Advanced AI testing and experiments
│   ├── documents_robust.py - Document upload and processing
│   ├── project_management.py - Project member management
│   └── debug.py - Internal debugging tools
│
├── Core Services (/app/services/)
│   ├── email_service.py - SMTP email handling
│   ├── startup_classifier.py - AI classification logic
│   ├── template_processor.py - Healthcare template processing
│   └── queue_processor.py - Background task processing
│
├── Database Layer (/app/db/)
│   ├── models.py - SQLAlchemy models
│   ├── database.py - Connection management
│   └── Migration scripts
│
└── Processing Integration
    ├── GPU server communication
    ├── Shared filesystem management
    └── Background task coordination
```

### GPU Processing System

```
GPU Processing Architecture:
├── HTTP API Server (port 8001)
│   ├── Health checks and status reporting
│   ├── Model management and configuration
│   └── Processing job coordination
│
├── AI Processing Pipeline
│   ├── Visual Analysis (PDF → page descriptions)
│   ├── Text Extraction (visual → structured text)
│   ├── Classification (text → industry sectors)  
│   ├── Template Analysis (classification → template selection)
│   └── Batch processing capabilities
│
├── Model Management
│   ├── Vision models (PDF page analysis)
│   ├── Language models (classification, extraction)
│   ├── Template models (healthcare-specific analysis)
│   └── Model versioning and configuration
│
└── Data Integration
    ├── Shared filesystem access
    ├── Direct database connectivity
    └── Result caching and storage
```

## Data Flow Architecture

### Document Processing Pipeline

```
1. Upload Flow:
   User Upload → Frontend → Backend API → Shared Storage
                     ↓
   Processing Queue → GPU Server → Visual Analysis → Results Cache
                     ↓
   Text Extraction → Classification → Template Analysis → Database Storage
                     ↓
   Frontend Polling → Results Display

2. Data Storage Locations:
   ┌─ Raw Files: /mnt/*/uploads/[project_id]/[filename]
   ├─ Results: /mnt/*/results/[processing_id]/
   ├─ Cache: visual_analysis_cache table
   └─ Final Data: extraction_experiments table
```

### Database Schema Architecture

```sql
-- Core Entities
users (authentication, roles)
├── projects (project containers for all documents)
│   ├── project_members (user-project relationships)
│   ├── project_documents (uploaded documents)
│   │   ├── reviews (GP feedback)
│   │   └── extraction_experiments (AI results)
│   │       ├── results_json (offering extraction)
│   │       ├── classification_results_json (sector classification)
│   │       ├── company_name_results_json (company name extraction)
│   │       ├── funding_amount_results_json (funding extraction)
│   │       └── deck_date_results_json (date extraction)
│   └── project_stages (funding journey stages)

-- Supporting Systems
├── visual_analysis_cache (PDF page analysis)
├── analysis_templates (healthcare templates)
│   ├── template_chapters 
│   └── chapter_questions
├── pipeline_prompts (AI prompt management)
└── processing_queue (background tasks)
```

## Authentication & Authorization

### User Roles & Permissions

```
Role Hierarchy:
├── startup
│   ├── Upload documents to projects
│   ├── View project documents and results
│   ├── Access project funding journey
│   └── Collaborate with project members
│
└── gp (General Partner)
    ├── All startup permissions
    ├── Access Dojo testing environment  
    ├── Manage extraction experiments
    ├── Configure AI models and prompts
    ├── Manage healthcare templates
    ├── Invite and manage users
    └── Access system configuration
```

### Authentication Flow

```
1. Registration/Invitation:
   User Registration → Email Verification → Account Activation
   GP Invitation → Temporary Password → Forced Password Change

2. Login Process:
   Credentials → JWT Token → Role-based Routing
   ├─ startup → /startup dashboard
   └─ gp → /gp dashboard

3. API Authorization:
   Request → JWT Validation → Role Check → Endpoint Access
```

## Integration Points

### External Services

```
Email System (Hetzner SMTP):
├── Registration verification emails
├── GP invitation emails  
├── Password reset notifications
└── Welcome and notification emails

File Storage:
├── NFS shared filesystem (primary)
├── Local filesystem (development fallback)
└── S3 integration (planned for scalability)

AI Services:
├── OpenAI API (classification, extraction)
├── Local models (visual analysis)
└── Custom healthcare models (template processing)
```

### Inter-Service Communication

```
Frontend ←→ Backend:
├── REST API (JSON over HTTPS)
├── JWT authentication
├── WebSocket (planned for real-time updates)
└── File upload (multipart/form-data)

Backend ←→ GPU:
├── HTTP API (internal endpoints)
├── Shared filesystem (file exchange)
├── Direct database access (PostgreSQL)
└── Job queue coordination

CPU ←→ CPU:
├── Git synchronization (code deployment)
├── Database replication (planned)
└── Shared configuration management
```

## Environment Configuration

### Configuration Hierarchy

```
Environment Configuration:
├── Global Settings (/environments/)
│   ├── .env.backend.development
│   ├── .env.backend.production  
│   ├── .env.gpu.development
│   └── .env.gpu.production
│
├── Component-Specific
│   ├── backend/.env (deployed from global)
│   ├── gpu_processing/.env (deployed from global)
│   └── frontend/.env.* (build-time configuration)
│
└── System Configuration
    ├── Nginx (/etc/nginx/sites-enabled/)
    ├── Systemd (/etc/systemd/system/)
    └── SSL certificates (/etc/letsencrypt/)
```

### Environment Variables

```bash
# Core Service URLs
BACKEND_DEVELOPMENT=http://65.108.32.143:8000
BACKEND_PRODUCTION=http://65.108.32.168:8000
GPU_DEVELOPMENT=135.181.71.17
GPU_PRODUCTION=135.181.63.133

# Database Configuration
DATABASE_HOST=<environment-specific>
DATABASE_NAME=review_dev|review-platform
DATABASE_USER=postgres
DATABASE_PASSWORD=<environment-specific>

# Shared Storage
SHARED_FILESYSTEM_MOUNT_PATH=/mnt/dev-shared|/mnt/CPU-GPU

# Email Configuration  
SMTP_SERVER=mail.halbzeit.ai
FROM_EMAIL=registration@halbzeit.ai
```

## Performance & Scalability

### Current Performance Characteristics

```
Processing Capacity:
├── PDF Analysis: ~2-5 seconds per page
├── Text Extraction: ~1-3 seconds per document  
├── Classification: ~500ms per company offering
└── Template Processing: ~10-30 seconds per document

Storage Requirements:
├── Original PDFs: ~1-10MB per document
├── Visual Analysis: ~10-50KB per page
├── Extraction Results: ~1-5KB per document
└── Database Records: ~10-20KB per experiment
```

### Scalability Considerations

```
Current Limitations:
├── Single GPU server per environment
├── Synchronous processing (no parallel processing)
├── Limited model caching
└── No content delivery network (CDN)

Scaling Strategies:
├── Horizontal GPU scaling (multiple servers)
├── Asynchronous processing with job queues
├── Database read replicas
├── CDN for static assets
└── Container orchestration (Docker/Kubernetes)
```

## Security Architecture

### Data Security

```
Encryption:
├── HTTPS/TLS for all web traffic
├── JWT token encryption for authentication
├── Database connection encryption (SSL)
└── File storage access controls

Access Controls:
├── Role-based permissions (startup/gp)
├── Project-based data isolation
├── Project membership verification
├── API endpoint protection
└── Database row-level security
```

### Operational Security

```
System Security:
├── Regular security updates
├── Firewall configuration
├── SSH key-based authentication
├── Service isolation
└── Log monitoring

Data Privacy:
├── GDPR compliance measures
├── Data retention policies  
├── User consent management
└── Secure data deletion
```

## Monitoring & Logging

### Logging Architecture

```
Centralized Logging:
├── Backend: /mnt/*/logs/backend.log
├── GPU Processing: /mnt/*/logs/gpu_http_server.log
├── Nginx: /var/log/nginx/
└── System: journalctl (systemd services)

Log Format:
├── Structured JSON logging
├── Request/response correlation IDs
├── Performance metrics
└── Error stack traces
```

### Monitoring Points

```
System Monitoring:
├── Service health checks
├── Database connection monitoring
├── Shared filesystem availability
├── GPU utilization tracking
└── API response times

Business Metrics:
├── Document processing success rates
├── User activity patterns
├── Classification accuracy metrics
└── System performance trends
```

## Development Workflow

### Code Organization

```
Repository Structure:
├── /frontend/ (React application)
├── /backend/ (FastAPI application)  
├── /gpu_processing/ (AI processing)
├── /environments/ (configuration management)
├── /scripts/ (deployment and utility scripts)
├── /docs/ (system documentation)
└── /PRD/ (product requirements)
```

### Deployment Pipeline

```
Development → Testing → Production:
1. Local development and testing
2. Commit to git with structured messages
3. Deploy to development environment  
4. Integration testing and validation
5. Deploy to production environment
6. Post-deployment verification
```

This architecture overview provides the foundational understanding needed to work effectively with the startup review platform. Refer to specific component documentation for detailed implementation guidance.
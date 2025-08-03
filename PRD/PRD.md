# Review Platform - Product Requirements Document (PRD)

## Overview

The Review Platform is a startup review and investment management platform that facilitates the evaluation, due diligence, and funding process for startups seeking venture capital investment.

## Core User Personas

### 1. **General Partners (GPs)**
- **Role**: Investment decision makers at venture capital firms
- **Goals**: Evaluate startup opportunities, manage due diligence, track investment pipeline
- **Key Activities**: Review pitch decks, conduct interviews, manage funding processes

### 2. **Startups**  
- **Role**: Entrepreneurs seeking venture capital funding
- **Goals**: Present their business effectively, navigate funding process, secure investment
- **Key Activities**: Upload pitch decks, complete funding stages, respond to due diligence requests

## Core Product Areas

### 1. **AI-Powered Startup Analysis**
- Automated pitch deck analysis and scoring
- Healthcare sector classification and specialized analysis
- Scientific hypothesis generation and validation
- Regulatory pathway assessment
- Clinical validation analysis

### 2. **Dojo Testing Environment**
- Safe testing environment for GPs to experiment with prompts and models
- A/B testing capabilities for AI analysis parameters
- Startup experience impersonation for testing
- Experiment tracking and results comparison

### 3. **Funding Process Management**
- 14-stage standardized funding pipeline
- Document management and version control  
- Stage progression tracking and automation
- Investor communication and commitment tracking

### 4. **Project Gallery & Dashboard**
- Unified view of all startup projects
- Real-time progress tracking and analytics
- Performance metrics and reporting
- Classification-based filtering and insights

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Processing**: GPU-accelerated LLM inference (Ollama)
- **Storage**: S3-compatible object storage
- **Authentication**: JWT-based authentication

### Frontend  
- **Framework**: React 18
- **UI Library**: Material-UI (MUI)
- **State Management**: React hooks and context
- **Routing**: React Router
- **Internationalization**: react-i18next

### Infrastructure
- **Deployment**: Docker containers with systemd
- **Web Server**: Nginx with zero-downtime deployments
- **File System**: NFS shared storage for GPU-CPU communication
- **Monitoring**: OpenTelemetry integration

## Key Features

### For GPs
- **Dashboard**: Overview of all startups, performance metrics, pipeline analytics
- **AI Analysis**: Automated pitch deck evaluation with customizable scoring
- **Dojo Environment**: Test AI parameters and prompts safely
- **Project Management**: Track startups through 14-stage funding process
- **Due Diligence**: Manage document collection and review processes

### For Startups
- **Pitch Deck Upload**: Secure document upload with AI analysis
- **Funding Journey**: Visual progress tracking through funding stages
- **Document Management**: Upload and manage required documents per stage
- **Communication**: Direct messaging with GPs and investor updates
- **Progress Tracking**: Real-time status of funding application

## Success Metrics

### Efficiency Metrics
- Time from pitch deck upload to initial GP review
- Due diligence completion time
- Document processing and analysis speed

### Quality Metrics  
- AI analysis accuracy vs. GP manual review
- Startup satisfaction with feedback quality
- GP confidence in AI-assisted decision making

### Business Metrics
- Number of startups evaluated per month
- Funding completion rate through platform
- GP time savings vs. manual processes

## Roadmap Priorities

### Phase 1: Core Platform (Current)
- ✅ AI pitch deck analysis
- ✅ Basic funding stage management
- ✅ Dojo testing environment
- ✅ Project gallery and dashboards

### Phase 2: Enhanced Intelligence  
- Advanced sector-specific analysis templates
- Multi-document analysis (financials, research papers)
- Competitive landscape analysis
- Market sizing and validation

### Phase 3: Ecosystem Integration
- Investor network integration
- Legal document automation
- Financial modeling tools
- Portfolio company management

### Phase 4: Scale & Automation
- Multi-language support
- Advanced analytics and predictions
- API ecosystem for third-party integrations
- White-label platform offerings
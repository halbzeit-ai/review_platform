# Startup Review Platform

A comprehensive platform for healthcare startup pitch deck analysis and review, featuring AI-powered analysis, structured templates, and GP-startup communication workflows.

## System Overview

* Startups register via email and confirm registration via email link
* They upload pitch decks (PDF files) to the website
* PDF files are stored in S3 bucket hosted on Datacrunch.io
* S3 upload triggers AI processing on GPU instances
* AI Python script generates structured review JSON files
* PostgreSQL database stores login data, deck links, and review metadata
* GPs are notified via email when reviews are generated
* GPs can view, modify, and approve reviews through the web interface
* Startups are notified when reviews are approved
* Startups can answer GP questions through the platform
* Q&A interactions are stored in PostgreSQL and linked to respective startups

## Architecture

### Backend (FastAPI)
- **Location**: `backend/` directory
- **Main entry**: `backend/app/main.py`
- **Database**: PostgreSQL (production) / SQLite (development)
- **Features**: JWT authentication, file upload, email notifications, healthcare templates

### Frontend (React)
- **Location**: `frontend/` directory  
- **Tech stack**: React 18, Material-UI, Recharts for visualizations
- **Features**: Dynamic polar plots, healthcare template support, responsive design

### AI Processing (GPU)
- **Location**: `gpu_processing/` directory
- **Features**: Healthcare-specific analysis, template-based scoring, visual analysis

## Quick Start

### Frontend Setup
```bash
cd frontend
npm install
npm start        # Development server (port 3000)
npm run build    # Production build
```

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

### Database Setup
```bash
# PostgreSQL setup (production)
# Configure connection in backend/app/core/config.py

# SQLite setup (development)
# Database created automatically at backend/sql_app.db
```

## Key Features

### 🎯 Healthcare Template System
- **7-Chapter Analysis**: Problem, Solution, Market Fit, Monetization, Financials, Use of Funds, Organization
- **34 Strategic Questions**: Comprehensive evaluation framework
- **Weighted Scoring**: Chapter-level and overall scoring (0-7 scale)
- **Specialized Analysis**: Clinical validation, regulatory pathway, scientific hypothesis

### 📊 Dynamic Polar Plots
- **Radar Chart Visualization**: Interactive polar plots for investment analysis
- **Template-Driven**: Automatically adapts to template structure
- **Professional Styling**: Investment-appropriate visual design
- **Responsive Design**: Works on desktop and mobile

### 🔐 Multi-User Authentication
- **Startup Registration**: Email confirmation workflow
- **GP Dashboard**: Review management and approval
- **Role-Based Access**: Different views for startups vs GPs
- **JWT Security**: Secure token-based authentication

### 📧 Email Workflows
- **Registration Confirmation**: Email verification for new users
- **Review Notifications**: GP alerts for new reviews
- **Approval Notifications**: Startup alerts for approved reviews
- **Q&A Notifications**: Interaction alerts for ongoing discussions

### 🤖 AI-Powered Analysis
- **PDF Processing**: Extract and analyze pitch deck content
- **Visual Analysis**: Slide-by-slide image analysis
- **Healthcare Classification**: Sector-specific categorization
- **Question-Response Generation**: Structured analysis output

## Development Commands

### Frontend
```bash
cd frontend
npm install                    # Install dependencies
npm start                     # Development server
npm run build                 # Production build
npm test                      # Run tests
npm run test:coverage         # Test coverage
```

### Backend
```bash
cd backend
pip install -r requirements.txt    # Install dependencies
uvicorn app.main:app --reload      # Development server
mypy .                             # Type checking
pytest                             # Run tests
```

### Type Checking
```bash
cd backend
mypy .
```

## File Storage Architecture

### Current Implementation
1. **Upload**: Startup uploads PDF → Shared NFS filesystem (`/mnt/shared/uploads/`)
2. **Processing**: Background task triggers AI processing on GPU instance
3. **Results**: AI generates review JSON → stored in shared filesystem (`/mnt/shared/results/`)
4. **Database**: Review metadata linked in PostgreSQL database
5. **Notifications**: Email notifications sent to relevant parties

### Development Setup
- **Local Development**: NixOS development machine
- **Production**: Datacrunch.io CPU server + GPU instances
- **Communication**: HTTP API between GPU and CPU servers
- **Storage**: Shared NFS filesystem for file coordination
- **Database**: PostgreSQL for multi-server access

## Database Schema

### Key Tables
- **users**: Authentication and user management
- **pitch_decks**: Uploaded deck metadata
- **pipeline_prompts**: Customizable AI analysis prompts
- **healthcare_sectors**: Healthcare classification system
- **analysis_templates**: Template definitions
- **template_chapters**: Chapter structure
- **chapter_questions**: Question framework
- **model_configs**: AI model configurations

## Development Workflow

### Git Workflow
- **Development**: Local NixOS machine
- **Commits**: Claude Code commits changes
- **Deployment**: Human pushes to production servers
- **Coordination**: Git repo accessible on both CPU and GPU servers

### Testing
- **Frontend**: Jest + React Testing Library
- **Backend**: pytest + type checking
- **Integration**: API testing with mock services
- **Coverage**: Comprehensive test coverage reporting

## Production Deployment

### Frontend
```bash
npm run build
# Deploy build/ directory to web server
```

### Backend
```bash
# Configure PostgreSQL connection
# Set up environment variables
# Deploy with uvicorn or gunicorn
```

### Database Migration
```bash
# Migrate from SQLite to PostgreSQL
# See migration scripts in backend/
```

## Configuration

### Environment Variables
- Database connections
- Email SMTP settings
- File storage paths
- API endpoints

### Settings Files
- `frontend/src/config/`: Frontend configuration
- `backend/app/core/config.py`: Backend configuration
- `CLAUDE.md`: Development guidelines and architecture

## Contributing

### Development Rules
- Follow `rules/python.md` for Python development
- Use type hints and mypy for type safety
- Implement comprehensive testing
- Follow functional programming patterns
- Use domain-driven design architecture

### Code Style
- **Python**: Type hints, dataclasses, functional patterns
- **React**: Hooks, Material-UI, modern React patterns
- **Database**: PostgreSQL with proper indexing
- **Testing**: Unit, integration, and coverage testing

## Support

For development guidance, see:
- `CLAUDE.md`: Project architecture and development guidelines
- `frontend/INSTALL.md`: Detailed frontend setup instructions
- `rules/python.md`: Python development standards
- `worklog/`: Development session logs and architecture decisions
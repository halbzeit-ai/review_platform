# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a startup review platform with a Python FastAPI backend and React frontend. The platform allows:
- Startups to register, upload pitch decks (PDFs), and receive AI-generated reviews
- GPs (General Partners) to review, modify, and approve reviews
- A Q&A system between startups and GPs
- S3 integration for file storage and AI processing triggers

## Architecture

### Backend (FastAPI)
- **Location**: `backend/` directory
- **Main entry**: `backend/app/main.py`
- **Structure**:
  - `app/api/`: API endpoints (auth, decks, reviews, questions, documents)
  - `app/core/`: Configuration and storage utilities
  - `app/db/`: Database models and connection (SQLAlchemy)
  - `app/services/`: Business logic services
  - `app/processing/`: AI processing components

### Frontend (React)
- **Location**: `frontend/` directory
- **Tech stack**: React 18, Material-UI, React Router
- **Structure**:
  - `src/pages/`: Main application pages (Login, Register, Review, Dashboards)
  - `src/components/`: Reusable UI components
  - `src/services/`: API communication layer
  - `src/utils/`: Utility functions (theme, etc.)

### Database
- SQLite for development (`backend/sql_app.db`)
- PostgreSQL for production (as indicated in PRD)

## Development Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

### Frontend
```bash
cd frontend
npm install
npm start        # Development server
npm run build    # Production build
npm test         # Run tests
```

### Type Checking
```bash
cd backend
mypy .
```

## Important Development Rules

The `rules/python.md` file contains comprehensive Python development guidelines including:
- Type safety with strict mypy settings
- Functional programming patterns
- Domain-driven design architecture
- Result types for error handling
- Comprehensive testing strategies

Key principles:
- Always use type hints
- Prefer pure functions and immutable data
- Use dataclasses with `frozen=True`
- Follow domain-driven design patterns
- Implement proper error handling with custom exceptions

## Key Integration Points

- **Shared Filesystem Storage**: Files stored on Datacrunch.io NFS shared filesystem
- **AI Processing**: On-demand GPU instances process uploaded PDFs via shared storage
- **Email Notifications**: System sends emails for review workflows (planned)
- **Authentication**: JWT-based auth system for both user types

## File Storage Flow (Current Implementation)

1. Startup uploads PDF → Shared NFS filesystem (`/mnt/shared/uploads/`)
2. Background task triggers AI processing on on-demand GPU instance
3. AI generates review JSON → stored in shared filesystem (`/mnt/shared/results/`)
4. Review data linked in SQLite database
5. Email notifications sent to relevant parties (planned)

## development setup
- we have a local development machine running nixos
- in the cloud at datacrunch.io, we have a production server CPU and a GPU instance for running LLMs
- the GPU and the CPU communicate via http
- git: claude should always add and commit, human should always push 
- the GPU and the CPU have access to the git repo, i.e. usually no copying between these two is necessary.

## Development Memories
- please do remember that you are on a development machine, the UUIDs, filepaths and SQL databases I paste are from the production machine
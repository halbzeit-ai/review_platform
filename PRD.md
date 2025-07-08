

# Product Requirements Document: Startup Review Platform

## 1. System Overview

The Startup Review Platform allows startups to upload pitch decks, which are automatically reviewed using AI, and then enables General Partners (GPs) to provide feedback and ask questions.

### 1.1 Core Components
- **Web Application**: Frontend (React + Material UI) + Backend (FastAPI)
- **Processing Coordinator**: Manages the pitch deck processing workflow
- **Database**: PostgreSQL for user data, reviews, and Q&A
- **Storage**: S3 bucket for pitch decks and reviews
- **Processing**: On-demand GPU droplets for AI analysis

## 2. Implementation Plan

### 2.1 Repository Structure
1. Create a new GitHub repository with the following structure:
```
startup-review-platform/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core functionality
│   │   ├── db/            # Database models
│   │   ├── processing/    # Processing coordinator
│   │   └── services/      # External services (S3, email)
│   ├── infrastructure/    # Terraform scripts
│   │   ├── app/           # Web application infrastructure
│   │   └── processing/    # GPU droplet templates
│   └── tests/             # Backend tests
├── frontend/              # React application
│   ├── public/
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API client services
│   │   └── utils/         # Utility functions
│   └── tests/             # Frontend tests
└── docs/                  # Documentation
```

### 2.2 Infrastructure Setup

1. **CPU Droplet for Web Application**:
   - Deploy a DigitalOcean droplet (4GB RAM, 2 vCPUs minimum)
   - Install Docker, Docker Compose
   - Set up Nginx as reverse proxy
   - Configure SSL with Let's Encrypt

2. **Database**:
   - Deploy PostgreSQL database (managed service recommended)
   - Set up connection pooling
   - Configure backup strategy

3. **S3 Storage**:
   - Configure existing S3 bucket for event notifications
   - Set up appropriate CORS policies
   - Define lifecycle policies for storage management

4. **Email Service**:
   - Set up SMTP service (SendGrid, Mailgun, or Amazon SES)
   - Configure email templates
   - Implement email queue for reliability

## 3. Backend Implementation

### 3.1 FastAPI Application

1. **Core Features**:
   - JWT authentication with role-based access control
   - S3 integration for file uploads
   - Email service for notifications
   - Database ORM (SQLAlchemy)

2. **API Endpoints**:
   - Authentication: `/api/auth/register`, `/api/auth/login`, `/api/auth/verify/{token}`
   - Pitch Decks: `/api/decks`, `/api/decks/{id}`
   - Reviews: `/api/reviews`, `/api/reviews/{id}`
   - Questions: `/api/reviews/{id}/questions`, `/api/questions/{id}/answer`

3. **Database Models**:
   - Users: `id`, `email`, `password_hash`, `company_name`, `role`, `is_verified`
   - PitchDecks: `id`, `user_id`, `file_name`, `s3_url`, `created_at`
   - Reviews: `id`, `pitch_deck_id`, `review_data`, `s3_review_url`, `status`
   - Questions: `id`, `review_id`, `question_text`, `asked_by`
   - Answers: `id`, `question_id`, `answer_text`, `answered_by`

### 3.2 Processing Coordinator

1. **S3 Event Handler**:
   - Endpoint to receive S3 event notifications
   - Queue management for processing jobs
   - Status tracking for jobs

2. **GPU Droplet Management**:
   - Terraform wrapper for creating droplets
   - SSH utilities for remote command execution
   - Droplet monitoring and lifecycle management

3. **Processing Workflow**:
   - File transfer between S3 and GPU droplet
   - Script execution and monitoring
   - Result collection and storage

## 4. Frontend Implementation

### 4.1 React Application

1. **Authentication**:
   - Login/registration forms
   - JWT token management
   - Protected routes

2. **Startup Interface**:
   - Dashboard with pitch deck status
   - Pitch deck upload
   - Review viewing
   - Question answering

3. **GP Interface**:
   - Review list and filtering
   - Review editing and approval
   - Question asking
   - Answer viewing

### 4.2 Material UI Components

1. **Layout Components**:
   - Navigation
   - Dashboard layout
   - Responsive containers

2. **Form Components**:
   - Login/registration forms
   - File upload with drag-and-drop
   - Question/answer forms

3. **Display Components**:
   - Review display with editing capabilities
   - Q&A thread view
   - Status indicators

## 5. Processing Implementation

### 5.1 GPU Droplet Template

1. **Base Configuration**:
   - Ubuntu 20.04 with CUDA support
   - Docker for containerization
   - Python environment setup

2. **Ollama Configuration**:
   - Installation script
   - Model pulling and management
   - Resource allocation

3. **Processing Script Integration**:
   - Script deployment
   - Parameter configuration
   - Output standardization

### 5.2 Infrastructure as Code

1. **Terraform Modules**:
   - GPU droplet provisioning
   - Network security configuration
   - SSH key management

2. **Automation Scripts**:
   - Droplet creation
   - Software installation
   - Model deployment

## 6. Deployment Plan

### 6.1 Initial Setup

1. **Repository Initialization**:
   - Create GitHub repository
   - Set up branch protection
   - Configure CI/CD workflows

2. **Infrastructure Deployment**:
   - Deploy CPU droplet for web application
   - Set up database
   - Configure S3 bucket for events

3. **Backend Deployment**:
   - Deploy FastAPI application
   - Set up processing coordinator
   - Configure environment variables

4. **Frontend Deployment**:
   - Build and deploy React application
   - Configure with backend API URL
   - Set up static file hosting

### 6.2 Testing Plan

1. **Backend Testing**:
   - API endpoint tests
   - Processing workflow tests
   - Security tests

2. **Frontend Testing**:
   - Component tests
   - Integration tests
   - End-to-end tests

3. **Infrastructure Testing**:
   - GPU droplet creation tests
   - S3 event tests
   - End-to-end processing tests

## 7. Monitoring and Maintenance

1. **Logging**:
   - Centralized logging with ELK stack
   - Error tracking
   - Usage analytics

2. **Monitoring**:
   - Infrastructure monitoring
   - Application performance monitoring
   - Processing job monitoring

3. **Maintenance Plan**:
   - Regular security updates
   - Database maintenance
   - Backup and recovery testing

## 8. Implementation Timeline

| Phase | Description | Timeline |
|-------|-------------|----------|
| 1 | Repository setup and infrastructure | Week 1 |
| 2 | Backend core functionality | Weeks 2-3 |
| 3 | Processing coordinator | Weeks 3-4 |
| 4 | Frontend implementation | Weeks 4-6 |
| 5 | Integration and testing | Weeks 6-7 |
| 6 | Deployment and monitoring | Week 8 |

## 9. Next Steps

1. Create GitHub repository
2. Set up CPU droplet for hosting the web application and coordinator
3. Implement the backend API with FastAPI
4. Develop the processing coordinator
5. Create Terraform templates for GPU droplets
6. Implement the frontend with React and Material UI
7. Test the entire workflow
8. Deploy to production
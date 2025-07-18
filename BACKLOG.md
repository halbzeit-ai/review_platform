# Product Backlog

This document tracks features, improvements, and technical debt that need to be addressed in future development cycles.

## High Priority

### Data Integrity & User Management
- **Multi-User Project Management System**
  - Status: Critical - Data integrity issue identified
  - Description: Implement proper project-user relationship management
  - Current Issue: When a user is deleted, their projects (PDFs, results, analysis) remain orphaned. Re-registering the same user grants access to old projects.
  - Proposed Solution:
    - Create project-user association table (many-to-many relationship)
    - Allow multiple users per project (team collaboration)
    - Implement cascade deletion: when last user of a project is deleted, delete the project
    - Add project ownership and permission management
  - Tasks:
    - Design project-user association schema
    - Create migration for existing data
    - Implement project deletion cascade logic
    - Add user permission levels (owner, viewer, editor)
    - Update frontend to handle multi-user projects
    - Add project sharing/invitation functionality
  - Impact: Prevents data leakage and ensures proper project lifecycle management

### Security & Infrastructure
- **HTTPS Setup with Let's Encrypt**
  - Status: Postponed until domain DNS is configured
  - Description: Set up SSL certificates for secure HTTPS connections
  - Prerequisites: Domain name pointing to server IP
  - Tasks:
    - Install certbot and nginx plugin
    - Obtain SSL certificate for domain
    - Update nginx configuration for HTTPS
    - Configure automatic HTTP to HTTPS redirect
    - Set up automatic certificate renewal

### Email Deliverability
- **Fix Email Spam Classification**
  - Status: Active issue - Gmail marking verification emails as spam
  - Description: Improve email deliverability to avoid spam folders
  - Current Issue: Emails sent from IP address instead of proper domain
  - Solutions to investigate:
    - Use professional email service (SendGrid, Mailgun, AWS SES)
    - Set up SPF/DKIM records when domain is ready
    - Improve email content and headers
    - Consider using a dedicated sending domain

## Medium Priority

### AI Processing Workflow
- **GPU Processing Implementation**
  - Status: Not started
  - Description: Implement AI review generation using on-demand GPU instances
  - Tasks:
    - Set up GPU processing pipeline
    - Integrate with shared filesystem storage
    - Implement review result parsing and storage

### User Experience
- **Email Templates Localization**
  - Status: Not started
  - Description: Translate verification and welcome emails to German/English
  - Current: Only English email templates exist

### Notification System
- **Email Notifications for Review Workflow**
  - Status: Planned but not implemented
  - Description: Send notifications for review status updates
  - Tasks:
    - GP notification when new deck uploaded
    - Startup notification when review completed
    - Q&A system notifications

## Low Priority

### Code Quality
- **Frontend ESLint Warnings**
  - Status: Build warnings present
  - Description: Clean up unused variables and missing dependencies
  - Files affected: LanguageSwitcher.js, GPDashboard.js, Register.js, etc.

- **Advanced MyPy Type Safety Issues**
  - Status: Deferred - complex refactoring needed
  - Description: Fix remaining mypy type checking issues for better type safety
  - Current: ~25 remaining errors after quick fixes completed
  - Impact: Medium - improves IDE support and catches potential runtime errors
  - Tasks:
    - **SQLAlchemy Column Assignment Issues** (15+ errors)
      - Fix incompatible assignment errors between Column types and values
      - Files: auth.py, documents.py, config.py, healthcare_templates.py
      - Example: `user.email = "new_email"` where email is Column[str]
      - Solution: Use proper SQLAlchemy ORM patterns or update to newer syntax
    - **Database Query Result Type Handling** (5+ errors)
      - Fix `Result[Any]` missing attributes like `rowcount`, `lastrowid`
      - Files: internal.py, healthcare_templates.py
      - Solution: Use proper result type annotations or raw SQL with text()
    - **Test Environment Import Issues** (3+ errors)
      - Cannot find pytest imports in test files
      - Files: All test files in backend/tests/
      - Solution: Create separate test requirements or configure mypy for test environment

### Features
- **User Profile Management**
  - Status: Not started
  - Description: Allow users to update profile information
  - Tasks:
    - Profile editing page
    - Password change functionality
    - Account deletion (self-service)

### Monitoring
- **Application Monitoring**
  - Status: Not implemented
  - Description: Add logging, metrics, and error tracking
  - Tools to consider: Sentry, Prometheus, Grafana

## Technical Debt

### Database
- **Migration to PostgreSQL**
  - Status: Planned for production scaling
  - Description: Move from SQLite to PostgreSQL for better performance
  - Current: Using SQLite for development

### Testing
- **Test Coverage**
  - Status: Minimal testing
  - Description: Add comprehensive test suite
  - Tasks:
    - Unit tests for backend services
    - Integration tests for API endpoints
    - Frontend component tests
    - End-to-end testing

---

## Completed Items

### ✅ Dynamic Polar Plot Results Visualization (2025-07-18)
- Implemented radar chart for healthcare template scoring
- Dynamic dimension mapping from template chapters
- Professional investment analysis styling
- Replaced linear progress bars with interactive polar plots
- Support for both healthcare templates and legacy scoring formats
- Enhanced text formatting with proper markdown handling
- Reduced excessive positive visual indicators for balanced analysis tone

### ✅ MyPy Type Safety - Quick Fixes (2025-07-18)
- Fixed 70% of mypy type checking errors (88 → 25 errors)
- Added missing type stubs for external libraries
- Migrated SQLAlchemy from declarative_base to DeclarativeBase
- Fixed Optional type annotation issues
- Improved IDE support and type safety
- Enhanced deployment automation with type checking

### ✅ Production Deployment Automation (2025-07-18)
- Created comprehensive deployment script with dry-run capability
- Fixed npm dependency resolution issues for production
- Added automated type checking to deployment pipeline
- Enhanced documentation with installation guides
- Implemented safe deployment with data protection guarantees

### ✅ Multilingual Support (2025-07-13)
- Implemented German/English internationalization
- German set as default language
- Language switcher component
- Backend language preference storage

### ✅ User Management (2025-07-13)
- GP dashboard user deletion functionality
- Confirmation dialogs for dangerous operations
- Enhanced error handling and debugging

### ✅ Email Verification System (2025-07-10)
- User registration with email verification
- Verification token system
- Resend verification functionality

### ✅ File Upload System (2025-07-10)
- PDF upload with size validation (up to 50MB)
- Shared filesystem integration
- Client-side file validation
# User Management System

## Overview

The platform supports two user types with distinct workflows:
- **General Partners (GPs)**: Investment professionals who evaluate startups
- **Startup Users**: Company representatives who upload documents and receive feedback

## User Registration & Authentication

### GP Registration
GPs are invited by existing GPs through the invitation system:

1. **Invitation Process**:
   - Existing GP sends invitation via `/api/auth/invite-gp`
   - System creates user account with temporary password
   - Invitation email sent with verification link and temporary credentials
   - GP must verify email and change password on first login

2. **Password Requirements**:
   - 8-128 characters long
   - At least 3 of: lowercase, uppercase, numbers, special characters
   - Not a common password
   - No sequential characters (123, abc, etc.)
   - No more than 2 repeated characters

### Startup User Registration  
Startup users are invited to specific projects:

1. **Project Invitation Workflow**:
   - GP invites startup user to a project via `ProjectInvitationManager`
   - Invitation email sent with project-specific signup link
   - User completes registration with company details and secure password
   - **Auto-login**: User is automatically logged in and redirected to upload tab
   - No forced password change required (streamlined UX)

2. **Invitation Acceptance Flow**:
   ```
   Invitation Email → Accept & Set Password → Auto-Login → Upload Tab
   ```

## Password Management

### Password Changes
- **Voluntary Changes**: Users can change passwords anytime via profile
- **Reset Flow**: Forgot password → Email token → Secure reset form
- **Forced Changes**: GPs may require password changes (configurable)

### Security Features
- **Time-limited tokens**: All reset/verification tokens expire
- **Hashed storage**: All tokens are hashed in database
- **Email verification**: Required for all new accounts
- **JWT authentication**: 8-day token validity for regular users

## User Deletion

### GP-Only Operation
Only General Partners can delete users via `/api/auth/delete-user`:

### Deletion Process
1. **Safety Checks**: Prevents deletion of users with active projects
2. **Cascading Cleanup**:
   - Legacy pitch deck system data (reviews, questions, decks)
   - Project system data (members, invitations, documents)
   - Preserves projects by unlinking user references
3. **Audit Trail**: Logs all deletion activities

### What Gets Deleted
- ✅ User account and authentication data
- ✅ Legacy system: pitch decks, reviews, questions
- ✅ Project memberships and invitations
- ✅ Personal data and preferences
- ❌ Projects themselves (preserved)
- ❌ Documents (unlinked but preserved)

## Multi-Language Support

### Available Languages
- **English (en)**: Default
- **German (de)**: Full translation support

### Email Localization
- Registration confirmations
- Password reset emails  
- Project invitations
- Welcome messages

All emails respect user's `preferred_language` setting.

## API Endpoints

### Authentication
- `POST /api/auth/register` - Startup user registration
- `POST /api/auth/login` - User login
- `POST /api/auth/change-password` - Password changes
- `POST /api/auth/forgot-password` - Password reset request
- `POST /api/auth/reset-password` - Complete password reset
- `GET /api/auth/verify-email` - Email verification
- `DELETE /api/auth/delete-user` - User deletion (GP only)

### GP Management  
- `POST /api/auth/invite-gp` - Invite new GP
- `GET /api/auth/users` - List all users (GP only)
- `GET /api/auth/pending-invitations` - View pending invitations

### Project Invitations
- Project-specific invitation system via `ProjectInvitationManager`
- Automatic project membership assignment
- Direct redirect to project upload interface

## Security Considerations

### Password Security
- OWASP-compliant password requirements
- Real-time validation feedback
- Common password blacklist
- Pattern detection (sequential, repeated characters)

### Email Security  
- SPF/DKIM friendly headers
- Gmail-optimized HTML structure
- Bounce handling and retry logic
- Time-limited verification tokens

### Session Management
- JWT-based authentication
- Configurable token expiry
- Automatic session cleanup
- Cross-device compatibility
# Project Management System

## Overview

The platform uses a comprehensive project-based system that replaces the legacy pitch deck approach. Projects serve as containers for:
- Company information and metadata
- Document uploads and processing
- Team member collaboration  
- Funding journey tracking
- Investment analysis workflow

## Project Lifecycle

### Project Creation
Projects can be created by:
1. **GP Initiative**: GPs create projects and invite startup teams
2. **Migration**: Legacy pitch decks automatically migrated to projects
3. **Dojo Experiments**: Test projects created from experimental data

### Project States
- **Active Projects**: Have members or pending invitations
- **Orphaned Projects**: No members, no pending invitations, but contain data
- **Test Projects**: Created from dojo/experimental data (`is_test = true`)

## Project Structure

### Core Data
```sql
projects:
- id (Primary Key)
- company_id (Unique identifier) 
- project_name (Display name)
- funding_round (Series A, B, C, etc.)
- funding_sought (Amount)
- healthcare_sector_id (Classification)
- company_offering (Business description)
- is_active (Status flag)
- is_test (Test data flag)
- project_metadata (JSON - flexible data storage)
```

### Associated Data
- **project_documents**: Uploaded files (pitch decks, financials, etc.)
- **project_members**: Team access control
- **project_invitations**: Pending member invites
- **project_stages**: 14-stage funding journey tracking

## Member Management

### Invitation System
1. **GP sends invitation** to startup email
2. **Invitation email** with project context and signup link
3. **User registration** with company details and password
4. **Automatic membership** assignment to project
5. **Direct redirect** to project upload interface

### Access Control
- **Project-based permissions**: Users access specific projects they're members of
- **Project membership verification**: All access requires active project membership
- **GP admin access**: Full access to all projects for management

### Membership Types  
- **Project Owner**: Creator of the project
- **Team Members**: Invited collaborators
- **GP Observers**: Investment team with evaluation access

## Orphaned Projects

### Definition
Projects that have:
- ✅ No active members
- ✅ No pending invitations  
- ✅ But contain valuable data (documents, analysis, etc.)

### Common Causes
1. **User deletion**: Last project member was deleted
2. **Failed invitations**: All invites expired or rejected
3. **Data migration**: Legacy system conversion artifacts
4. **Cleanup operations**: Bulk user management side effects

### Management
Orphaned projects are displayed in GP Dashboard with:
- **Company identification**
- **Document count**  
- **User email history** (from deleted users)
- **Recovery options**: "Open Project", "Invite Person", "Delete Project"

### Recovery Process
GPs can recover orphaned projects by:
1. **Direct access**: "Open Project" for immediate evaluation
2. **Re-invitation**: Send new invites to startup team
3. **Data preservation**: All analysis and documents remain intact

## Project Deletion

### Comprehensive Deletion System
**DESTRUCTIVE OPERATION** - Permanently removes all project data:

### What Gets Deleted
1. **Physical Files**: All uploaded documents from shared filesystem
2. **Project Data**: Documents, members, invitations, stages
3. **Computed Results**: Reviews, analysis, extraction results, visual cache
4. **Associated Users**: Startup users who only belonged to this project
5. **Database References**: Complete cleanup of all related data

### Safety Features
- **GP-Only Access**: Only General Partners can delete projects
- **Confirmation Required**: Must type "DELETE" exactly to proceed
- **Detailed Warning**: Shows comprehensive list of what will be removed
- **Transaction Safety**: Uses PostgreSQL savepoints for fault tolerance
- **Audit Logging**: Detailed statistics on what was actually deleted

### Deletion Process
```python
# Fault-tolerant deletion with savepoints
1. Verify GP permissions
2. Delete physical files from filesystem
3. Find users to delete (safety checks)
4. Delete computed results (with savepoints)
5. Delete project-specific data (dependency order)
6. Delete isolated users
7. Delete project record
8. Commit transaction with detailed statistics
```

### Error Handling
- **Savepoint-based recovery**: Individual operation failures don't abort entire deletion
- **Comprehensive logging**: Track exactly what succeeded/failed
- **Graceful degradation**: Core deletion proceeds even if cleanup operations fail

## API Endpoints

### Project Management
- `GET /api/project-management/all-projects` - List all projects (GP only)
- `GET /api/project-management/my-projects` - User's projects (Startup only)
- `GET /api/project-management/projects/{id}` - Project details
- `DELETE /api/project-management/projects/{id}` - Delete project (GP only)

### Orphaned Projects
- `GET /api/project-management/orphaned-projects` - List orphaned projects (GP only)

### Project Documents
- `GET /api/project-management/projects/{id}/documents` - Project documents
- `POST /api/robust/documents/upload` - Upload to project

### Project Members
- Project invitation system via frontend `ProjectInvitationManager`
- Automatic membership assignment on invitation acceptance

## Dojo Integration

### Test Projects
Dojo experiments create test projects with:
- `is_test = true` flag
- `project_metadata.created_from_experiment = "true"`
- Company IDs like "dojo", experimental names
- Full project functionality for testing

### Bulk Operations
- **Cleanup test data**: Remove experimental projects while preserving core experiments
- **Mass deletion**: Filter and delete multiple test projects
- **Data regeneration**: Recreate projects from experiment data

## Clean Architecture System

### Project-Centric Design
All data now flows through the project-centric architecture:
```sql
-- Core structure:
projects (container for all related data)
project_documents (all uploaded documents)
project_members (user access control)
project_stages (funding journey tracking)
```

### Data Structure
- **Clean architecture**: All data uses project-centric model
- **No legacy dependencies**: Removed pitch_decks table references
- **Simplified access**: Single consistent interface for all operations

## Best Practices

### For GPs
1. **Regular cleanup**: Monitor orphaned projects, recover or delete as appropriate
2. **Invitation management**: Use meaningful project names and clear invitations
3. **Access control**: Carefully manage who has project access
4. **Data retention**: Consider data value before permanent deletion

### For Startups  
1. **Team coordination**: Ensure all team members accept invitations
2. **Document organization**: Use clear file names and document types
3. **Regular updates**: Keep project information current
4. **Communication**: Respond to GP requests and invitations promptly

### System Maintenance
1. **Monitor orphaned projects**: Regular cleanup prevents data accumulation
2. **User lifecycle management**: Proper user deletion to avoid orphaned data
3. **Storage monitoring**: Track document storage usage across projects
4. **Performance optimization**: Regular database maintenance for project queries
# Database Migration Scripts

This directory contains scripts for database migrations and updates that need to be run on the production server.

## add_company_offering_prompt.py

Adds the company_offering prompt to the pipeline_prompts table in PostgreSQL. This prompt is extracted from the pitch_deck_analyzer.py file and includes the complete role context.

### Usage on Production Server:

1. **Navigate to backend directory**:
   ```bash
   cd /opt/review-platform/backend
   ```

2. **Run the script** (uses FastAPI database configuration):
   ```bash
   python scripts/add_company_offering_prompt.py
   ```

   The script automatically uses the same database configuration as the FastAPI application (from settings and .env file).

### What it does:

- Connects to PostgreSQL database
- Checks if `company_offering` prompt already exists
- If exists: Updates the prompt text
- If not exists: Inserts new prompt with the complete text from pitch_deck_analyzer.py
- Verifies the operation was successful

### The prompt being added:

```
You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck. Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company.
```

This prompt combines the role context with the offering extraction task, matching exactly what's used in the GPU processing pipeline.

### Requirements:

- Python 3.x
- FastAPI application dependencies (sqlalchemy, pydantic-settings)
- Access to PostgreSQL database via application configuration

### Safety:

- Script uses parameterized queries to prevent SQL injection
- Checks for existing prompts before inserting
- Provides detailed logging of operations
- Uses database transactions for consistency
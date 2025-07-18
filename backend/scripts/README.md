# Database Migration Scripts

This directory contains scripts for database migrations and updates that need to be run on the production server.

## add_company_offering_prompt.py

Adds the company_offering prompt to the pipeline_prompts table in PostgreSQL. This prompt is extracted from the pitch_deck_analyzer.py file and includes the complete role context.

### Usage on Production Server:

1. **Set environment variables** (if not already configured):
   ```bash
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=review_platform
   export DB_USER=postgres
   export DB_PASSWORD=your_password
   ```

2. **Run the script**:
   ```bash
   cd /opt/review-platform/backend
   python scripts/add_company_offering_prompt.py
   ```

3. **Alternative with direct environment variables**:
   ```bash
   DB_HOST=localhost DB_NAME=review_platform DB_USER=postgres DB_PASSWORD=your_password python scripts/add_company_offering_prompt.py
   ```

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
- psycopg2 (PostgreSQL adapter)
- Access to PostgreSQL database

### Safety:

- Script uses parameterized queries to prevent SQL injection
- Checks for existing prompts before inserting
- Provides detailed logging of operations
- Uses database transactions for consistency
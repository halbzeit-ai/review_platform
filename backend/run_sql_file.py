#!/usr/bin/env python3
"""
SQL file executor - runs SQL queries from a file using the database connection
"""

import sys
import os
from sqlalchemy import text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal

def run_sql_file(sql_file_path: str):
    """Run all SQL queries from a file"""
    if not os.path.exists(sql_file_path):
        print(f"❌ SQL file not found: {sql_file_path}")
        return False
    
    print(f"🔧 Running SQL file: {sql_file_path}")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split queries by semicolon and remove comments/empty lines
        queries = []
        current_query = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue
            
            current_query.append(line)
            
            # If line ends with semicolon, it's end of query
            if line.endswith(';'):
                query_text = ' '.join(current_query)
                if query_text.strip():
                    queries.append(query_text)
                current_query = []
        
        # Add remaining query if any
        if current_query:
            query_text = ' '.join(current_query)
            if query_text.strip():
                queries.append(query_text)
        
        print(f"Found {len(queries)} SQL queries to execute\n")
        
        # Execute each query
        for i, query in enumerate(queries, 1):
            print(f"🔍 Query {i}:")
            print(f"   {query[:100]}{'...' if len(query) > 100 else ''}")
            print("-" * 60)
            
            try:
                result = db.execute(text(query))
                
                if query.strip().upper().startswith('SELECT'):
                    rows = result.fetchall()
                    if rows:
                        # Print column headers
                        columns = result.keys()
                        header = " | ".join(f"{col:<20}" for col in columns)
                        print(header)
                        print("-" * len(header))
                        
                        # Print rows
                        for row in rows:
                            row_data = " | ".join(f"{str(val):<20}" for val in row)
                            print(row_data)
                        
                        print(f"\nFound {len(rows)} rows")
                    else:
                        print("No results found")
                else:
                    print(f"Query executed successfully. Rows affected: {result.rowcount}")
                    db.commit()
                
            except Exception as e:
                print(f"❌ Query {i} failed: {e}")
                continue
            
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to run SQL file: {e}")
        return False
        
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python run_sql_file.py <sql_file_path>")
        print("")
        print("Example:")
        print("  python run_sql_file.py archive/sql/schema_checks/investigate_visual_analysis_format.sql")
        sys.exit(1)
    
    sql_file_path = sys.argv[1]
    success = run_sql_file(sql_file_path)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Generate complete SQL schema from development database
Export actual table creation statements
"""

import psycopg2
import sys

def export_complete_schema():
    """Export complete database schema as SQL"""
    
    dev_conn_str = "postgresql://dev_user:!dev_Halbzeit1024@65.108.32.143:5432/review_dev"
    
    try:
        print("Connecting to development database...")
        dev_conn = psycopg2.connect(dev_conn_str)
        dev_cur = dev_conn.cursor()
        
        # Get all tables
        dev_cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        tables = [row[0] for row in dev_cur.fetchall()]
        
        print(f"Found {len(tables)} tables in development")
        
        sql_file = "/opt/review-platform-dev/scripts/complete_production_schema.sql"
        with open(sql_file, 'w') as f:
            f.write("-- Complete production database schema\n")
            f.write("-- Generated from development database\n\n")
            
            for table in tables:
                if table == 'users':
                    continue  # Skip users table as it already exists
                    
                print(f"Exporting table: {table}")
                
                # Get table structure
                dev_cur.execute(f"""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' 
                    ORDER BY ordinal_position
                """)
                
                columns = dev_cur.fetchall()
                
                f.write(f"-- Table: {table}\n")
                f.write(f"CREATE TABLE IF NOT EXISTS {table} (\n")
                
                column_defs = []
                for col_name, data_type, max_length, nullable, default in columns:
                    col_def = f"    {col_name} "
                    
                    # Map data types
                    if data_type == 'integer':
                        if 'serial' in (default or ''):
                            col_def += "SERIAL"
                        else:
                            col_def += "INTEGER"
                    elif data_type == 'character varying':
                        if max_length:
                            col_def += f"VARCHAR({max_length})"
                        else:
                            col_def += "VARCHAR(255)"
                    elif data_type == 'text':
                        col_def += "TEXT"
                    elif data_type == 'boolean':
                        col_def += "BOOLEAN"
                    elif data_type == 'timestamp without time zone':
                        col_def += "TIMESTAMP"
                    elif data_type == 'numeric':
                        col_def += "NUMERIC"
                    elif data_type == 'ARRAY':
                        col_def += "INTEGER[]"
                    else:
                        col_def += data_type.upper()
                    
                    # Handle constraints
                    if nullable == 'NO':
                        col_def += " NOT NULL"
                    
                    if default:
                        if 'nextval' in default:
                            # Skip serial defaults
                            pass
                        elif default == 'CURRENT_TIMESTAMP':
                            col_def += " DEFAULT CURRENT_TIMESTAMP"
                        elif default in ('true', 'false'):
                            col_def += f" DEFAULT {default}"
                        else:
                            col_def += f" DEFAULT {default}"
                    
                    column_defs.append(col_def)
                
                f.write(",\n".join(column_defs))
                f.write("\n);\n\n")
                
                # Get primary key
                dev_cur.execute(f"""
                    SELECT column_name 
                    FROM information_schema.key_column_usage k
                    JOIN information_schema.table_constraints t ON k.constraint_name = t.constraint_name
                    WHERE t.table_name = '{table}' AND t.constraint_type = 'PRIMARY KEY'
                """)
                pk_cols = dev_cur.fetchall()
                
                if pk_cols:
                    pk_columns = ", ".join([col[0] for col in pk_cols])
                    f.write(f"ALTER TABLE {table} ADD PRIMARY KEY ({pk_columns});\n\n")
        
        print(f"✅ Complete schema exported to: {sql_file}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        if 'dev_conn' in locals():
            dev_conn.close()

if __name__ == "__main__":
    export_complete_schema()
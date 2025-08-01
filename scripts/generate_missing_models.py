#!/usr/bin/env python3
"""
Generate missing SQLAlchemy models from development database
This fixes the code vs database drift issue
"""

import psycopg2
import sys
from collections import defaultdict

def generate_sqlalchemy_models():
    """Generate SQLAlchemy model classes from actual database schema"""
    
    dev_conn_str = "postgresql://dev_user:!dev_Halbzeit1024@65.108.32.143:5432/review_dev"
    
    # Tables that already exist in models.py (skip these)
    existing_models = {
        'users', 'pitch_decks', 'reviews', 'questions', 'model_configs', 
        'answers', 'projects', 'project_stages', 'project_documents', 
        'project_interactions', 'pipeline_prompts', 'visual_analysis_cache', 
        'extraction_experiments'
    }
    
    try:
        print("Connecting to development database...")
        dev_conn = psycopg2.connect(dev_conn_str)
        dev_cur = dev_conn.cursor()
        
        # Get all tables
        dev_cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        all_tables = [row[0] for row in dev_cur.fetchall()]
        
        # Find missing tables
        missing_tables = [t for t in all_tables if t not in existing_models]
        print(f"Found {len(missing_tables)} missing model tables:")
        for table in missing_tables:
            print(f"  - {table}")
        
        models_code = []
        models_code.append("# Generated SQLAlchemy models for missing tables")
        models_code.append("# Add these to app/db/models.py")
        models_code.append("")
        
        # Get foreign key relationships
        foreign_keys = defaultdict(list)
        dev_cur.execute("""
            SELECT 
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
        """)
        
        for table, column, ref_table, ref_column in dev_cur.fetchall():
            foreign_keys[table].append((column, ref_table, ref_column))
        
        # Generate models for each missing table
        for table in missing_tables:
            class_name = ''.join(word.capitalize() for word in table.split('_'))
            
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
            
            models_code.append(f"class {class_name}(Base):")
            models_code.append(f'    __tablename__ = "{table}"')
            models_code.append("")
            
            # Generate columns
            for col_name, data_type, max_length, nullable, default in columns:
                col_def = f"    {col_name} = Column("
                
                # Map data types to SQLAlchemy types
                if data_type == 'integer':
                    if col_name == 'id' or 'serial' in (default or ''):
                        col_def += "Integer, primary_key=True"
                    else:
                        col_def += "Integer"
                elif data_type == 'character varying':
                    if max_length:
                        col_def += f"String({max_length})"
                    else:
                        col_def += "String"
                elif data_type == 'text':
                    col_def += "Text"
                elif data_type == 'boolean':
                    col_def += "Boolean"
                elif data_type == 'timestamp without time zone':
                    col_def += "DateTime"
                elif data_type == 'numeric':
                    col_def += "Numeric"
                elif data_type == 'ARRAY':
                    col_def += "postgresql.ARRAY(Integer)"
                else:
                    col_def += f"String  # {data_type}"
                
                # Add constraints
                if nullable == 'NO' and col_name != 'id':
                    col_def += ", nullable=False"
                
                # Add foreign keys
                fk_info = None
                for fk_col, ref_table, ref_col in foreign_keys.get(table, []):
                    if fk_col == col_name:
                        fk_info = (ref_table, ref_col)
                        break
                        
                if fk_info:
                    col_def += f', ForeignKey("{fk_info[0]}.{fk_info[1]}")'
                
                # Add indexes for common patterns
                if col_name in ['id', 'email', 'name', 'stage_name'] or col_name.endswith('_id'):
                    col_def += ", index=True"
                
                # Add defaults
                if default:
                    if 'CURRENT_TIMESTAMP' in (default or ''):
                        col_def += ", default=datetime.utcnow"
                    elif default in ('true', 'false'):
                        col_def += f", default={default.capitalize()}"
                
                col_def += ")"
                models_code.append(col_def)
            
            models_code.append("")
        
        # Write to file
        output_file = "/opt/review-platform-dev/scripts/missing_models.py"
        with open(output_file, 'w') as f:
            f.write("\\n".join(models_code))
        
        print(f"✅ Generated models for {len(missing_tables)} tables")
        print(f"✅ Models written to: {output_file}")
        print("\\n📋 Next steps:")
        print("1. Review the generated models")
        print("2. Add them to app/db/models.py")
        print("3. Add necessary imports (DateTime, postgresql, etc.)")
        print("4. Test schema creation")
        
    except Exception as e:
        print(f"❌ Model generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        if 'dev_conn' in locals():
            dev_conn.close()

if __name__ == "__main__":
    generate_sqlalchemy_models()
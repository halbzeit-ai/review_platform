#!/usr/bin/env python3
"""
SQL File Analyzer - Categorizes SQL files by purpose and usage frequency
Helps identify which SQL files are still needed vs obsolete one-time migrations
"""

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

def get_git_info(file_path):
    """Get git information for a file"""
    try:
        # Get last commit date
        result = subprocess.run([
            'git', 'log', '-1', '--format=%ci', '--', file_path
        ], capture_output=True, text=True, cwd=os.path.dirname(file_path))
        
        last_commit = result.stdout.strip() if result.returncode == 0 else None
        
        # Get commit count
        result = subprocess.run([
            'git', 'log', '--oneline', '--', file_path
        ], capture_output=True, text=True, cwd=os.path.dirname(file_path))
        
        commit_count = len(result.stdout.strip().split('\n')) if result.returncode == 0 and result.stdout.strip() else 0
        
        # Get creation date (first commit)
        result = subprocess.run([
            'git', 'log', '--reverse', '--format=%ci', '--', file_path
        ], capture_output=True, text=True, cwd=os.path.dirname(file_path))
        
        first_commit = result.stdout.strip().split('\n')[0] if result.returncode == 0 and result.stdout.strip() else None
        
        return {
            'last_commit': last_commit,
            'first_commit': first_commit,
            'commit_count': commit_count
        }
    except Exception:
        return {'last_commit': None, 'first_commit': None, 'commit_count': 0}

def analyze_sql_content(file_path):
    """Analyze SQL file content to determine purpose and type"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'purpose': 'unknown',
            'type': 'unknown',
            'operations': [],
            'tables_affected': [],
            'is_migration': False,
            'is_schema_change': False,
            'is_data_change': False,
            'is_one_time': False,
            'is_reusable': False,
            'destructive': False
        }
        
        content_lower = content.lower()
        filename = os.path.basename(file_path).lower()
        
        # Detect SQL operations
        operations = []
        if 'create table' in content_lower or 'create index' in content_lower:
            operations.append('CREATE')
            analysis['is_schema_change'] = True
        if 'alter table' in content_lower or 'add column' in content_lower:
            operations.append('ALTER')
            analysis['is_schema_change'] = True
        if 'drop table' in content_lower or 'drop column' in content_lower:
            operations.append('DROP')
            analysis['is_schema_change'] = True
            analysis['destructive'] = True
        if 'insert into' in content_lower:
            operations.append('INSERT')
            analysis['is_data_change'] = True
        if 'update' in content_lower and 'set' in content_lower:
            operations.append('UPDATE')
            analysis['is_data_change'] = True
        if 'delete from' in content_lower:
            operations.append('DELETE')
            analysis['is_data_change'] = True
            analysis['destructive'] = True
        if 'select' in content_lower:
            operations.append('SELECT')
        
        analysis['operations'] = operations
        
        # Extract table names
        table_patterns = [
            r'(?:from|into|table|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'alter\s+table\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'create\s+table\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'drop\s+table\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        ]
        
        tables = set()
        for pattern in table_patterns:
            matches = re.findall(pattern, content_lower)
            tables.update(matches)
        
        # Filter out common SQL keywords that might be matched
        sql_keywords = {'values', 'where', 'select', 'from', 'into', 'table', 'join', 'inner', 'left', 'right', 'on', 'as'}
        analysis['tables_affected'] = list(tables - sql_keywords)
        
        # Categorize by filename patterns
        if any(word in filename for word in ['migration', 'migrate', 'schema', 'upgrade', 'version']):
            analysis['is_migration'] = True
            analysis['purpose'] = 'migration'
            analysis['type'] = 'migration'
            analysis['is_one_time'] = True
        
        if any(word in filename for word in ['seed', 'data', 'populate', 'init', 'setup']):
            analysis['purpose'] = 'data_seeding'
            analysis['type'] = 'data'
            analysis['is_one_time'] = True
        
        if any(word in filename for word in ['fix', 'repair', 'cleanup', 'correct']):
            analysis['purpose'] = 'fix'
            analysis['type'] = 'fix'
            analysis['is_one_time'] = True
        
        if any(word in filename for word in ['add', 'create', 'new']):
            analysis['purpose'] = 'addition'
            analysis['type'] = 'schema'
        
        if any(word in filename for word in ['template', 'standard', 'default']):
            analysis['purpose'] = 'template_setup'
            analysis['type'] = 'data'
        
        # Determine if reusable
        if any(indicator in content_lower for indicator in ['-- reusable', '-- utility', '-- helper']):
            analysis['is_reusable'] = True
        elif analysis['is_migration'] or 'one-time' in content_lower or 'temporary' in content_lower:
            analysis['is_one_time'] = True
        
        return analysis
        
    except Exception as e:
        return {'error': str(e)}

def categorize_sql_files():
    """Categorize all SQL files in the backend directory and subdirectories"""
    backend_dir = Path('.')
    sql_files = []
    
    # Find all SQL files
    for sql_file in backend_dir.rglob('*.sql'):
        if sql_file.name.startswith('.'):
            continue
            
        file_path = str(sql_file)
        
        # Get file stats
        stat = sql_file.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime)
        
        # Get git info
        git_info = get_git_info(file_path)
        
        # Analyze content
        content_analysis = analyze_sql_content(file_path)
        
        sql_files.append({
            'name': sql_file.name,
            'path': file_path,
            'relative_path': str(sql_file.relative_to(backend_dir)),
            'size': size,
            'modified': modified,
            'git_info': git_info,
            'analysis': content_analysis
        })
    
    return sql_files

def print_sql_categories(sql_files):
    """Print SQL files organized by categories"""
    
    # Categorize files
    categories = {
        'active_migrations': [],
        'historical_migrations': [],
        'data_seeds': [],
        'one_time_fixes': [],
        'schema_templates': [],
        'obsolete_candidates': [],
        'unknown': []
    }
    
    for sql_file in sql_files:
        analysis = sql_file['analysis']
        git_info = sql_file['git_info']
        
        if analysis.get('is_migration'):
            # Recent migrations (last 30 days) vs historical
            if git_info.get('last_commit'):
                try:
                    last_commit_date = datetime.fromisoformat(git_info['last_commit'].replace(' ', 'T'))
                    days_ago = (datetime.now() - last_commit_date).days
                    if days_ago <= 30:
                        categories['active_migrations'].append(sql_file)
                    else:
                        categories['historical_migrations'].append(sql_file)
                except:
                    categories['historical_migrations'].append(sql_file)
            else:
                categories['historical_migrations'].append(sql_file)
        elif analysis.get('purpose') == 'data_seeding' or analysis.get('purpose') == 'template_setup':
            categories['data_seeds'].append(sql_file)
        elif analysis.get('purpose') == 'fix' or analysis.get('is_one_time'):
            if git_info.get('commit_count', 0) <= 2:
                categories['obsolete_candidates'].append(sql_file)
            else:
                categories['one_time_fixes'].append(sql_file)
        elif analysis.get('is_schema_change') and not analysis.get('is_migration'):
            categories['schema_templates'].append(sql_file)
        else:
            categories['unknown'].append(sql_file)
    
    # Print results
    print("=" * 80)
    print("SQL FILES ANALYSIS")
    print("=" * 80)
    print()
    
    def print_category(title, files_list, description):
        if not files_list:
            return
            
        print(f"🔶 {title}")
        print(f"   {description}")
        print("-" * 60)
        
        for sql_file in sorted(files_list, key=lambda x: x['name']):
            name = sql_file['name']
            analysis = sql_file['analysis']
            git_info = sql_file['git_info']
            
            print(f"📄 {sql_file['relative_path']}")
            print(f"   Purpose: {analysis.get('purpose', 'unknown')}")
            print(f"   Operations: {', '.join(analysis.get('operations', []))}")
            if analysis.get('tables_affected'):
                tables = analysis['tables_affected'][:3]  # Show first 3 tables
                tables_str = ', '.join(tables)
                if len(analysis['tables_affected']) > 3:
                    tables_str += f" (+{len(analysis['tables_affected'])-3} more)"
                print(f"   Tables: {tables_str}")
            print(f"   Size: {sql_file['size']} bytes")
            print(f"   Commits: {git_info['commit_count']}")
            if git_info['last_commit']:
                print(f"   Last modified: {git_info['last_commit'][:10]}")
            
            # Add warnings
            if analysis.get('destructive'):
                print("   ⚠️  DESTRUCTIVE - Contains DROP/DELETE operations")
            if analysis.get('is_one_time'):
                print("   📅 One-time use - candidate for archiving")
            if analysis.get('is_migration'):
                print("   🔄 Migration script")
            
            print()
        
        print()
    
    print_category(
        "RECENT MIGRATIONS (Last 30 days)", 
        categories['active_migrations'],
        "Recent schema/data migrations - keep for reference"
    )
    
    print_category(
        "HISTORICAL MIGRATIONS", 
        categories['historical_migrations'],
        "Older migration scripts - archive candidates"
    )
    
    print_category(
        "DATA SEEDS & TEMPLATES", 
        categories['data_seeds'],
        "Data population and template setup scripts"
    )
    
    print_category(
        "SCHEMA TEMPLATES", 
        categories['schema_templates'],
        "Reusable schema definition scripts"
    )
    
    print_category(
        "ONE-TIME FIXES", 
        categories['one_time_fixes'],
        "Specific data fixes and corrections"
    )
    
    print_category(
        "OBSOLETE CANDIDATES", 
        categories['obsolete_candidates'],
        "Low activity, one-time scripts - safe to archive"
    )
    
    print_category(
        "UNCLASSIFIED", 
        categories['unknown'],
        "SQL files that need manual review"
    )
    
    # Summary recommendations
    print("📋 RECOMMENDATIONS")
    print("=" * 40)
    print()
    
    archive_candidates = categories['historical_migrations'] + categories['obsolete_candidates'] + categories['one_time_fixes']
    if archive_candidates:
        print("🗂️  ARCHIVE CANDIDATES:")
        for sql_file in archive_candidates:
            print(f"   - {sql_file['relative_path']}")
        print()
    
    keep_files = categories['active_migrations'] + categories['data_seeds'] + categories['schema_templates']
    if keep_files:
        print("✅ KEEP (still useful):")
        for sql_file in keep_files:
            print(f"   - {sql_file['relative_path']}")
        print()
    
    if categories['unknown']:
        print("❓ MANUAL REVIEW NEEDED:")
        for sql_file in categories['unknown']:
            print(f"   - {sql_file['relative_path']}")
        print()

def main():
    """Main function"""
    print("SQL File Analyzer")
    print("Analyzing SQL files to determine which are still needed...")
    print()
    
    sql_files = categorize_sql_files()
    
    if not sql_files:
        print("No SQL files found in the backend directory.")
        return
    
    print_sql_categories(sql_files)
    
    print("💡 TIP: Create 'archive/sql/' folders and move obsolete scripts there")
    print("    Keep recent migrations and reusable templates in main directory")

if __name__ == "__main__":
    main()
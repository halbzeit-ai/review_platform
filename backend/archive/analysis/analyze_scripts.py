#!/usr/bin/env python3
"""
Script Analyzer - Categorizes backend scripts by purpose and usage frequency
Helps identify which scripts are still needed vs obsolete one-time use scripts
"""

import os
import re
import subprocess
from datetime import datetime, timedelta
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

def analyze_script_content(file_path):
    """Analyze script content to determine purpose and type"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Analyze content patterns
        analysis = {
            'docstring': '',
            'purpose': 'unknown',
            'type': 'unknown',
            'imports': [],
            'database_operations': False,
            'migration_related': False,
            'debug_related': False,
            'one_time_use': False,
            'reusable': False
        }
        
        # Extract docstring
        docstring_match = re.search(r'"""([^"]+)"""', content)
        if docstring_match:
            analysis['docstring'] = docstring_match.group(1).strip()
        
        # Detect imports
        imports = re.findall(r'^(?:from|import)\s+([^\s]+)', content, re.MULTILINE)
        analysis['imports'] = list(set(imports))
        
        # Categorize by filename and content
        filename = os.path.basename(file_path).lower()
        content_lower = content.lower()
        
        # Database operations
        if any(db_term in content_lower for db_term in ['sqlalchemy', 'sessionlocal', 'database', 'sql', 'query', 'execute']):
            analysis['database_operations'] = True
        
        # Migration related
        if any(term in filename for term in ['migration', 'migrate', 'schema', 'upgrade']):
            analysis['migration_related'] = True
            analysis['purpose'] = 'migration'
            analysis['type'] = 'migration'
        
        # Debug/analysis related
        if any(term in filename for term in ['debug', 'analyze', 'inspect', 'test', 'check']):
            analysis['debug_related'] = True
            analysis['purpose'] = 'debug/analysis'
            analysis['type'] = 'debug'
        
        # One-time use indicators
        one_time_indicators = [
            'cleanup', 'fix', 'repair', 'convert', 'import', 'export',
            'one-time', 'temporary', 'temp', 'quick', 'hotfix'
        ]
        if any(indicator in filename or indicator in content_lower for indicator in one_time_indicators):
            analysis['one_time_use'] = True
        
        # Reusable indicators
        reusable_indicators = [
            'def main', 'argparse', 'if __name__', 'class ', 'utility', 'helper', 'tool'
        ]
        if any(indicator in content_lower for indicator in reusable_indicators):
            analysis['reusable'] = True
        
        # Determine purpose based on content
        if 'migration' in content_lower or 'alter table' in content_lower:
            analysis['purpose'] = 'database_migration'
        elif 'cleanup' in content_lower or 'delete' in content_lower:
            analysis['purpose'] = 'cleanup'
        elif 'analyze' in content_lower or 'inspect' in content_lower:
            analysis['purpose'] = 'analysis'
        elif 'debug' in content_lower or 'test' in content_lower:
            analysis['purpose'] = 'debugging'
        elif 'import' in content_lower or 'export' in content_lower:
            analysis['purpose'] = 'data_management'
        
        return analysis
        
    except Exception as e:
        return {'error': str(e)}

def categorize_scripts():
    """Categorize all Python scripts in the backend directory"""
    backend_dir = Path('.')
    scripts = []
    
    # Find all Python files
    for py_file in backend_dir.glob('*.py'):
        if py_file.name.startswith('.'):
            continue
            
        file_path = str(py_file)
        
        # Get file stats
        stat = py_file.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime)
        
        # Get git info
        git_info = get_git_info(file_path)
        
        # Analyze content
        content_analysis = analyze_script_content(file_path)
        
        scripts.append({
            'name': py_file.name,
            'path': file_path,
            'size': size,
            'modified': modified,
            'git_info': git_info,
            'analysis': content_analysis
        })
    
    return scripts

def print_script_categories(scripts):
    """Print scripts organized by categories"""
    
    # Categorize scripts
    categories = {
        'core_app': [],
        'migrations': [],
        'cleanup_oneoff': [],
        'debug_analysis': [],
        'utilities_reusable': [],
        'obsolete_candidates': [],
        'unknown': []
    }
    
    for script in scripts:
        name = script['name']
        analysis = script['analysis']
        git_info = script['git_info']
        
        # Skip core app files
        if name.startswith('app/') or name in ['main.py', '__init__.py']:
            categories['core_app'].append(script)
        elif analysis.get('migration_related'):
            categories['migrations'].append(script)
        elif analysis.get('one_time_use') or 'cleanup' in analysis.get('purpose', ''):
            categories['cleanup_oneoff'].append(script)
        elif analysis.get('debug_related') or 'debug' in analysis.get('purpose', '') or 'analysis' in analysis.get('purpose', ''):
            categories['debug_analysis'].append(script)
        elif analysis.get('reusable') and not analysis.get('one_time_use'):
            categories['utilities_reusable'].append(script)
        elif git_info['commit_count'] <= 2 and analysis.get('one_time_use'):
            categories['obsolete_candidates'].append(script)
        else:
            categories['unknown'].append(script)
    
    # Print results
    print("=" * 80)
    print("BACKEND SCRIPT ANALYSIS")
    print("=" * 80)
    print()
    
    def print_category(title, scripts_list, description):
        if not scripts_list:
            return
            
        print(f"🔶 {title}")
        print(f"   {description}")
        print("-" * 60)
        
        for script in sorted(scripts_list, key=lambda x: x['name']):
            name = script['name']
            analysis = script['analysis']
            git_info = script['git_info']
            
            print(f"📄 {name}")
            if analysis.get('docstring'):
                print(f"   Purpose: {analysis['docstring'][:80]}...")
            print(f"   Type: {analysis.get('purpose', 'unknown')}")
            print(f"   Size: {script['size']} bytes")
            print(f"   Commits: {git_info['commit_count']}")
            if git_info['last_commit']:
                print(f"   Last modified: {git_info['last_commit'][:10]}")
            
            # Add recommendation
            if analysis.get('one_time_use'):
                print("   ⚠️  One-time use - consider archiving")
            elif analysis.get('reusable'):
                print("   ✅ Reusable utility - keep")
            
            print()
        
        print()
    
    print_category(
        "CORE APPLICATION FILES", 
        categories['core_app'],
        "Main application files - definitely keep"
    )
    
    print_category(
        "DATABASE MIGRATIONS", 
        categories['migrations'],
        "Schema and data migration scripts - keep for reference"
    )
    
    print_category(
        "REUSABLE UTILITIES", 
        categories['utilities_reusable'],
        "Scripts that can be used multiple times - keep"
    )
    
    print_category(
        "DEBUG & ANALYSIS TOOLS", 
        categories['debug_analysis'],
        "Debugging and analysis scripts - useful for troubleshooting"
    )
    
    print_category(
        "ONE-TIME CLEANUP SCRIPTS", 
        categories['cleanup_oneoff'],
        "Scripts for specific cleanup tasks - candidates for archiving"
    )
    
    print_category(
        "OBSOLETE CANDIDATES", 
        categories['obsolete_candidates'],
        "Low activity, one-time use scripts - likely safe to archive"
    )
    
    print_category(
        "UNCLASSIFIED", 
        categories['unknown'],
        "Scripts that need manual review"
    )
    
    # Summary recommendations
    print("📋 RECOMMENDATIONS")
    print("=" * 40)
    print()
    
    archive_candidates = categories['cleanup_oneoff'] + categories['obsolete_candidates']
    if archive_candidates:
        print("🗂️  ARCHIVE CANDIDATES (move to 'archive/' folder):")
        for script in archive_candidates:
            print(f"   - {script['name']}")
        print()
    
    keep_scripts = categories['utilities_reusable'] + categories['debug_analysis']
    if keep_scripts:
        print("✅ KEEP (still useful):")
        for script in keep_scripts:
            print(f"   - {script['name']}")
        print()
    
    if categories['unknown']:
        print("❓ MANUAL REVIEW NEEDED:")
        for script in categories['unknown']:
            print(f"   - {script['name']} (review purpose and usage)")
        print()

def main():
    """Main function"""
    print("Backend Script Analyzer")
    print("Analyzing Python scripts to determine which are still needed...")
    print()
    
    scripts = categorize_scripts()
    print_script_categories(scripts)
    
    print("💡 TIP: Create an 'archive/' folder and move obsolete scripts there")
    print("    This keeps them accessible but out of the main directory")

if __name__ == "__main__":
    main()
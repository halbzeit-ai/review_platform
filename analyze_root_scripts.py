#!/usr/bin/env python3
"""
Root Folder Script Analyzer - Categorizes Python and shell scripts by purpose and usage frequency
Helps identify which scripts are still needed vs obsolete one-time use scripts
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
        ], capture_output=True, text=True, cwd=os.path.dirname(file_path) or '.')
        
        last_commit = result.stdout.strip() if result.returncode == 0 else None
        
        # Get commit count
        result = subprocess.run([
            'git', 'log', '--oneline', '--', file_path
        ], capture_output=True, text=True, cwd=os.path.dirname(file_path) or '.')
        
        commit_count = len(result.stdout.strip().split('\n')) if result.returncode == 0 and result.stdout.strip() else 0
        
        # Get creation date (first commit)
        result = subprocess.run([
            'git', 'log', '--reverse', '--format=%ci', '--', file_path
        ], capture_output=True, text=True, cwd=os.path.dirname(file_path) or '.')
        
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
        
        analysis = {
            'docstring': '',
            'purpose': 'unknown',
            'type': 'unknown',
            'imports': [],
            'database_operations': False,
            'gpu_related': False,
            'deployment_related': False,
            'debug_related': False,
            'test_related': False,
            'migration_related': False,
            'one_time_use': False,
            'reusable': False,
            'has_main': False,
            'is_executable': False
        }
        
        filename = os.path.basename(file_path).lower()
        content_lower = content.lower()
        
        # Extract docstring
        docstring_match = re.search(r'["\'](["\'])\1\1(.*?)\1\1\1', content, re.DOTALL)
        if docstring_match:
            analysis['docstring'] = docstring_match.group(2).strip()
        
        # Check if executable
        analysis['is_executable'] = os.access(file_path, os.X_OK)
        
        # Check for main function
        analysis['has_main'] = 'if __name__ == "__main__"' in content or 'def main(' in content
        
        # Extract imports
        import_matches = re.findall(r'^(?:from\s+\S+\s+)?import\s+(.+)$', content, re.MULTILINE)
        for match in import_matches:
            analysis['imports'].extend([imp.strip() for imp in match.split(',')])
        
        # Categorize by filename patterns
        if any(word in filename for word in ['debug', 'test', 'check']):
            if 'test' in filename:
                analysis['test_related'] = True
                analysis['purpose'] = 'testing'
                analysis['type'] = 'test'
            elif 'debug' in filename:
                analysis['debug_related'] = True
                analysis['purpose'] = 'debugging'
                analysis['type'] = 'debug'
            elif 'check' in filename:
                analysis['purpose'] = 'validation'
                analysis['type'] = 'check'
        
        if any(word in filename for word in ['deploy', 'setup', 'install']):
            analysis['deployment_related'] = True
            analysis['purpose'] = 'deployment'
            analysis['type'] = 'deployment'
        
        if any(word in filename for word in ['migrate', 'migration', 'fix']):
            analysis['migration_related'] = True
            analysis['purpose'] = 'migration'
            analysis['type'] = 'migration'
        
        if any(word in filename for word in ['gpu', 'model', 'ai']):
            analysis['gpu_related'] = True
        
        # Analyze content patterns
        if any(pattern in content_lower for pattern in ['database', 'db', 'sql', 'sqlite', 'postgresql']):
            analysis['database_operations'] = True
        
        if any(pattern in content_lower for pattern in ['gpu', 'cuda', 'torch', 'tensorflow']):
            analysis['gpu_related'] = True
        
        # Determine if one-time use
        one_time_indicators = [
            'one-time', 'temporary', 'quick fix', 'hotfix',
            'migration', 'deploy', 'setup', 'install'
        ]
        if any(indicator in content_lower for indicator in one_time_indicators):
            analysis['one_time_use'] = True
        
        # Determine if reusable
        reusable_indicators = [
            'utility', 'helper', 'library', 'module', 'reusable',
            'class ', 'def ', 'function'
        ]
        if (analysis['has_main'] and 
            any(indicator in content_lower for indicator in reusable_indicators) and
            not analysis['one_time_use']):
            analysis['reusable'] = True
        
        return analysis
        
    except Exception as e:
        return {'error': str(e)}

def categorize_root_scripts():
    """Categorize all Python and shell scripts in the root directory"""
    root_dir = Path('.')
    script_files = []
    
    # Find all Python and shell scripts in root (not subdirectories)
    patterns = ['*.py', '*.sh']
    for pattern in patterns:
        for script_file in root_dir.glob(pattern):
            if script_file.is_file() and not script_file.name.startswith('.'):
                file_path = str(script_file)
                
                # Get file stats
                stat = script_file.stat()
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime)
                
                # Get git info
                git_info = get_git_info(file_path)
                
                # Analyze content
                content_analysis = analyze_script_content(file_path)
                
                script_files.append({
                    'name': script_file.name,
                    'path': file_path,
                    'extension': script_file.suffix,
                    'size': size,
                    'modified': modified,
                    'git_info': git_info,
                    'analysis': content_analysis
                })
    
    return script_files

def print_script_categories(script_files):
    """Print scripts organized by categories"""
    
    # Categorize files
    categories = {
        'deployment_scripts': [],
        'debug_testing': [],
        'migration_fixes': [],
        'gpu_processing': [],
        'database_tools': [],
        'obsolete_candidates': [],
        'active_utilities': [],
        'unknown': []
    }
    
    for script in script_files:
        analysis = script['analysis']
        git_info = script['git_info']
        
        if analysis.get('deployment_related'):
            categories['deployment_scripts'].append(script)
        elif analysis.get('debug_related') or analysis.get('test_related'):
            # Check if recent activity
            if git_info.get('commit_count', 0) <= 2:
                categories['obsolete_candidates'].append(script)
            else:
                categories['debug_testing'].append(script)
        elif analysis.get('migration_related'):
            categories['migration_fixes'].append(script)
        elif analysis.get('gpu_related'):
            categories['gpu_processing'].append(script)
        elif analysis.get('database_operations'):
            categories['database_tools'].append(script)
        elif analysis.get('reusable') and not analysis.get('one_time_use'):
            categories['active_utilities'].append(script)
        elif analysis.get('one_time_use') or git_info.get('commit_count', 0) <= 1:
            categories['obsolete_candidates'].append(script)
        else:
            categories['unknown'].append(script)
    
    # Print results
    print("=" * 80)
    print("ROOT FOLDER SCRIPTS ANALYSIS")
    print("=" * 80)
    print()
    
    def print_category(title, files_list, description):
        if not files_list:
            return
            
        print(f"🔶 {title}")
        print(f"   {description}")
        print("-" * 60)
        
        for script in sorted(files_list, key=lambda x: x['name']):
            name = script['name']
            analysis = script['analysis']
            git_info = script['git_info']
            
            print(f"📄 {name} ({script['extension']})")
            if analysis.get('docstring'):
                print(f"   Description: {analysis['docstring'][:100]}...")
            print(f"   Purpose: {analysis.get('purpose', 'unknown')}")
            print(f"   Size: {script['size']} bytes")
            print(f"   Commits: {git_info['commit_count']}")
            if git_info['last_commit']:
                print(f"   Last modified: {git_info['last_commit'][:10]}")
            
            # Add indicators
            if analysis.get('is_executable'):
                print("   🚀 Executable script")
            if analysis.get('has_main'):
                print("   🎯 Has main function - likely standalone tool")
            if analysis.get('one_time_use'):
                print("   📅 One-time use - candidate for archiving")
            if analysis.get('database_operations'):
                print("   🗄️  Database operations")
            if analysis.get('gpu_related'):
                print("   🖥️  GPU/AI related")
            if analysis.get('deployment_related'):
                print("   🚀 Deployment/setup script")
            
            print()
        
        print()
    
    print_category(
        "DEPLOYMENT & SETUP SCRIPTS", 
        categories['deployment_scripts'],
        "Scripts for deployment, setup, and infrastructure management"
    )
    
    print_category(
        "GPU & AI PROCESSING", 
        categories['gpu_processing'],
        "Scripts related to GPU processing and AI model management"
    )
    
    print_category(
        "DATABASE TOOLS", 
        categories['database_tools'],
        "Database management and migration tools"
    )
    
    print_category(
        "ACTIVE DEBUG/TESTING TOOLS", 
        categories['debug_testing'],
        "Actively maintained debugging and testing utilities"
    )
    
    print_category(
        "MIGRATION & FIX SCRIPTS", 
        categories['migration_fixes'],
        "Migration scripts and one-time fixes"
    )
    
    print_category(
        "ACTIVE UTILITIES", 
        categories['active_utilities'],
        "Reusable utility scripts that are still needed"
    )
    
    print_category(
        "OBSOLETE CANDIDATES", 
        categories['obsolete_candidates'],
        "Low activity scripts - likely safe to archive"
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
    
    archive_candidates = categories['obsolete_candidates'] + categories['migration_fixes']
    if archive_candidates:
        print("🗂️  ARCHIVE CANDIDATES:")
        for script in archive_candidates:
            print(f"   - {script['name']} ({script['analysis']['purpose']})")
        print()
    
    keep_files = (categories['deployment_scripts'] + categories['gpu_processing'] + 
                 categories['database_tools'] + categories['debug_testing'] + 
                 categories['active_utilities'])
    if keep_files:
        print("✅ KEEP (still useful):")
        for script in keep_files:
            print(f"   - {script['name']} ({script['analysis']['purpose']})")
        print()
    
    if categories['unknown']:
        print("❓ MANUAL REVIEW NEEDED:")
        for script in categories['unknown']:
            print(f"   - {script['name']}")
        print()

def main():
    """Main function"""
    print("Root Folder Script Analyzer")
    print("Analyzing Python and shell scripts in root directory...")
    print()
    
    script_files = categorize_root_scripts()
    
    if not script_files:
        print("No Python or shell scripts found in the root directory.")
        return
    
    print_script_categories(script_files)
    
    print("💡 TIP: Create 'archive/root/' folders and move obsolete scripts there")
    print("    Keep active deployment, GPU, and utility scripts in root directory")

if __name__ == "__main__":
    main()
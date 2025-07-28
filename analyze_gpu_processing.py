#!/usr/bin/env python3
"""
GPU Processing Folder Analyzer - Categorizes GPU processing files by purpose and usage frequency
Helps identify which files are still needed vs obsolete one-time setup scripts
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

def analyze_gpu_file_content(file_path):
    """Analyze GPU processing file content to determine purpose and type"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'docstring': '',
            'purpose': 'unknown',
            'type': 'unknown',
            'imports': [],
            'is_core_service': False,
            'is_setup_script': False,
            'is_test_file': False,
            'is_utility': False,
            'is_config': False,
            'is_deployment': False,
            'is_debug_tool': False,
            'one_time_use': False,
            'reusable': False,
            'has_main': False,
            'is_executable': False
        }
        
        filename = os.path.basename(file_path).lower()
        content_lower = content.lower()
        
        # Skip binary files
        if not file_path.endswith(('.py', '.sh', '.md', '.txt', '.service', '.yml', '.yaml', '.json')):
            return analysis
        
        # Extract docstring for Python files
        if file_path.endswith('.py'):
            docstring_match = re.search(r'["\'](["\'])\1\1(.*?)\1\1\1', content, re.DOTALL)
            if docstring_match:
                analysis['docstring'] = docstring_match.group(2).strip()
        
        # Check if executable
        analysis['is_executable'] = os.access(file_path, os.X_OK)
        
        # Check for main function
        analysis['has_main'] = 'if __name__ == "__main__"' in content or 'def main(' in content
        
        # Extract imports for Python files
        if file_path.endswith('.py'):
            import_matches = re.findall(r'^(?:from\s+\S+\s+)?import\s+(.+)$', content, re.MULTILINE)
            for match in import_matches:
                analysis['imports'].extend([imp.strip() for imp in match.split(',')])
        
        # Categorize by filename patterns
        if any(word in filename for word in ['test', 'spec']):
            analysis['is_test_file'] = True
            analysis['purpose'] = 'testing'
            analysis['type'] = 'test'
        
        if any(word in filename for word in ['setup', 'install', 'deploy']):
            analysis['is_setup_script'] = True
            analysis['purpose'] = 'setup'
            analysis['type'] = 'setup'
            analysis['one_time_use'] = True
        
        if any(word in filename for word in ['config', 'settings']):
            analysis['is_config'] = True
            analysis['purpose'] = 'configuration'
            analysis['type'] = 'config'
        
        if filename.endswith('.service'):
            analysis['is_deployment'] = True
            analysis['purpose'] = 'systemd_service'
            analysis['type'] = 'deployment'
        
        # Categorize by core GPU processing functionality
        core_service_indicators = [
            'http_server', 'command_service', 'job_monitor', 'main.py'
        ]
        if any(indicator in filename for indicator in core_service_indicators):
            analysis['is_core_service'] = True
            analysis['purpose'] = 'core_service'
            analysis['type'] = 'service'
            analysis['reusable'] = True
        
        # Categorize utilities
        utility_indicators = [
            'analyzer', 'extractor', 'processor', 'helper'
        ]
        if any(indicator in filename for indicator in utility_indicators):
            analysis['is_utility'] = True
            analysis['purpose'] = 'utility'
            analysis['type'] = 'utility'
            analysis['reusable'] = True
        
        # Debug/development tools
        if any(word in filename for word in ['debug', 'show', 'inspect']):
            analysis['is_debug_tool'] = True
            analysis['purpose'] = 'debugging'
            analysis['type'] = 'debug'
        
        # Analyze content patterns
        if any(pattern in content_lower for pattern in ['fastapi', 'uvicorn', 'flask', 'server']):
            analysis['is_core_service'] = True
        
        if any(pattern in content_lower for pattern in ['systemctl', 'service', 'daemon']):
            analysis['is_deployment'] = True
        
        # Determine if one-time use
        one_time_indicators = [
            'setup', 'install', 'deploy', 'configure', 'initialize'
        ]
        if any(indicator in content_lower for indicator in one_time_indicators):
            analysis['one_time_use'] = True
        
        return analysis
        
    except Exception as e:
        return {'error': str(e)}

def categorize_gpu_processing_files():
    """Categorize all files in the gpu_processing directory"""
    gpu_dir = Path('gpu_processing')
    if not gpu_dir.exists():
        print("GPU processing directory not found!")
        return []
    
    files = []
    
    # Find all files recursively
    for file_path in gpu_dir.rglob('*'):
        if file_path.is_file() and not file_path.name.startswith('.'):
            
            # Get file stats
            stat = file_path.stat()
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime)
            
            # Get git info
            git_info = get_git_info(str(file_path))
            
            # Analyze content
            content_analysis = analyze_gpu_file_content(str(file_path))
            
            files.append({
                'name': file_path.name,
                'path': str(file_path),
                'relative_path': str(file_path),
                'directory': str(file_path.parent),
                'extension': file_path.suffix,
                'size': size,
                'modified': modified,
                'git_info': git_info,
                'analysis': content_analysis
            })
    
    return files

def print_gpu_categories(files):
    """Print GPU processing files organized by categories"""
    
    # Categorize files
    categories = {
        'core_services': [],
        'setup_deployment': [],
        'utilities_analyzers': [],
        'tests': [],
        'config_docs': [],
        'debug_tools': [],
        'obsolete_candidates': [],
        'unknown': []
    }
    
    for file_item in files:
        analysis = file_item['analysis']
        git_info = file_item['git_info']
        
        if analysis.get('is_core_service'):
            categories['core_services'].append(file_item)
        elif analysis.get('is_setup_script') or analysis.get('is_deployment'):
            categories['setup_deployment'].append(file_item)
        elif analysis.get('is_utility'):
            categories['utilities_analyzers'].append(file_item)
        elif analysis.get('is_test_file'):
            categories['tests'].append(file_item)
        elif analysis.get('is_config') or file_item['extension'] in ['.md', '.txt', '.json']:
            categories['config_docs'].append(file_item)
        elif analysis.get('is_debug_tool'):
            categories['debug_tools'].append(file_item)
        elif (analysis.get('one_time_use') or 
              git_info.get('commit_count', 0) <= 2 or
              analysis.get('is_setup_script')):
            categories['obsolete_candidates'].append(file_item)
        else:
            categories['unknown'].append(file_item)
    
    # Print results
    print("=" * 80)
    print("GPU PROCESSING FOLDER ANALYSIS")
    print("=" * 80)
    print()
    
    def print_category(title, files_list, description):
        if not files_list:
            return
            
        print(f"🔶 {title}")
        print(f"   {description}")
        print("-" * 60)
        
        for file_item in sorted(files_list, key=lambda x: x['relative_path']):
            name = file_item['name']
            analysis = file_item['analysis']
            git_info = file_item['git_info']
            
            print(f"📄 {file_item['relative_path']}")
            if analysis.get('docstring'):
                print(f"   Description: {analysis['docstring'][:80]}...")
            print(f"   Purpose: {analysis.get('purpose', 'unknown')}")
            print(f"   Size: {file_item['size']} bytes")
            print(f"   Commits: {git_info['commit_count']}")
            if git_info['last_commit']:
                print(f"   Last modified: {git_info['last_commit'][:10]}")
            
            # Add indicators
            if analysis.get('is_executable'):
                print("   🚀 Executable")
            if analysis.get('has_main'):
                print("   🎯 Has main function")
            if analysis.get('is_core_service'):
                print("   ⚙️  Core GPU service")
            if analysis.get('one_time_use'):
                print("   📅 One-time use - candidate for archiving")
            if analysis.get('is_setup_script'):
                print("   🔧 Setup/deployment script")
            if analysis.get('is_test_file'):
                print("   🧪 Test file")
            
            print()
        
        print()
    
    print_category(
        "CORE GPU SERVICES", 
        categories['core_services'],
        "Essential GPU processing services and main application files"
    )
    
    print_category(
        "UTILITIES & ANALYZERS", 
        categories['utilities_analyzers'],
        "Reusable utility modules for AI processing and analysis"
    )
    
    print_category(
        "TESTS", 
        categories['tests'],
        "Test files for GPU processing functionality"
    )
    
    print_category(
        "CONFIGURATION & DOCS", 
        categories['config_docs'],
        "Configuration files, documentation, and requirements"
    )
    
    print_category(
        "SETUP & DEPLOYMENT", 
        categories['setup_deployment'],
        "Setup scripts, deployment tools, and systemd services"
    )
    
    print_category(
        "DEBUG TOOLS", 
        categories['debug_tools'],
        "Debug utilities and development tools"
    )
    
    print_category(
        "OBSOLETE CANDIDATES", 
        categories['obsolete_candidates'],
        "Low activity files - likely safe to archive"
    )
    
    print_category(
        "UNCLASSIFIED", 
        categories['unknown'],
        "Files that need manual review"
    )
    
    # Summary recommendations
    print("📋 RECOMMENDATIONS")
    print("=" * 40)
    print()
    
    archive_candidates = categories['obsolete_candidates'] + categories['debug_tools']
    if archive_candidates:
        print("🗂️  ARCHIVE CANDIDATES:")
        for file_item in archive_candidates:
            purpose = file_item['analysis'].get('purpose', 'unknown')
            print(f"   - {file_item['relative_path']} ({purpose})")
        print()
    
    keep_files = (categories['core_services'] + categories['utilities_analyzers'] + 
                 categories['tests'] + categories['config_docs'] + 
                 categories['setup_deployment'])
    if keep_files:
        print("✅ KEEP (still useful):")
        for file_item in keep_files:
            purpose = file_item['analysis'].get('purpose', 'unknown')
            print(f"   - {file_item['relative_path']} ({purpose})")
        print()
    
    if categories['unknown']:
        print("❓ MANUAL REVIEW NEEDED:")
        for file_item in categories['unknown']:
            print(f"   - {file_item['relative_path']}")
        print()

def main():
    """Main function"""
    print("GPU Processing Folder Analyzer")
    print("Analyzing files in gpu_processing directory...")
    print()
    
    files = categorize_gpu_processing_files()
    
    if not files:
        print("No files found in the gpu_processing directory.")
        return
    
    print_gpu_categories(files)
    
    print("💡 TIP: Create 'gpu_processing/archive/' folders and move obsolete files there")
    print("    Keep core services, utilities, and active tests in main directories")

if __name__ == "__main__":
    main()
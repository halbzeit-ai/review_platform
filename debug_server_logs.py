#!/usr/bin/env python3
"""
Debug script to monitor server logs in real-time - run this on PRODUCTION server
This will help see what's happening when you access the deck viewer
"""

import os
import subprocess
import time
from datetime import datetime

def find_log_files():
    """Find likely locations for server logs"""
    possible_locations = [
        "/var/log/uvicorn.log",
        "/var/log/fastapi.log", 
        "/var/log/halbzeit.log",
        "/home/ramin/halbzeit-ai/review_platform/backend/app.log",
        "/home/ramin/halbzeit-ai/review_platform/backend/uvicorn.log",
        "/tmp/uvicorn.log",
        "/tmp/fastapi.log"
    ]
    
    existing_logs = []
    for log_path in possible_locations:
        if os.path.exists(log_path):
            existing_logs.append(log_path)
            
    return existing_logs

def monitor_logs():
    """Monitor server logs for deck viewer requests"""
    print("=== SERVER LOG MONITOR ===")
    print("This will monitor server logs for deck viewer requests")
    print("Open the deck viewer in your browser after starting this script")
    print()
    
    log_files = find_log_files()
    
    if not log_files:
        print("No log files found in standard locations.")
        print("Checking for Python processes that might be the server...")
        
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            lines = result.stdout.split('\\n')
            for line in lines:
                if 'uvicorn' in line or 'fastapi' in line or 'main:app' in line:
                    print(f"Found process: {line}")
        except Exception as e:
            print(f"Error checking processes: {e}")
            
        print("\\nPlease run the server with explicit logging:")
        print("cd /home/ramin/halbzeit-ai/review_platform/backend")
        print("uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload --log-level debug --access-log")
        return
    
    print(f"Found {len(log_files)} log files:")
    for i, log_file in enumerate(log_files):
        print(f"  {i+1}. {log_file}")
    
    print("\\nMonitoring all log files for deck viewer activity...")
    print("Look for these patterns:")
    print("  - GET /api/projects/nostic-solutions-ag/deck-analysis/5947")
    print("  - GET /api/projects/nostic-solutions-ag/slide-image/")
    print("  - Any errors or 404s")
    print()
    print("=" * 60)
    
    # Start monitoring
    processes = []
    for log_file in log_files:
        try:
            # Use tail -f to follow the log file
            proc = subprocess.Popen(
                ["tail", "-f", log_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            processes.append((proc, log_file))
        except Exception as e:
            print(f"Error monitoring {log_file}: {e}")
    
    if not processes:
        print("Could not start monitoring any log files")
        return
    
    print(f"Started monitoring {len(processes)} log files...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            for proc, log_file in processes:
                try:
                    # Check if there's new output
                    line = proc.stdout.readline()
                    if line:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] {os.path.basename(log_file)}: {line.strip()}")
                        
                        # Highlight important lines
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in ['deck-analysis', 'slide-image', 'nostic', '5947', 'error', '404', '500']):
                            print("  ^^^ IMPORTANT ^^^")
                            
                except Exception as e:
                    print(f"Error reading from {log_file}: {e}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\\nStopping log monitoring...")
        for proc, _ in processes:
            proc.terminate()

def show_recent_logs():
    """Show recent log entries related to deck viewer"""
    print("=== RECENT LOG ENTRIES ===")
    
    log_files = find_log_files()
    
    for log_file in log_files:
        print(f"\\n--- {log_file} (last 20 lines) ---")
        try:
            result = subprocess.run(["tail", "-20", log_file], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\\n')
                for line in lines:
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['deck', 'nostic', '5947', 'error', '404', '500']):
                        print(f">>> {line}")  # Highlight relevant lines
                    else:
                        print(f"    {line}")
            else:
                print(f"Error reading {log_file}: {result.stderr}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--recent":
        show_recent_logs()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage:")
        print("  python debug_server_logs.py          # Monitor logs in real-time")
        print("  python debug_server_logs.py --recent # Show recent log entries")
    else:
        monitor_logs()
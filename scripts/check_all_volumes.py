#!/usr/bin/env python3
"""
Check ALL volumes in Datacrunch account for orphaned attachments
"""

import json
import sys
import os
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

class DatacrunchVolumeChecker:
    def __init__(self):
        self.api_base = "https://api.datacrunch.io/v1"
        self.access_token = None
        self.client_id = None
        self.client_secret = None
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from .env file"""
        env_file = '/opt/review-platform/backend/.env'
        if not os.path.exists(env_file):
            print(f"Error: {env_file} not found")
            sys.exit(1)
        
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    if key == 'DATACRUNCH_CLIENT_ID':
                        self.client_id = value
                    elif key == 'DATACRUNCH_CLIENT_SECRET':
                        self.client_secret = value
    
    def get_access_token(self):
        """Get access token"""
        if self.access_token:
            return self.access_token
        
        data = urlencode({
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }).encode('utf-8')
        
        req = Request(f"{self.api_base}/oauth2/token", data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        req.add_header('Accept', 'application/json, text/plain, */*')
        
        try:
            with urlopen(req) as response:
                token_data = json.loads(response.read().decode('utf-8'))
                self.access_token = token_data['access_token']
                return self.access_token
        except Exception as e:
            print(f"Error getting token: {e}")
            sys.exit(1)
    
    def _make_request(self, method, endpoint):
        """Make authenticated API request"""
        token = self.get_access_token()
        
        url = f"{self.api_base}{endpoint}"
        req = Request(url, method=method)
        req.add_header('Authorization', f'Bearer {token}')
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        req.add_header('Accept', 'application/json, text/plain, */*')
        
        try:
            with urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"API Error {e.code}: {error_body}")
            raise
    
    def get_all_volumes(self):
        """Get all volumes in account"""
        return self._make_request('GET', '/volumes')
    
    def get_all_instances(self):
        """Get all instances in account"""
        return self._make_request('GET', '/instances')
    
    def get_volume(self, volume_id):
        """Get specific volume"""
        return self._make_request('GET', f'/volumes/{volume_id}')

def check_account_status():
    """Check complete account status"""
    print("=== Datacrunch Account Volume Analysis ===")
    
    checker = DatacrunchVolumeChecker()
    
    try:
        # Get all volumes
        print("📀 Getting all volumes...")
        volumes = checker.get_all_volumes()
        print(f"Total volumes in account: {len(volumes)}")
        
        total_attachments = 0
        problem_volumes = []
        
        for i, volume in enumerate(volumes):
            volume_id = volume.get('id', 'unknown')
            volume_name = volume.get('name', 'unnamed')
            volume_status = volume.get('status', 'unknown')
            volume_type = volume.get('type', 'unknown')
            
            print(f"\n📀 Volume {i+1}: {volume_name}")
            print(f"   ID: {volume_id}")
            print(f"   Status: {volume_status}")
            print(f"   Type: {volume_type}")
            
            # Get detailed volume info
            try:
                detailed_volume = checker.get_volume(volume_id)
                attached_instances = detailed_volume.get('attached_instances', [])
                
                print(f"   Attached instances: {len(attached_instances)}")
                total_attachments += len(attached_instances)
                
                if attached_instances:
                    print(f"   Instance IDs: {attached_instances}")
                    problem_volumes.append({
                        'id': volume_id,
                        'name': volume_name,
                        'attachments': attached_instances
                    })
                
            except Exception as e:
                print(f"   ⚠️  Could not get detailed info: {e}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total volumes: {len(volumes)}")
        print(f"   Total attachments: {total_attachments}")
        print(f"   Volumes with attachments: {len(problem_volumes)}")
        
        # Get all instances to check which ones exist
        print(f"\n🖥️  Getting all instances...")
        instances = checker.get_all_instances()
        existing_instance_ids = [inst.get('id') for inst in instances]
        print(f"Existing instances: {len(existing_instance_ids)}")
        
        # Check for orphaned attachments
        print(f"\n🔍 Checking for orphaned attachments...")
        orphaned_count = 0
        
        for vol in problem_volumes:
            print(f"\n📀 Volume: {vol['name']} ({vol['id']})")
            for instance_id in vol['attachments']:
                if instance_id in existing_instance_ids:
                    print(f"   ✅ Instance {instance_id}: EXISTS")
                else:
                    print(f"   ❌ Instance {instance_id}: ORPHANED")
                    orphaned_count += 1
        
        print(f"\n🎯 RESULTS:")
        print(f"   Orphaned attachments found: {orphaned_count}")
        
        if orphaned_count > 0:
            print(f"\n💡 ACTION NEEDED:")
            print(f"   You have {orphaned_count} orphaned volume attachments")
            print(f"   These are consuming your volume attachment quota")
            print(f"   Contact Datacrunch support to clean them up")
            return False
        else:
            print(f"\n✅ No orphaned attachments found")
            print(f"   The volume limit error might be due to:")
            print(f"   1. Account-level volume limits")
            print(f"   2. Instance creation rate limits") 
            print(f"   3. Temporary API issues")
            return True
            
    except Exception as e:
        print(f"Error checking account: {e}")
        return False

if __name__ == "__main__":
    success = check_account_status()
    sys.exit(0 if success else 1)
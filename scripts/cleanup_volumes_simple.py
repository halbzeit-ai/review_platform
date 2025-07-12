#!/usr/bin/env python3
"""
Simple cleanup script for orphaned volume attachments using system Python
No virtual environment required - uses only standard library
"""

import json
import sys
import os
import asyncio
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

class SimpleDatacrunchClient:
    def __init__(self):
        self.api_base = "https://api.datacrunch.io/v1"
        self.access_token = None
        self.client_id = None
        self.client_secret = None
        self.shared_filesystem_id = None
        
        # Load from environment file
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
                    # Remove quotes if present
                    value = value.strip('"\'')
                    if key == 'DATACRUNCH_CLIENT_ID':
                        self.client_id = value
                    elif key == 'DATACRUNCH_CLIENT_SECRET':
                        self.client_secret = value
                    elif key == 'DATACRUNCH_SHARED_FILESYSTEM_ID':
                        self.shared_filesystem_id = value
        
        if not all([self.client_id, self.client_secret, self.shared_filesystem_id]):
            print("Error: Missing required configuration in .env file")
            print(f"CLIENT_ID: {'✓' if self.client_id else '✗'}")
            print(f"CLIENT_SECRET: {'✓' if self.client_secret else '✗'}")
            print(f"SHARED_FILESYSTEM_ID: {'✓' if self.shared_filesystem_id else '✗'}")
            sys.exit(1)
        
        # Debug: show partial values to verify loading
        print(f"Loaded CLIENT_ID: {self.client_id[:8]}..." if self.client_id else "No CLIENT_ID")
        print(f"Loaded CLIENT_SECRET: {self.client_secret[:8]}..." if self.client_secret else "No CLIENT_SECRET")
    
    def get_access_token(self):
        """Get access token using client credentials"""
        if self.access_token:
            return self.access_token
        
        # Use form data format exactly like the working backend
        data = urlencode({
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }).encode('utf-8')
        
        req = Request(f"{self.api_base}/oauth2/token", data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        # Add browser-like headers to bypass Cloudflare
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Accept-Language', 'en-US,en;q=0.9')
        req.add_header('Origin', 'https://datacrunch.io')
        req.add_header('Referer', 'https://datacrunch.io/')
        
        try:
            print(f"Requesting token from: {self.api_base}/oauth2/token")
            print(f"With client_id: {self.client_id[:8]}...")
            
            with urlopen(req) as response:
                response_text = response.read().decode('utf-8')
                print(f"Token response: {response_text[:100]}...")
                
                token_data = json.loads(response_text)
                self.access_token = token_data['access_token']
                print(f"✓ Token obtained: {self.access_token[:20]}...")
                return self.access_token
                
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            print(f"HTTP Error {e.code}: {error_body}")
            print(f"Request URL: {self.api_base}/oauth2/token")
            print(f"Client ID length: {len(self.client_id)}")
            print(f"Client Secret length: {len(self.client_secret)}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error getting access token: {e}")
            sys.exit(1)
    
    def _make_request(self, method, endpoint, data=None):
        """Make authenticated API request"""
        token = self.get_access_token()
        
        url = f"{self.api_base}{endpoint}"
        
        req_data = None
        if data:
            req_data = json.dumps(data).encode('utf-8')
        
        req = Request(url, data=req_data, method=method)
        req.add_header('Authorization', f'Bearer {token}')
        req.add_header('Content-Type', 'application/json')
        # Add browser-like headers to bypass Cloudflare
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        req.add_header('Accept', 'application/json, text/plain, */*')
        
        try:
            with urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"API Error {e.code}: {error_body}")
            raise
    
    def get_volume(self, volume_id):
        """Get volume information"""
        return self._make_request('GET', f'/volumes/{volume_id}')
    
    def get_instance(self, instance_id):
        """Get instance information"""
        return self._make_request('GET', f'/instances/{instance_id}')
    
    def detach_volume(self, volume_id):
        """Detach volume from instance"""
        return self._make_request('POST', f'/volumes/{volume_id}/detach')

def cleanup_orphaned_attachments():
    """Clean up orphaned volume attachments"""
    print("=== Datacrunch Volume Cleanup (Simple) ===")
    
    client = SimpleDatacrunchClient()
    
    print(f"Shared filesystem ID: {client.shared_filesystem_id}")
    
    try:
        # Get volume information
        print("Getting volume information...")
        volume = client.get_volume(client.shared_filesystem_id)
        
        print(f"Volume name: {volume.get('name', 'Unknown')}")
        print(f"Volume status: {volume.get('status', 'Unknown')}")
        
        attached_instances = volume.get('attached_instances', [])
        print(f"Attached to {len(attached_instances)} instances: {attached_instances}")
        
        if not attached_instances:
            print("✓ No instances attached - volume is clean")
            return True
        
        # Check each attached instance
        cleaned_count = 0
        for instance_id in attached_instances:
            print(f"Checking instance {instance_id}...")
            
            try:
                instance = client.get_instance(instance_id)
                status = instance.get('status', 'unknown')
                print(f"  Instance {instance_id}: {status} (keeping attachment)")
                
            except HTTPError as e:
                if e.code == 404:
                    print(f"  Instance {instance_id}: NOT FOUND - detaching volume")
                    try:
                        client.detach_volume(client.shared_filesystem_id)
                        cleaned_count += 1
                        print(f"  ✓ Detached volume from {instance_id}")
                    except Exception as detach_error:
                        print(f"  ✗ Failed to detach: {detach_error}")
                else:
                    print(f"  Error checking instance {instance_id}: {e}")
        
        print(f"\n✓ Cleanup complete: {cleaned_count} orphaned attachments removed")
        
        # Check final status
        final_volume = client.get_volume(client.shared_filesystem_id)
        final_attachments = final_volume.get('attached_instances', [])
        print(f"Remaining attachments: {len(final_attachments)}")
        
        return True
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return False

def main():
    """Main function"""
    success = cleanup_orphaned_attachments()
    
    if success:
        print("\n🎉 Volume cleanup completed!")
        print("You should now be able to create new GPU instances.")
    else:
        print("\n❌ Volume cleanup failed.")
        print("You may need to contact Datacrunch support.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"""
Datacrunch.io API client for volume and instance management
"""
import httpx
import asyncio
import json
from typing import Optional, Dict, Any, List
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class DatacrunchClient:
    def __init__(self):
        self.client_id = settings.DATACRUNCH_CLIENT_ID
        self.client_secret = settings.DATACRUNCH_CLIENT_SECRET
        self.api_base = settings.DATACRUNCH_API_BASE
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
    
    async def get_access_token(self) -> str:
        """Get or refresh access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Datacrunch client ID and secret must be configured")
        
        # Check if token is still valid (with 5 minute buffer)
        import time
        if self.access_token and self.token_expires_at and time.time() < (self.token_expires_at - 300):
            return self.access_token
        
        # Get new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get access token: {response.text}")
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expires_at = time.time() + token_data["expires_in"]
            
            return self.access_token
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        """Make authenticated API request"""
        token = await self.get_access_token()
        
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers
        
        async with httpx.AsyncClient() as client:
            print(f"DEBUG DATACRUNCH: {method} {endpoint}")
            response = await client.request(method, f"{self.api_base}{endpoint}", **kwargs)
            if response.status_code not in [200, 201, 202]:
                print(f"DEBUG DATACRUNCH: Error {response.status_code}: {response.text[:100]}...")
            
            if response.status_code not in [200, 201, 202]:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
            
            try:
                return response.json()
            except Exception as json_error:
                # Handle special case where Datacrunch returns plain UUID for instance creation
                if endpoint == "/instances" and method == "POST":
                    response_text = response.text.strip()
                    # Check if it looks like a UUID
                    import re
                    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', response_text):
                        print(f"DEBUG DATACRUNCH: Plain UUID response handled")
                        return {"id": response_text}
                
                logger.error(f"Datacrunch API returned invalid JSON for {method} {endpoint}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response text: {response.text}")
                logger.error(f"JSON parse error: {json_error}")
                raise Exception(f"Datacrunch API returned invalid JSON: {json_error}")
    
    async def create_volume(self, name: str, size_gb: int, volume_type: str = "NVMe_Shared") -> Dict[Any, Any]:
        """Create a new volume"""
        data = {
            "name": name,
            "size": size_gb,
            "volume_type": volume_type
        }
        
        result = await self._make_request("POST", "/volumes", json=data)
        logger.info(f"Created volume: {result}")
        return result
    
    async def get_volumes(self) -> List[Dict[Any, Any]]:
        """Get all volumes"""
        result = await self._make_request("GET", "/volumes")
        # API returns a list directly, not a dict with 'volumes' key
        return result if isinstance(result, list) else result.get("volumes", [])
    
    async def get_volume(self, volume_id: str) -> Dict[Any, Any]:
        """Get volume by ID"""
        result = await self._make_request("GET", f"/volumes/{volume_id}")
        return result
    
    async def delete_volume(self, volume_id: str) -> Dict[Any, Any]:
        """Delete volume by ID"""
        result = await self._make_request("DELETE", f"/volumes/{volume_id}")
        return result
    
    async def deploy_instance(self, 
                             hostname: str, 
                             instance_type: str, 
                             image: str = "ubuntu-22.04",
                             description: str = "Review Platform Instance",
                             ssh_key_ids: List[str] = None,
                             existing_volume_ids: List[str] = None,
                             startup_script: str = None) -> Dict[Any, Any]:
        """Deploy instance with proper API parameters"""
        data = {
            "hostname": hostname,
            "instance_type": instance_type,
            "image": image,
            "description": description,
            "ssh_key_ids": ssh_key_ids or [],
            "existing_volumes": existing_volume_ids or [],
            # Try alternative parameter names for volumes
            "volumes": existing_volume_ids or [],
            "volume_ids": existing_volume_ids or []
        }
        
        if startup_script:
            # Try different parameter names for startup script
            data["startup_script"] = startup_script
            data["user_data"] = startup_script
            data["cloud_init"] = startup_script
        
        result = await self._make_request("POST", "/instances", json=data)
        logger.info(f"Deployed instance: {result}")
        return result
    
    async def get_instances(self) -> List[Dict[Any, Any]]:
        """Get all instances"""
        result = await self._make_request("GET", "/instances")
        return result if isinstance(result, list) else result.get("instances", [])
    
    async def get_instance(self, instance_id: str) -> Dict[Any, Any]:
        """Get instance by ID"""
        result = await self._make_request("GET", f"/instances/{instance_id}")
        return result
    
    async def delete_instance(self, instance_id: str) -> Dict[Any, Any]:
        """Delete instance by ID"""
        result = await self._make_request("DELETE", f"/instances/{instance_id}")
        return result
    
    async def wait_for_instance_running(self, instance_id: str, timeout: int = 300) -> bool:
        """Wait for instance to be in running state"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            instance = await self.get_instance(instance_id)
            status = instance.get("status", "").lower()
            
            if status == "running":
                return True
            elif status in ["error", "failed"]:
                raise Exception(f"Instance {instance_id} failed to start")
            
            await asyncio.sleep(10)
        
        return False

# Global client instance
datacrunch_client = DatacrunchClient()
#!/usr/bin/env python3
"""
Clean up orphaned volume attachments from Datacrunch
This script will detach volumes from instances that no longer exist
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.datacrunch import datacrunch_client
from app.core.config import settings

async def cleanup_orphaned_attachments():
    """Clean up all orphaned volume attachments"""
    print("=== Datacrunch Volume Cleanup ===")
    
    # Check if we have the required configuration
    if not settings.DATACRUNCH_SHARED_FILESYSTEM_ID:
        print("Error: DATACRUNCH_SHARED_FILESYSTEM_ID not configured")
        return False
    
    shared_volume_id = settings.DATACRUNCH_SHARED_FILESYSTEM_ID
    print(f"Shared filesystem volume ID: {shared_volume_id}")
    
    try:
        # Get current volume status
        print("Getting volume information...")
        volume = await datacrunch_client.get_volume(shared_volume_id)
        print(f"Volume name: {volume.get('name', 'Unknown')}")
        print(f"Volume status: {volume.get('status', 'Unknown')}")
        
        attached_instances = volume.get("attached_instances", [])
        print(f"Currently attached to {len(attached_instances)} instances: {attached_instances}")
        
        if not attached_instances:
            print("✓ No instances attached to shared volume")
            return True
        
        # Clean up orphaned attachments
        print("Cleaning up orphaned attachments...")
        cleaned_count = await datacrunch_client.cleanup_orphaned_volume_attachments(shared_volume_id)
        
        print(f"✓ Cleaned up {cleaned_count} orphaned attachments")
        
        # Get updated volume status
        volume_after = await datacrunch_client.get_volume(shared_volume_id)
        remaining_attachments = volume_after.get("attached_instances", [])
        print(f"Remaining attachments: {len(remaining_attachments)}")
        
        if remaining_attachments:
            print("Checking remaining attachments...")
            for instance_id in remaining_attachments:
                try:
                    instance = await datacrunch_client.get_instance(instance_id)
                    status = instance.get("status", "unknown")
                    print(f"  - Instance {instance_id}: {status}")
                except Exception as e:
                    print(f"  - Instance {instance_id}: ERROR - {e}")
        
        return True
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return False

async def main():
    """Main cleanup function"""
    success = await cleanup_orphaned_attachments()
    
    if success:
        print("\n🎉 Volume cleanup completed successfully!")
        print("You should now be able to create new GPU instances.")
    else:
        print("\n❌ Volume cleanup failed.")
        print("You may need to contact Datacrunch support.")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
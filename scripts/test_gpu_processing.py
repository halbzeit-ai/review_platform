#!/usr/bin/env python3
"""
Test script to verify GPU processing configuration
"""

import sys
import os
sys.path.append('/opt/review-platform/backend')

from app.services.gpu_processing import GPUProcessingService
from app.core.datacrunch import datacrunch_client
from app.core.config import settings
import asyncio

async def test_gpu_config():
    """Test GPU processing configuration"""
    print("🧪 Testing GPU Processing Configuration")
    print("=" * 50)
    
    # Initialize service
    gpu_service = GPUProcessingService()
    
    print(f"GPU Instance Type: {gpu_service.gpu_instance_type}")
    print(f"GPU Image: {gpu_service.gpu_image}")
    print(f"Processing Timeout: {gpu_service.processing_timeout}s")
    
    # Test Datacrunch connection
    print("\n📡 Testing Datacrunch API Connection...")
    try:
        token = await datacrunch_client.get_access_token()
        print(f"✅ API Connection successful: {token[:20]}...")
    except Exception as e:
        print(f"❌ API Connection failed: {e}")
        return False
    
    # Test shared filesystem configuration
    print("\n💾 Testing Shared Filesystem Configuration...")
    filesystem_id = settings.DATACRUNCH_SHARED_FILESYSTEM_ID
    if filesystem_id:
        print(f"✅ Shared Filesystem ID: {filesystem_id}")
    else:
        print("❌ Shared Filesystem ID not configured")
        return False
    
    # Test instance types (optional - requires API call)
    print("\n🔍 Testing Instance Types...")
    try:
        # Note: This might require a different API endpoint
        print(f"✅ Will attempt to create instance with type: {gpu_service.gpu_instance_type}")
    except Exception as e:
        print(f"⚠️  Could not verify instance types: {e}")
    
    print("\n✅ GPU Processing Configuration Test Complete!")
    return True

async def test_instance_creation():
    """Test creating and immediately deleting a GPU instance"""
    print("\n🚀 Testing GPU Instance Creation...")
    
    gpu_service = GPUProcessingService()
    
    try:
        # Create test instance
        instance_name = "test-gpu-instance"
        filesystem_id = settings.DATACRUNCH_SHARED_FILESYSTEM_ID
        startup_script = "echo 'Test instance started successfully'"
        
        print(f"Creating instance: {instance_name}")
        instance_data = await datacrunch_client.deploy_instance(
            hostname=instance_name,
            instance_type=gpu_service.gpu_instance_type,
            image=gpu_service.gpu_image,
            existing_volume_ids=[filesystem_id],
            startup_script=startup_script
        )
        
        instance_id = instance_data["id"]
        print(f"✅ Instance created successfully: {instance_id}")
        
        # Immediately delete the test instance
        print(f"Deleting test instance: {instance_id}")
        await datacrunch_client.delete_instance(instance_id)
        print("✅ Test instance deleted successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Instance creation test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 GPU Processing Test Suite")
    print("=" * 50)
    
    # Test configuration
    config_ok = await test_gpu_config()
    
    if not config_ok:
        print("\n❌ Configuration test failed - fix issues before proceeding")
        sys.exit(1)
    
    # Ask user if they want to test instance creation
    print("\n🤔 Test actual GPU instance creation? (y/n): ", end="")
    response = input().lower().strip()
    
    if response == 'y':
        creation_ok = await test_instance_creation()
        if creation_ok:
            print("\n🎉 All tests passed! GPU processing is ready.")
        else:
            print("\n❌ Instance creation test failed")
            sys.exit(1)
    else:
        print("\n✅ Configuration tests passed. Ready for GPU processing.")

if __name__ == "__main__":
    asyncio.run(main())
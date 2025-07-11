#!/bin/bash
# Get SSH key IDs from Datacrunch account

echo "🔑 Getting SSH Keys from Datacrunch Account"
echo "=" * 50

# Activate virtual environment and get SSH keys
cd /opt/review-platform/backend
source ../venv/bin/activate

python3 -c "
import sys
import asyncio
sys.path.append('/opt/review-platform/backend')

from app.core.datacrunch import datacrunch_client

async def get_ssh_keys():
    try:
        # Get SSH keys from Datacrunch API
        # Note: This endpoint might need to be adjusted based on Datacrunch API
        ssh_keys = await datacrunch_client._make_request('GET', '/ssh-keys')
        
        if ssh_keys:
            print('✅ SSH Keys found in your Datacrunch account:')
            print('')
            for key in ssh_keys:
                key_id = key.get('id', 'Unknown')
                name = key.get('name', 'Unnamed')
                fingerprint = key.get('fingerprint', 'Unknown')[:20] + '...'
                print(f'  ID: {key_id}')
                print(f'  Name: {name}')
                print(f'  Fingerprint: {fingerprint}')
                print('')
            
            # Suggest configuration
            key_ids = [key.get('id') for key in ssh_keys if key.get('id')]
            if key_ids:
                print('💡 To configure for GPU instances, add to your .env file:')
                print(f'DATACRUNCH_SSH_KEY_IDS={','.join(key_ids)}')
        else:
            print('❌ No SSH keys found in your Datacrunch account')
            print('💡 You need to add SSH keys to your Datacrunch account first')
            
    except Exception as e:
        print(f'❌ Error getting SSH keys: {e}')
        print('💡 Make sure your Datacrunch API credentials are correct')

asyncio.run(get_ssh_keys())
"

echo ""
echo "🔧 Next steps:"
echo "1. If SSH keys were found, add DATACRUNCH_SSH_KEY_IDS to your .env file"
echo "2. If no SSH keys found, add them to your Datacrunch account first"
echo "3. Restart the review-platform service"
#!/bin/bash
# Manual SSH key configuration for GPU instances

echo "🔑 Manual SSH Key Configuration"
echo "=" * 50

echo "Since the SSH key auto-detection isn't working, let's configure it manually."
echo ""

echo "📋 Steps to find your SSH key ID:"
echo "1. Go to your Datacrunch dashboard"
echo "2. Look for 'SSH Keys' or 'Keys' section"
echo "3. Find the key you just added"
echo "4. Look for an ID field (might be called 'Key ID', 'ID', or similar)"
echo ""

echo "🔧 Common SSH key ID formats in Datacrunch:"
echo "- ssh-key-xxxxxxxx"
echo "- key-xxxxxxxx"  
echo "- xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (UUID format)"
echo "- Simple number like 12345"
echo ""

echo "💡 Once you find the SSH key ID:"
echo "1. Edit your .env file:"
echo "   nano /opt/review-platform/backend/.env"
echo ""
echo "2. Add this line (replace YOUR_SSH_KEY_ID with the actual ID):"
echo "   DATACRUNCH_SSH_KEY_IDS=YOUR_SSH_KEY_ID"
echo ""
echo "3. If you have multiple keys, separate with commas:"
echo "   DATACRUNCH_SSH_KEY_IDS=key1,key2,key3"
echo ""
echo "4. Restart the service:"
echo "   systemctl restart review-platform"
echo ""
echo "5. Test GPU processing by uploading a PDF"
echo ""

echo "❓ Can't find the SSH key ID?"
echo "You can also try these common patterns based on your key name:"

# Try to suggest some IDs based on common patterns
echo ""
echo "🎯 Try these in your .env file (one at a time):"
echo "DATACRUNCH_SSH_KEY_IDS=ssh-key-1"
echo "DATACRUNCH_SSH_KEY_IDS=key-1" 
echo "DATACRUNCH_SSH_KEY_IDS=1"
echo ""
echo "Or check the browser developer tools:"
echo "1. Open Datacrunch dashboard"
echo "2. Press F12 to open developer tools"
echo "3. Go to Network tab"
echo "4. Refresh the SSH keys page"
echo "5. Look for API calls that show your SSH key data"
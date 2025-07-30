#!/bin/bash
# Setup GitHub SSH access for GPU dev machine

echo "🔑 Setting up GitHub SSH access for GPU dev machine"
echo "===================================================="

# Generate SSH key if it doesn't exist
if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "📝 Generating new SSH key..."
    ssh-keygen -t ed25519 -C "dev-gpu-fin-01" -f ~/.ssh/id_ed25519 -N ""
    echo "✅ SSH key generated"
else
    echo "✅ SSH key already exists"
fi

# Display the public key
echo ""
echo "📋 Your SSH public key:"
echo "========================"
cat ~/.ssh/id_ed25519.pub
echo "========================"
echo ""
echo "📌 Next steps:"
echo "1. Copy the SSH key above"
echo "2. Go to: https://github.com/settings/keys"
echo "3. Click 'New SSH key'"
echo "4. Title: 'dev-gpu-fin-01'"
echo "5. Paste the key and save"
echo ""
echo "After adding the key to GitHub, you can clone with:"
echo "git clone git@github.com:halbzeit-ai/review_platform.git /opt/review-platform-dev"
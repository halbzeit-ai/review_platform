#!/bin/bash

# Geographic IP Blocking Script for HALBZEIT AI
# Blocks traffic from China and Russia for security purposes
# Based on CIDR ranges from reliable IP allocation databases

set -e

echo "🛡️  Setting up geographic IP blocking for China and Russia..."

# Create directory for IP lists
sudo mkdir -p /etc/security/ip-blocks

# Function to download and process country IP ranges
download_country_ips() {
    local country_code=$1
    local country_name=$2
    local output_file="/etc/security/ip-blocks/${country_code,,}.txt"
    
    echo "📥 Downloading IP ranges for $country_name ($country_code)..."
    
    # Download from multiple reliable sources and combine
    # Using ipdeny.com which provides reliable country-based IP ranges
    wget -q -O - "https://www.ipdeny.com/ipblocks/data/countries/${country_code,,}.zone" > "$output_file" 2>/dev/null || {
        echo "⚠️  Failed to download from ipdeny.com, trying alternative..."
        
        # Alternative: Use ipverse.net
        wget -q -O - "https://ipverse.net/ipblocks/data/countries/${country_code,,}.zone" > "$output_file" 2>/dev/null || {
            echo "❌ Failed to download IP ranges for $country_name"
            return 1
        }
    }
    
    echo "✅ Downloaded $(wc -l < "$output_file") IP ranges for $country_name"
}

# Create iptables chain for geo-blocking
echo "🔧 Creating iptables chain for geo-blocking..."
sudo iptables -N GEO_BLOCK 2>/dev/null || echo "Chain GEO_BLOCK already exists"

# Clear existing rules in the chain
sudo iptables -F GEO_BLOCK

# Download IP ranges for China and Russia
download_country_ips "CN" "China"
download_country_ips "RU" "Russia"

# Add China IP ranges to iptables
echo "🚫 Adding China IP ranges to firewall..."
if [ -f "/etc/security/ip-blocks/cn.txt" ]; then
    while IFS= read -r ip_range; do
        [ -n "$ip_range" ] && sudo iptables -A GEO_BLOCK -s "$ip_range" -j DROP
    done < /etc/security/ip-blocks/cn.txt
    echo "✅ Added $(wc -l < /etc/security/ip-blocks/cn.txt) China IP ranges"
fi

# Add Russia IP ranges to iptables
echo "🚫 Adding Russia IP ranges to firewall..."
if [ -f "/etc/security/ip-blocks/ru.txt" ]; then
    while IFS= read -r ip_range; do
        [ -n "$ip_range" ] && sudo iptables -A GEO_BLOCK -s "$ip_range" -j DROP
    done < /etc/security/ip-blocks/ru.txt
    echo "✅ Added $(wc -l < /etc/security/ip-blocks/ru.txt) Russia IP ranges"
fi

# Insert the geo-blocking chain at the beginning of INPUT chain
# Only if it's not already there
if ! sudo iptables -C INPUT -j GEO_BLOCK 2>/dev/null; then
    sudo iptables -I INPUT 1 -j GEO_BLOCK
    echo "✅ Activated geo-blocking in INPUT chain"
else
    echo "✅ Geo-blocking already active in INPUT chain"
fi

# Save iptables rules
echo "💾 Saving iptables rules..."
sudo iptables-save > /etc/iptables/rules.v4

# Create systemd service for automatic updates
echo "⚙️  Creating auto-update service..."
sudo tee /etc/systemd/system/geo-block-update.service > /dev/null << 'EOF'
[Unit]
Description=Update Geographic IP Blocking Rules
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/review-platform/scripts/setup-geo-blocking.sh
User=root
StandardOutput=journal
StandardError=journal
EOF

# Create timer for weekly updates
sudo tee /etc/systemd/system/geo-block-update.timer > /dev/null << 'EOF'
[Unit]
Description=Update Geographic IP Blocking Rules Weekly
Requires=geo-block-update.service

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start the timer
sudo systemctl daemon-reload
sudo systemctl enable geo-block-update.timer
sudo systemctl start geo-block-update.timer

# Show current status
echo "📊 Current geo-blocking status:"
echo "   📈 Total blocked IP ranges: $(sudo iptables -L GEO_BLOCK -n | grep -c DROP || echo 0)"
echo "   🕒 Auto-update timer: $(sudo systemctl is-active geo-block-update.timer)"

# Log the blocking
echo "📝 Logging geo-blocking setup to system log..."
logger "HALBZEIT-SECURITY: Geographic IP blocking enabled for China and Russia"

echo "🎉 Geographic IP blocking setup complete!"
echo ""
echo "To check status: sudo iptables -L GEO_BLOCK -n"
echo "To disable: sudo iptables -D INPUT -j GEO_BLOCK"
echo "To re-enable: sudo iptables -I INPUT 1 -j GEO_BLOCK"
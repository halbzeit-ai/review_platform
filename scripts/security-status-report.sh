#!/bin/bash

# HALBZEIT AI Security Status Report
echo "🛡️  HALBZEIT AI Security Status Report - $(date)"
echo "=================================================="

echo ""
echo "🌍 Geographic IP Blocking:"
# Check for GEO_BLOCK chain existence and ipset-based blocking
if sudo iptables -L GEO_BLOCK -n >/dev/null 2>&1; then
    # Check if ipset-based rules exist
    cn_blocked=$(sudo ipset list geoblock_cn 2>/dev/null | grep "Number of entries" | awk '{print $4}' || echo "0")
    ru_blocked=$(sudo ipset list geoblock_ru 2>/dev/null | grep "Number of entries" | awk '{print $4}' || echo "0")
    
    if [ "$cn_blocked" -gt 0 ] || [ "$ru_blocked" -gt 0 ]; then
        total_blocked=$((cn_blocked + ru_blocked))
        echo "   ✅ Active - Blocking $total_blocked IP ranges from China ($cn_blocked) and Russia ($ru_blocked)"
    else
        # Fallback to old method for legacy rule-based blocking
        geo_rules=$(sudo iptables -L GEO_BLOCK -n | wc -l)
        if [ $geo_rules -gt 10 ]; then
            echo "   ✅ Active - Blocking $((geo_rules-2)) IP ranges from China and Russia"
        else
            echo "   ❌ Not configured"
        fi
    fi
else
    echo "   ❌ Not configured"
fi

echo ""
echo "🚨 Fail2ban Protection:"
fail2ban_status=$(sudo systemctl is-active fail2ban 2>/dev/null || echo "inactive")
if [ "$fail2ban_status" = "active" ]; then
    echo "   ✅ Active"
    sudo fail2ban-client status | grep -E "(Number of jail|Jail list)"
else
    echo "   ❌ Not running"
fi

echo ""
echo "🔥 Firewall Status:"
if command -v ufw >/dev/null 2>&1; then
    ufw_status=$(sudo ufw status | grep "Status:" | awk '{print $2}')
    if [ "$ufw_status" = "active" ]; then
        echo "   ✅ UFW Active"
    else
        echo "   ⚠️  UFW Inactive"
    fi
else
    echo "   ⚠️  UFW Not installed - using iptables-persistent"
fi

echo ""
echo "🔐 SSH Security:"
ssh_status=$(sudo systemctl is-active ssh 2>/dev/null || echo "inactive")
if [ "$ssh_status" = "active" ]; then
    echo "   ✅ SSH Service Active"
    if grep -q "PermitRootLogin no" /etc/ssh/sshd_config* 2>/dev/null; then
        echo "   ✅ Root login disabled"
    else
        echo "   ⚠️  Root login may be enabled"
    fi
else
    echo "   ❌ SSH Service not running"
fi

echo ""
echo "🌐 Open Ports:"
ss -tuln | grep LISTEN | grep -E ":80|:443|:22|:8000" | while read line; do
    echo "   📡 $line"
done

echo ""
echo "📊 System Status:"
echo "   🖥️  Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "   💾 Disk: $(df -h / | awk 'NR==2 {print $5 " used (" $4 " free)"}')"
echo "   🕒 Uptime: $(uptime -p)"

echo ""
echo "📝 Recent Security Events (last 24h):"
recent_blocks=$(sudo journalctl --since "24 hours ago" | grep -i "fail2ban\|blocked\|banned" | wc -l)
if [ $recent_blocks -gt 0 ]; then
    echo "   🚫 $recent_blocks security events detected"
    sudo journalctl --since "24 hours ago" | grep -i "fail2ban\|blocked\|banned" | tail -3 | sed 's/^/      /'
else
    echo "   ✅ No security events in last 24h"
fi

echo ""
echo "🎯 Security Recommendations:"
echo "   • Monitor logs regularly: sudo journalctl -f"
echo "   • Check blocked IPs: sudo fail2ban-client status sshd"
echo "   • Review firewall rules: sudo iptables -L -n"
echo "   • Keep system updated: sudo apt update && sudo apt upgrade"

echo ""
echo "📞 Emergency Commands:"
echo "   • Disable geo-blocking: sudo iptables -D INPUT -j GEO_BLOCK"
echo "   • Restart fail2ban: sudo systemctl restart fail2ban"
echo "   • Allow emergency SSH: sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT"

echo ""
echo "✅ Security check completed at $(date)"
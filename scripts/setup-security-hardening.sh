#!/bin/bash

# Security Hardening Script for HALBZEIT AI
# Based on Datacrunch.io recommendations plus additional hardening measures

set -e

echo "🛡️  Starting comprehensive security hardening..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 1. Install and Configure Fail2ban (Datacrunch recommendation)
echo "🚨 Installing and configuring Fail2ban..."
sudo apt install -y fail2ban

# Create custom fail2ban configuration
sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[DEFAULT]
# Ban hosts for 1 hour by default
bantime = 3600
# Find failures in 10 minutes
findtime = 600
# Ban after 3 attempts
maxretry = 3
# Email notifications (configure SMTP if needed)
destemail = ramin@halbzeit.ai
sendername = HALBZEIT-Security
mta = sendmail

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-botsearch]
enabled = true
filter = nginx-botsearch
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 3
EOF

# Start and enable Fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# 2. Configure UFW Firewall (Datacrunch recommendation)
echo "🔥 Installing and configuring UFW firewall..."
sudo apt install -y ufw

# Reset UFW to default policies
sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow essential services
sudo ufw allow ssh comment 'SSH access'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Allow backend API port (internal)
sudo ufw allow 8000/tcp comment 'Backend API'

# Enable UFW
echo "y" | sudo ufw enable

# 3. Additional Security Hardening Measures

# Secure shared memory
echo "🔒 Securing shared memory..."
if ! grep -q "tmpfs /run/shm tmpfs defaults,noexec,nosuid" /etc/fstab; then
    echo "tmpfs /run/shm tmpfs defaults,noexec,nosuid 0 0" | sudo tee -a /etc/fstab
fi

# Disable unused network protocols
echo "🌐 Disabling unused network protocols..."
sudo tee /etc/modprobe.d/blacklist-rare-network.conf > /dev/null << 'EOF'
# Disable rare network protocols
install dccp /bin/true
install sctp /bin/true
install rds /bin/true
install tipc /bin/true
EOF

# Configure kernel security parameters
echo "⚙️  Configuring kernel security parameters..."
sudo tee /etc/sysctl.d/99-security-hardening.conf > /dev/null << 'EOF'
# IP Spoofing protection
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Log Martians (packets with impossible addresses)
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Ignore ICMP ping requests
net.ipv4.icmp_echo_ignore_all = 1

# Ignore Directed pings
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Disable IPv6 if not needed
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1

# TCP SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5
EOF

# Apply kernel parameters
sudo sysctl -p /etc/sysctl.d/99-security-hardening.conf

# 4. SSH Hardening
echo "🔐 Hardening SSH configuration..."
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

sudo tee /etc/ssh/sshd_config.d/99-halbzeit-security.conf > /dev/null << 'EOF'
# HALBZEIT AI SSH Security Configuration

# Disable root login
PermitRootLogin no

# Use SSH protocol 2 only
Protocol 2

# Change default port (uncomment if you want to use a different port)
# Port 2222

# Disable password authentication (enable only if you have SSH keys set up)
# PasswordAuthentication no

# Maximum authentication attempts
MaxAuthTries 3

# Login grace time
LoginGraceTime 30

# Maximum sessions per connection
MaxSessions 2

# Disable empty passwords
PermitEmptyPasswords no

# Disable X11 forwarding
X11Forwarding no

# Disable tunneling
AllowTcpForwarding no
AllowStreamLocalForwarding no
GatewayPorts no

# Enable strict mode
StrictModes yes

# Log verbosely
LogLevel VERBOSE

# Client alive settings
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

# Validate SSH configuration
sudo sshd -t

# Restart SSH service
sudo systemctl restart ssh

# 5. Install additional security tools
echo "🛠️  Installing additional security tools..."
sudo apt install -y \
    lynis \
    rkhunter \
    chkrootkit \
    aide \
    unattended-upgrades \
    logwatch

# Configure automatic security updates
echo "🔄 Configuring automatic security updates..."
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure aide for file integrity monitoring
echo "📁 Configuring AIDE file integrity monitoring..."
sudo aideinit
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# 6. Set up log monitoring and alerting
echo "📊 Setting up log monitoring..."
sudo tee /etc/logwatch/conf/logwatch.conf > /dev/null << 'EOF'
# Logwatch configuration for HALBZEIT AI
MailTo = ramin@halbzeit.ai
MailFrom = security@halbzeit.ai
Detail = Med
Service = All
Range = yesterday
Format = html
Output = mail
EOF

# 7. Create security monitoring script
echo "🕵️  Creating security monitoring script..."
sudo tee /opt/review-platform/scripts/security-check.sh > /dev/null << 'EOF'
#!/bin/bash

# HALBZEIT AI Security Check Script
echo "🛡️  HALBZEIT AI Security Status Report - $(date)"
echo "=================================================="

echo "🔥 UFW Firewall Status:"
sudo ufw status verbose

echo ""
echo "🚨 Fail2ban Status:"
sudo fail2ban-client status

echo ""
echo "🔐 SSH Login Attempts (last 24h):"
sudo journalctl --since "24 hours ago" -u ssh | grep -E "(Failed|Accepted)" | tail -10

echo ""
echo "🌐 Active Network Connections:"
ss -tuln

echo ""
echo "💾 Disk Usage:"
df -h / /var /tmp

echo ""
echo "🖥️  System Load:"
uptime

echo ""
echo "🔍 Recent Security Events:"
sudo ausearch -ts today -m avc,user_auth,user_start,user_end 2>/dev/null | tail -5 || echo "No auditd events found"

echo ""
echo "✅ Security check completed at $(date)"
EOF

chmod +x /opt/review-platform/scripts/security-check.sh

# 8. Create systemd service for regular security checks
sudo tee /etc/systemd/system/security-check.service > /dev/null << 'EOF'
[Unit]
Description=HALBZEIT AI Security Check
After=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/review-platform/scripts/security-check.sh
User=root
StandardOutput=journal
StandardError=journal
EOF

# Create timer for daily security checks
sudo tee /etc/systemd/system/security-check.timer > /dev/null << 'EOF'
[Unit]
Description=Daily Security Check for HALBZEIT AI
Requires=security-check.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start the timer
sudo systemctl daemon-reload
sudo systemctl enable security-check.timer
sudo systemctl start security-check.timer

# Final verification
echo "✅ Verifying security configuration..."
echo "📊 UFW Status:"
sudo ufw status

echo ""
echo "🚨 Fail2ban Status:"
sudo fail2ban-client status

echo ""
echo "⚙️  Systemd Timers:"
sudo systemctl list-timers --all | grep -E "(security-check|geo-block)"

echo ""
echo "🎉 Security hardening completed successfully!"
echo ""
echo "📋 Summary of implemented security measures:"
echo "   • Fail2ban: Protection against brute force attacks"
echo "   • UFW Firewall: Network traffic filtering"
echo "   • Kernel hardening: Security-focused kernel parameters"
echo "   • SSH hardening: Secure SSH configuration"
echo "   • File integrity monitoring: AIDE database"
echo "   • Automatic security updates: Unattended upgrades"
echo "   • Daily security monitoring: Automated reports"
echo ""
echo "🔧 Next steps:"
echo "   • Run geo-blocking script: /opt/review-platform/scripts/setup-geo-blocking.sh"
echo "   • Review logs regularly: sudo journalctl -f"
echo "   • Check security status: /opt/review-platform/scripts/security-check.sh"

# Log security hardening completion
logger "HALBZEIT-SECURITY: Security hardening completed successfully"
#!/bin/bash

# Security Hardening Script for HALBZEIT AI - Safe Version
# Based on Datacrunch.io recommendations plus additional hardening measures
# This version ensures a sudo user exists before disabling root login

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🛡️  Starting comprehensive security hardening (Safe Version)...${NC}"

# Function to check for sudo users
check_sudo_users() {
    echo -e "${BLUE}👥 Checking for existing sudo users...${NC}"
    
    # Get all users with sudo privileges
    SUDO_USERS=$(getent group sudo | cut -d: -f4 | tr ',' '\n' | grep -v '^$' || true)
    
    # Also check sudoers.d directory for user-specific files
    if [ -d /etc/sudoers.d ]; then
        for file in /etc/sudoers.d/*; do
            if [ -f "$file" ]; then
                # Extract usernames from sudoers files (basic pattern matching)
                grep -E "^[^#].*ALL.*ALL" "$file" 2>/dev/null | awk '{print $1}' | grep -v '^%' >> /tmp/sudoers_check || true
            fi
        done
    fi
    
    # Count non-root sudo users
    NON_ROOT_SUDO_COUNT=0
    if [ -n "$SUDO_USERS" ]; then
        for user in $SUDO_USERS; do
            if [ "$user" != "root" ] && id "$user" &>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Found sudo user: $user"
                NON_ROOT_SUDO_COUNT=$((NON_ROOT_SUDO_COUNT + 1))
            fi
        done
    fi
    
    # Clean up temp file
    rm -f /tmp/sudoers_check
    
    return $NON_ROOT_SUDO_COUNT
}

# Function to create a sudo user
create_sudo_user() {
    echo -e "${YELLOW}⚠️  No non-root sudo users found!${NC}"
    echo -e "${RED}CRITICAL: Disabling root login without a sudo user will lock you out!${NC}"
    echo ""
    
    read -p "Would you like to create a sudo user now? (yes/no): " CREATE_USER
    
    if [[ "$CREATE_USER" =~ ^[Yy]es$ ]]; then
        read -p "Enter username for the new sudo user: " NEW_USER
        
        # Validate username
        if [[ ! "$NEW_USER" =~ ^[a-z][-a-z0-9]*$ ]]; then
            echo -e "${RED}Invalid username. Must start with lowercase letter and contain only lowercase letters, numbers, and hyphens.${NC}"
            exit 1
        fi
        
        # Check if user already exists
        if id "$NEW_USER" &>/dev/null; then
            echo -e "${YELLOW}User $NEW_USER already exists. Adding to sudo group...${NC}"
            sudo usermod -aG sudo "$NEW_USER"
        else
            echo -e "${GREEN}Creating user $NEW_USER...${NC}"
            sudo adduser --gecos "" "$NEW_USER"
            sudo usermod -aG sudo "$NEW_USER"
        fi
        
        # Set up SSH key for the new user
        echo ""
        echo -e "${BLUE}SSH Key Setup for $NEW_USER:${NC}"
        echo "1. Copy your existing SSH public key"
        echo "2. Create a new SSH key pair"
        echo "3. Skip SSH key setup (configure manually later)"
        read -p "Choose option (1/2/3): " SSH_OPTION
        
        case $SSH_OPTION in
            1)
                echo "Please paste your SSH public key (entire line):"
                read -r SSH_KEY
                if [ -n "$SSH_KEY" ]; then
                    sudo mkdir -p /home/$NEW_USER/.ssh
                    echo "$SSH_KEY" | sudo tee /home/$NEW_USER/.ssh/authorized_keys
                    sudo chown -R $NEW_USER:$NEW_USER /home/$NEW_USER/.ssh
                    sudo chmod 700 /home/$NEW_USER/.ssh
                    sudo chmod 600 /home/$NEW_USER/.ssh/authorized_keys
                    echo -e "${GREEN}✓ SSH key added successfully${NC}"
                fi
                ;;
            2)
                sudo -u $NEW_USER ssh-keygen -t ed25519 -f /home/$NEW_USER/.ssh/id_ed25519 -N ""
                sudo cat /home/$NEW_USER/.ssh/id_ed25519.pub >> /home/$NEW_USER/.ssh/authorized_keys
                sudo chmod 600 /home/$NEW_USER/.ssh/authorized_keys
                echo -e "${GREEN}✓ SSH key pair created${NC}"
                echo -e "${YELLOW}⚠️  Save this private key to access the server:${NC}"
                sudo cat /home/$NEW_USER/.ssh/id_ed25519
                ;;
            3)
                echo -e "${YELLOW}⚠️  Remember to configure SSH access before disabling password authentication!${NC}"
                ;;
        esac
        
        echo -e "${GREEN}✅ User $NEW_USER created successfully with sudo privileges${NC}"
        
        # Test sudo access
        echo -e "${BLUE}Testing sudo access for $NEW_USER...${NC}"
        sudo -u $NEW_USER sudo -n true 2>/dev/null && echo -e "${GREEN}✓ Sudo access verified${NC}" || echo -e "${YELLOW}⚠️  User will need to enter password for sudo${NC}"
        
        return 0
    else
        echo -e "${RED}⚠️  WARNING: Proceeding without creating a sudo user!${NC}"
        echo -e "${RED}Root login will remain enabled to prevent lockout.${NC}"
        return 1
    fi
}

# Update system packages
echo -e "${BLUE}📦 Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Check for sudo users before proceeding with security hardening
check_sudo_users
SUDO_USER_COUNT=$?

if [ $SUDO_USER_COUNT -eq 0 ]; then
    create_sudo_user
    HAS_SUDO_USER=$?
else
    echo -e "${GREEN}✅ Found $SUDO_USER_COUNT non-root sudo user(s). Safe to proceed.${NC}"
    HAS_SUDO_USER=0
fi

# 1. Install and Configure Fail2ban (Datacrunch recommendation)
echo -e "${BLUE}🚨 Installing and configuring Fail2ban...${NC}"
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
echo -e "${BLUE}🔥 Installing and configuring UFW firewall...${NC}"
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

# 2a. Geographic IP Blocking for China and Russia
echo -e "${BLUE}🌍 Setting up geographic IP blocking (China & Russia)...${NC}"

# Install required packages for geographic IP blocking
echo -e "${BLUE}📦 Checking and installing required packages for geo-blocking...${NC}"

# Check and install ipset
if ! command -v ipset &> /dev/null; then
    echo -e "  Installing ipset..."
    sudo apt install -y ipset
else
    echo -e "  ${GREEN}✓${NC} ipset already installed"
fi

# Check and install wget
if ! command -v wget &> /dev/null; then
    echo -e "  Installing wget..."
    sudo apt install -y wget
else
    echo -e "  ${GREEN}✓${NC} wget already installed"
fi

# Check and install iptables-persistent
if ! dpkg -l | grep -q iptables-persistent; then
    echo -e "  Installing iptables-persistent..."
    # Pre-configure to avoid interactive prompts
    echo "iptables-persistent iptables-persistent/autosave_v4 boolean false" | sudo debconf-set-selections
    echo "iptables-persistent iptables-persistent/autosave_v6 boolean false" | sudo debconf-set-selections
    DEBIAN_FRONTEND=noninteractive sudo apt install -y iptables-persistent
else
    echo -e "  ${GREEN}✓${NC} iptables-persistent already installed"
fi

# Create directory for IP lists
sudo mkdir -p /etc/security/ip-blocks

# Function to download country IP ranges
download_country_ips() {
    local country_code=$1
    local country_name=$2
    local output_file="/etc/security/ip-blocks/${country_code,,}.txt"
    
    echo -e "  📥 Downloading IP ranges for $country_name ($country_code)..."
    
    # Download from ipdeny.com (reliable source)
    if wget -q -O - "https://www.ipdeny.com/ipblocks/data/countries/${country_code,,}.zone" > "$output_file" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Downloaded $(wc -l < "$output_file") IP ranges for $country_name"
        return 0
    else
        echo -e "  ${YELLOW}⚠️${NC} Failed to download IP ranges for $country_name"
        return 1
    fi
}

# Create ipset for blocked countries (more efficient than individual iptables rules)
echo -e "${BLUE}Creating IP sets for geo-blocking...${NC}"
sudo ipset create geoblock_cn hash:net family inet maxelem 65536 2>/dev/null || sudo ipset flush geoblock_cn
sudo ipset create geoblock_ru hash:net family inet maxelem 65536 2>/dev/null || sudo ipset flush geoblock_ru

# Download and add China IP ranges
if download_country_ips "CN" "China"; then
    while IFS= read -r ip_range; do
        [ -n "$ip_range" ] && sudo ipset add geoblock_cn "$ip_range" 2>/dev/null || true
    done < /etc/security/ip-blocks/cn.txt
    echo -e "${GREEN}✅ Added China IP ranges to blocking list${NC}"
fi

# Download and add Russia IP ranges
if download_country_ips "RU" "Russia"; then
    while IFS= read -r ip_range; do
        [ -n "$ip_range" ] && sudo ipset add geoblock_ru "$ip_range" 2>/dev/null || true
    done < /etc/security/ip-blocks/ru.txt
    echo -e "${GREEN}✅ Added Russia IP ranges to blocking list${NC}"
fi

# Add iptables rules using ipset (much more efficient)
echo -e "${BLUE}Applying geo-blocking rules...${NC}"
sudo iptables -I INPUT 1 -m set --match-set geoblock_cn src -j DROP 2>/dev/null || true
sudo iptables -I INPUT 1 -m set --match-set geoblock_ru src -j DROP 2>/dev/null || true

# Save iptables rules
sudo netfilter-persistent save

echo -e "${GREEN}✅ Geographic blocking configured for China and Russia${NC}"

# 3. Additional Security Hardening Measures

# Secure shared memory
echo -e "${BLUE}🔒 Securing shared memory...${NC}"
if ! grep -q "tmpfs /run/shm tmpfs defaults,noexec,nosuid" /etc/fstab; then
    echo "tmpfs /run/shm tmpfs defaults,noexec,nosuid 0 0" | sudo tee -a /etc/fstab
fi

# Disable unused network protocols
echo -e "${BLUE}🌐 Disabling unused network protocols...${NC}"
sudo tee /etc/modprobe.d/blacklist-rare-network.conf > /dev/null << 'EOF'
# Disable rare network protocols
install dccp /bin/true
install sctp /bin/true
install rds /bin/true
install tipc /bin/true
EOF

# Configure kernel security parameters
echo -e "${BLUE}⚙️  Configuring kernel security parameters...${NC}"
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
echo -e "${BLUE}🔐 Hardening SSH configuration...${NC}"
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)

# Determine if we should disable root login
if [ $HAS_SUDO_USER -eq 0 ]; then
    ROOT_LOGIN_SETTING="PermitRootLogin prohibit-password  # Key-based only"
    echo -e "${GREEN}✅ Disabling password-based root login (key-based still allowed)${NC}"
else
    ROOT_LOGIN_SETTING="# PermitRootLogin no  # Kept enabled - no sudo user exists!"
    echo -e "${YELLOW}⚠️  Keeping root login enabled - no sudo user configured${NC}"
fi

sudo tee /etc/ssh/sshd_config.d/99-halbzeit-security.conf > /dev/null << EOF
# HALBZEIT AI SSH Security Configuration
# Generated on $(date)

# Root login configuration
$ROOT_LOGIN_SETTING

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
echo -e "${BLUE}Validating SSH configuration...${NC}"
sudo sshd -t && echo -e "${GREEN}✓ SSH configuration valid${NC}" || echo -e "${RED}✗ SSH configuration error!${NC}"

# Restart SSH service
sudo systemctl restart ssh

# 5. Install additional security tools
echo -e "${BLUE}🛠️  Installing additional security tools...${NC}"
sudo apt install -y \
    lynis \
    rkhunter \
    chkrootkit \
    aide \
    unattended-upgrades \
    logwatch

# Configure automatic security updates
echo -e "${BLUE}🔄 Configuring automatic security updates...${NC}"
echo -e "unattended-upgrades unattended-upgrades/enable_auto_updates boolean true" | sudo debconf-set-selections
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure aide for file integrity monitoring
echo -e "${BLUE}📁 Configuring AIDE file integrity monitoring...${NC}"
sudo aideinit
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# 6. Set up log monitoring and alerting
echo -e "${BLUE}📊 Setting up log monitoring...${NC}"
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
echo -e "${BLUE}🕵️  Creating security monitoring script...${NC}"
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
echo "👥 Sudo Users:"
getent group sudo | cut -d: -f4

echo ""
echo "🌍 Geo-blocking Status:"
echo -n "  China IPs blocked: "
sudo ipset list geoblock_cn 2>/dev/null | grep "Number of entries" | awk '{print $4}'
echo -n "  Russia IPs blocked: "
sudo ipset list geoblock_ru 2>/dev/null | grep "Number of entries" | awk '{print $4}'

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
Description=Run HALBZEIT AI Security Check daily
Persistent=true

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h

[Install]
WantedBy=timers.target
EOF

# Enable and start the timer
sudo systemctl daemon-reload
sudo systemctl enable security-check.timer
sudo systemctl start security-check.timer

# 9. Final security summary
echo ""
echo -e "${GREEN}=================================================="
echo -e "🎉 Security Hardening Complete!"
echo -e "==================================================${NC}"
echo ""
echo -e "${BLUE}Summary of configurations:${NC}"
echo -e "  ${GREEN}✓${NC} Fail2ban configured and running"
echo -e "  ${GREEN}✓${NC} UFW firewall enabled with essential ports"
echo -e "  ${GREEN}✓${NC} Geographic blocking active (China & Russia)"
echo -e "  ${GREEN}✓${NC} Kernel security parameters hardened"

if [ $HAS_SUDO_USER -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} SSH hardened with restricted root access"
    echo -e "  ${GREEN}✓${NC} Sudo user configured for administrative access"
else
    echo -e "  ${YELLOW}⚠️${NC}  SSH partially hardened (root login still enabled)"
    echo -e "  ${RED}⚠️${NC}  No sudo user configured - create one ASAP!"
fi

echo -e "  ${GREEN}✓${NC} Security monitoring tools installed"
echo -e "  ${GREEN}✓${NC} Automatic security updates configured"
echo -e "  ${GREEN}✓${NC} File integrity monitoring (AIDE) initialized"
echo -e "  ${GREEN}✓${NC} Daily security checks scheduled"
echo ""

# Check current SSH sessions
echo -e "${YELLOW}⚠️  Current SSH sessions:${NC}"
who

echo ""
echo -e "${BLUE}Important next steps:${NC}"
if [ $HAS_SUDO_USER -eq 0 ]; then
    echo -e "1. ${YELLOW}TEST SSH access with your sudo user in a NEW terminal before closing this session${NC}"
    echo -e "2. Once verified, you can fully disable root login by editing:"
    echo -e "   /etc/ssh/sshd_config.d/99-halbzeit-security.conf"
    echo -e "   Change: PermitRootLogin prohibit-password"
    echo -e "   To: PermitRootLogin no"
else
    echo -e "1. ${RED}CREATE A SUDO USER immediately to avoid lockout${NC}"
    echo -e "2. Configure SSH key authentication for the new user"
    echo -e "3. Re-run this script to apply full security hardening"
fi
echo -e "3. Review security status: sudo /opt/review-platform/scripts/security-check.sh"
echo -e "4. Monitor logs: sudo journalctl -f"
echo -e "5. Check banned IPs: sudo fail2ban-client status sshd"
echo ""

echo -e "${GREEN}🛡️  Security hardening script completed successfully!${NC}"
# Development Server Git Setup Guide

This guide helps you set up SSH keys and Git access on your development server at **65.108.32.143**.

## 🔧 Quick Setup (Automated)

**First, update the repository URL in the script:**
```bash
# Edit the script to set your actual repository URL
nano scripts/setup-dev-git-access.sh
# Change REPO_URL to: git@github.com:yourusername/halbzeit-ai.git
```

**Then run the automated setup:**
```bash
# See what it would do
./scripts/setup-dev-git-access.sh --dry-run

# Actually run it
./scripts/setup-dev-git-access.sh
```

---

## 📋 Manual Setup (Step by Step)

If you prefer to do it manually, here are the exact steps:

### Step 1: SSH to Development Server
```bash
ssh root@65.108.32.143
```

### Step 2: Generate SSH Key on Development Server
```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -C "dev-server-halbzeit@$(hostname)" -f ~/.ssh/id_rsa -N ''

# Start SSH agent and add key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa

# Display the public key
cat ~/.ssh/id_rsa.pub
```

### Step 3: Add Public Key to GitHub
1. Copy the entire public key output from Step 2
2. Go to: https://github.com/settings/keys
3. Click **"New SSH key"**
4. Title: `Development Server - Halbzeit`
5. Paste the public key
6. Click **"Add SSH key"**

### Step 4: Configure Git on Development Server
```bash
# Set your Git credentials
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase false
```

### Step 5: Test GitHub SSH Connection
```bash
# Test SSH connection (this is supposed to "fail" with authentication message)
ssh -T git@github.com

# You should see: "Hi username! You've successfully authenticated..."
```

### Step 6: Clone Repository
```bash
# Create directory and clone
cd /opt
git clone git@github.com:yourusername/halbzeit-ai.git review-platform-dev

# Verify it worked
cd review-platform-dev
git status
git remote -v
```

### Step 7: Test Git Operations
```bash
# Test that you can pull without password
git pull origin main

# Test that you can push (make a small change first)
echo "# Development setup complete" >> DEV-SETUP.md
git add DEV-SETUP.md
git commit -m "Test development server git access"
git push origin main
```

---

## 🎯 Expected Results

After completion, you should have:

- ✅ SSH key pair on development server (`~/.ssh/id_rsa`, `~/.ssh/id_rsa.pub`)
- ✅ Public key added to your GitHub account
- ✅ Git configured with your credentials
- ✅ Repository cloned to `/opt/review-platform-dev`
- ✅ Ability to `git push` and `git pull` without entering passwords

---

## 🚨 Troubleshooting

### SSH Key Issues
```bash
# Check if SSH key exists
ls -la ~/.ssh/

# Check SSH agent
ssh-add -l

# Test GitHub connection
ssh -vT git@github.com
```

### Git Permission Issues
```bash
# Fix ownership
chown -R root:root /opt/review-platform-dev

# Check remote URL
cd /opt/review-platform-dev
git remote get-url origin
# Should be: git@github.com:yourusername/halbzeit-ai.git (not https://)
```

### Clone Issues
```bash
# If clone fails, check the repository URL
# Make sure you're using SSH format: git@github.com:user/repo.git
# Not HTTPS format: https://github.com/user/repo.git
```

---

## 📝 What This Enables

Once this is set up, you can:

1. **Work directly on the development server** with full Git access
2. **Run the database schema export scripts** 
3. **Set up the complete development environment**
4. **Use the CI/CD pipeline** to deploy between environments
5. **Have Claude work directly** with the development PostgreSQL database

This is a prerequisite for all the other development environment setup steps!
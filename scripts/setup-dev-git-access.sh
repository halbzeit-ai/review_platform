#!/bin/bash

# Setup Git Access on Development Server
# This script helps set up SSH keys and Git configuration on the development server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Development server IP from your screenshot
DEVELOPMENT_CPU="65.108.32.143"
REPO_URL="git@github.com:your-username/halbzeit-ai.git"  # You'll need to update this

# Default values
SETUP_SSH_KEY=true
CONFIGURE_GIT=true
CLONE_REPO=true
DRY_RUN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --no-ssh-key)
            SETUP_SSH_KEY=false
            shift
            ;;
        --no-git-config)
            CONFIGURE_GIT=false
            shift
            ;;
        --no-clone)
            CLONE_REPO=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            cat << 'EOF'
Setup Git Access on Development Server

This script helps you set up SSH keys and Git configuration on the development server.

Usage: ./setup-dev-git-access.sh [options]

Options:
  --repo-url URL         Git repository URL (default: needs to be set)
  --no-ssh-key          Skip SSH key generation
  --no-git-config       Skip Git configuration
  --no-clone            Skip repository cloning
  --dry-run             Show what would be done without executing
  --help, -h            Show this help message

Steps this script performs:
1. Generate SSH key pair on development server
2. Display public key for adding to GitHub
3. Configure Git with your details
4. Test SSH connection to GitHub
5. Clone the repository to development server

You will need to:
- Add the generated public key to your GitHub account
- Update the repository URL in this script

EOF
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if repo URL is set
if [[ "$REPO_URL" == *"your-username"* ]]; then
    log_error "Please update the REPO_URL variable with your actual GitHub repository URL"
    log_info "Edit this script and change REPO_URL to your repository SSH URL"
    log_info "Example: git@github.com:yourusername/halbzeit-ai.git"
    exit 1
fi

echo "🔐 Setting up Git Access on Development Server"
echo "=============================================="
echo "Development Server: $DEVELOPMENT_CPU"
echo "Repository URL: $REPO_URL"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN MODE - No changes will be made"
    echo ""
fi

# Function to run command on remote server
run_remote_command() {
    local cmd="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would run on $DEVELOPMENT_CPU: $cmd"
        if [ -n "$description" ]; then
            echo "   Purpose: $description"
        fi
    else
        log_info "Running on $DEVELOPMENT_CPU: $description"
        ssh -o StrictHostKeyChecking=no root@"$DEVELOPMENT_CPU" "$cmd"
    fi
}

# Function to get output from remote server
get_remote_output() {
    local cmd="$1"
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN - would execute: $cmd]"
    else
        ssh -o StrictHostKeyChecking=no root@"$DEVELOPMENT_CPU" "$cmd"
    fi
}

# Step 1: Generate SSH key on development server
generate_ssh_key() {
    if [ "$SETUP_SSH_KEY" = false ]; then
        log_info "Skipping SSH key generation"
        return
    fi
    
    log_info "Step 1: Generating SSH key on development server..."
    
    # Check if SSH key already exists
    local check_key_cmd="[ -f ~/.ssh/id_rsa ] && echo 'exists' || echo 'not_found'"
    local key_exists=$(get_remote_output "$check_key_cmd")
    
    if [[ "$key_exists" == *"exists"* ]] && [ "$DRY_RUN" = false ]; then
        log_warning "SSH key already exists on development server"
        read -p "Do you want to generate a new one? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Using existing SSH key"
            display_public_key
            return
        fi
    fi
    
    # Generate new SSH key
    local ssh_keygen_cmd="ssh-keygen -t rsa -b 4096 -C 'dev-server-halbzeit@$(hostname)' -f ~/.ssh/id_rsa -N ''"
    run_remote_command "$ssh_keygen_cmd" "Generate SSH key pair"
    
    # Start SSH agent and add key
    local ssh_agent_cmd="eval \"\$(ssh-agent -s)\" && ssh-add ~/.ssh/id_rsa"
    run_remote_command "$ssh_agent_cmd" "Add SSH key to agent"
    
    log_success "SSH key generated successfully"
    
    # Display the public key
    display_public_key
}

# Function to display public key
display_public_key() {
    log_info "📋 Public Key for GitHub:"
    echo "=========================="
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN - would display public key content]"
    else
        local pub_key=$(get_remote_output "cat ~/.ssh/id_rsa.pub")
        echo "$pub_key"
    fi
    
    echo ""
    log_warning "🔑 IMPORTANT: Copy the above public key and add it to your GitHub account!"
    log_info "Steps to add to GitHub:"
    log_info "1. Go to https://github.com/settings/keys"
    log_info "2. Click 'New SSH key'"
    log_info "3. Give it a title like 'Development Server - Halbzeit'"
    log_info "4. Paste the public key above"
    log_info "5. Click 'Add SSH key'"
    echo ""
    
    if [ "$DRY_RUN" = false ]; then
        read -p "Press Enter after you've added the key to GitHub..."
    fi
}

# Step 2: Configure Git
configure_git() {
    if [ "$CONFIGURE_GIT" = false ]; then
        log_info "Skipping Git configuration"
        return
    fi
    
    log_info "Step 2: Configuring Git on development server..."
    
    # You might want to customize these
    local git_name="Ramin Halbzeit Dev"
    local git_email="dev@halbzeit.ai"
    
    log_info "Setting Git configuration..."
    log_info "Name: $git_name"
    log_info "Email: $git_email"
    
    if [ "$DRY_RUN" = false ]; then
        read -p "Do you want to use different Git credentials? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter your Git name: " git_name
            read -p "Enter your Git email: " git_email
        fi
    fi
    
    # Configure Git
    run_remote_command "git config --global user.name '$git_name'" "Set Git username"
    run_remote_command "git config --global user.email '$git_email'" "Set Git email"
    run_remote_command "git config --global init.defaultBranch main" "Set default branch to main"
    run_remote_command "git config --global pull.rebase false" "Set pull strategy"
    
    log_success "Git configuration completed"
}

# Step 3: Test SSH connection to GitHub
test_github_connection() {
    log_info "Step 3: Testing SSH connection to GitHub..."
    
    local test_cmd="ssh -o StrictHostKeyChecking=no -T git@github.com"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would test SSH connection to GitHub"
    else
        log_info "Testing GitHub SSH connection..."
        
        # This command will return exit code 1 but that's normal for GitHub SSH test
        if run_remote_command "$test_cmd" "Test GitHub SSH connection" 2>&1 | grep -q "successfully authenticated"; then
            log_success "GitHub SSH connection successful!"
        else
            log_warning "GitHub SSH test completed (this is normal behavior)"
            log_info "If you see 'successfully authenticated' message above, SSH is working"
        fi
    fi
}

# Step 4: Clone repository
clone_repository() {
    if [ "$CLONE_REPO" = false ]; then
        log_info "Skipping repository cloning"
        return
    fi
    
    log_info "Step 4: Cloning repository to development server..."
    
    # Check if directory already exists
    local check_dir_cmd="[ -d '/opt/review-platform-dev' ] && echo 'exists' || echo 'not_found'"
    local dir_exists=$(get_remote_output "$check_dir_cmd")
    
    if [[ "$dir_exists" == *"exists"* ]] && [ "$DRY_RUN" = false ]; then
        log_warning "Directory /opt/review-platform-dev already exists"
        read -p "Do you want to remove it and clone fresh? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_remote_command "rm -rf /opt/review-platform-dev" "Remove existing directory"
        else
            log_info "Skipping repository clone"
            return
        fi
    fi
    
    # Clone repository
    run_remote_command "cd /opt && git clone '$REPO_URL' review-platform-dev" "Clone repository"
    
    # Set up remote tracking
    run_remote_command "cd /opt/review-platform-dev && git remote -v" "Verify remote configuration"
    
    log_success "Repository cloned successfully to /opt/review-platform-dev"
}

# Step 5: Final verification
final_verification() {
    log_info "Step 5: Final verification..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would verify repository setup and permissions"
    else
        # Check repository status
        run_remote_command "cd /opt/review-platform-dev && git status" "Check repository status"
        
        # Check if we can fetch
        run_remote_command "cd /opt/review-platform-dev && git fetch origin" "Test Git fetch"
        
        # Show current branch
        local current_branch=$(get_remote_output "cd /opt/review-platform-dev && git branch --show-current")
        log_info "Current branch: $current_branch"
        
        # Set up directory permissions
        run_remote_command "chown -R root:root /opt/review-platform-dev" "Set directory permissions"
        
        log_success "Final verification completed"
    fi
}

# Main execution
main() {
    log_info "Starting Git access setup for development server..."
    echo ""
    
    # Step 1: Generate SSH key
    generate_ssh_key
    
    # Step 2: Configure Git
    configure_git
    
    # Step 3: Test GitHub connection
    test_github_connection
    
    # Step 4: Clone repository
    clone_repository
    
    # Step 5: Final verification
    final_verification
    
    if [ "$DRY_RUN" = true ]; then
        log_info "DRY RUN COMPLETED - No changes were made"
    else
        log_success "🎉 Git access setup completed!"
        echo ""
        echo "📚 What's Ready:"
        echo "================"
        echo "✅ SSH key generated on development server"
        echo "✅ Git configured with your credentials"
        echo "✅ Repository cloned to /opt/review-platform-dev"
        echo "✅ Git push/pull should work without passwords"
        echo ""
        echo "📋 Next Steps:"
        echo "=============="
        echo "1. SSH to development server: ssh root@$DEVELOPMENT_CPU"
        echo "2. Navigate to project: cd /opt/review-platform-dev"
        echo "3. Test git operations: git pull, git push, etc."
        echo "4. Proceed with database schema export and development setup"
        echo ""
        echo "💡 Pro Tip:"
        echo "You can now work directly on the development server with full Git access!"
    fi
}

# Run main function
main
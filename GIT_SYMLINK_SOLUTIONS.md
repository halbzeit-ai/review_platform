# Git + Symlink Solutions for Zero-Downtime Frontend

## The Problem
Git and symlinks don't play well together, especially when:
- `frontend/build` is sometimes a directory, sometimes a symlink
- Files get "lost" behind symlinks causing `git stash` failures
- Commits become messy with symlink state changes

## Solution Options (Pick One)

### 🏆 **Option 1: Exclude Build Directory from Git (Recommended)**

This is the cleanest solution - build artifacts shouldn't be in Git anyway.

```bash
# Add to .gitignore
echo "frontend/build*" >> .gitignore
echo "frontend/build_*" >> .gitignore

# Remove build directory from Git tracking
git rm -r --cached frontend/build* 2>/dev/null || true
git add .gitignore
git commit -m "Exclude frontend build directories from Git tracking

- Build artifacts should not be versioned
- Prevents symlink conflicts with zero-downtime deployment
- Each environment builds its own optimized version"
```

### 🔧 **Option 2: Git Hooks for Smart Handling**

Automatically handle symlinks during Git operations:

```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Handle symlinks before commit

# If build is a symlink, temporarily remove it from staging
if [ -L "frontend/build" ]; then
    git reset HEAD frontend/build 2>/dev/null || true
fi

# Remove any build_* directories from staging
git reset HEAD frontend/build_* 2>/dev/null || true
EOF

chmod +x .git/hooks/pre-commit
```

### 🛠️ **Option 3: Enhanced Build Script with Git Safety**

Modify the build script to be Git-aware:

```bash
# Add to build-frontend.sh before deployment
echo -e "${YELLOW}🔍 Checking Git status...${NC}"

# Stash any uncommitted changes safely
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}📦 Stashing uncommitted changes...${NC}"
    
    # Remove problematic symlinks first
    if [ -L "build" ]; then
        git rm --cached build 2>/dev/null || true
    fi
    
    git stash push -u -m "Auto-stash before build $(date)"
fi
```

### 🚀 **Option 4: Separate Build Directory Structure**

Move builds completely outside the Git repo:

```bash
# Modify build script to use external directory
BUILD_BASE="/opt/builds/review-platform"
mkdir -p $BUILD_BASE

# In nginx config, point to external builds
location / {
    root /opt/builds/review-platform/build;
    try_files $uri $uri/ /index.html;
}
```

## 🎯 **Recommended Implementation**

**Immediate Fix (5 minutes):**
```bash
# 1. Add build directories to .gitignore
echo -e "\n# Frontend build artifacts\nfrontend/build*\nfrontend/build_*" >> .gitignore

# 2. Remove from Git tracking
git rm -r --cached frontend/build* 2>/dev/null || true

# 3. Commit the change
git add .gitignore
git commit -m "Exclude frontend builds from Git to prevent symlink conflicts"
```

**Long-term Enhancement:**
- Use Option 3 to make build script Git-aware
- Consider Option 4 for complete separation

## 🔄 **Emergency Recovery Commands**

When Git gets stuck with symlinks:

```bash
# Force reset problematic symlinks
git rm --cached frontend/build* 2>/dev/null || true
git reset --hard HEAD

# If stash is stuck:
git stash drop  # Only if you're sure!

# Nuclear option (saves uncommitted work first):
git add . 2>/dev/null || true
git commit -m "WIP: Save work before symlink reset" 2>/dev/null || true
git reset --hard HEAD~1  # If you just made the WIP commit
```

## ✅ **Benefits of Option 1 (Exclude from Git)**

1. **Clean Repository**: Build artifacts aren't versioned (industry standard)
2. **No Symlink Conflicts**: Git never sees the symlinks
3. **Environment Flexibility**: Each environment builds optimized for its needs
4. **Faster Operations**: Smaller repository, faster clones/pulls
5. **Zero Maintenance**: No special handling needed

## 🎭 **Production Workflow After Fix**

```bash
# Development
git add . && git commit -m "Feature changes"
git push origin main

# Production deployment
git pull origin main
./scripts/build-frontend.sh production  # Builds outside Git
# Zero-downtime symlink switching continues to work perfectly
```

This completely eliminates the Git+symlink friction while preserving your excellent zero-downtime deployment! 🎉
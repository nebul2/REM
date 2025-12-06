# Setting Up Dual Repository Workflow (Personal + GOS Org)

## Overview

You want to:
1. Keep your personal repo (`dom-robinson/stats`) as the **development/main** repository
2. Have a GOS organization repo that can receive updates from yours
3. Maintain a connection so GOS can pull updates when ready

## Recommended Approach: Dual Remote Setup

This is the cleanest approach that gives you full control while allowing GOS to receive updates.

### Step 1: Create Repository in GOS Organization

1. Go to the GOS GitHub organization
2. Create a new repository:
   - Name: `gos-rem` or `stats` (your choice)
   - Description: "GOS Remote Energy Measurement System"
   - Make it **Public** or **Private** (your preference)
   - **Don't** initialize with README, .gitignore, or license (we'll push existing code)

### Step 2: Add GOS Repo as a Remote

In your personal repo, add the GOS repo as a second remote:

```bash
cd /path/to/stats
git remote add gos git@github.com:greeningofstreaming/gos-rem.git
# Or whatever the GOS repo URL is

# Verify both remotes exist
git remote -v
# Should show:
# origin    git@github.com:dom-robinson/stats.git (fetch)
# origin    git@github.com:dom-robinson/stats.git (push)
# gos       git@github.com:greeningofstreaming/gos-rem.git (fetch)
# gos       git@github.com:greeningofstreaming/gos-rem.git (push)
```

### Step 3: Initial Push to GOS Repo

Push your current code to GOS:

```bash
# Push master branch and tags to GOS repo
git push gos master
git push gos --tags

# Now GOS has the v1.0 release
```

### Step 4: Set Up Branch Protection (Optional but Recommended)

In the GOS repo settings:
1. Go to Settings → Branches
2. Add rule for `master` branch
3. Require pull requests for merges (prevents accidental direct pushes)
4. Allow pushes from organization admins (you)

### Step 5: Workflow for Updates

**For regular development:**
```bash
# Work on your personal repo as normal
git add .
git commit -m "New feature"
git push origin master
```

**When you want to release to GOS:**
```bash
# Push the same commits to GOS repo
git push gos master

# Or push specific branches/tags
git push gos master --tags
```

### Step 6: Make it Easy with Git Aliases

Add aliases to simplify pushing to both repos:

```bash
# Add to your ~/.gitconfig or run:
git config --global alias.pushall '!git push origin "$@" && git push gos "$@"'
git config --global alias.pushall-tags '!git push origin --tags && git push gos --tags'

# Now you can push to both with:
git pushall master
git pushall-tags
```

## Alternative: Automated Sync with GitHub Actions

If you want automatic syncing, you can set up a GitHub Action in your personal repo that automatically pushes to GOS when you tag a release.

### Create `.github/workflows/sync-to-gos.yml`:

```yaml
name: Sync to GOS Organization

on:
  push:
    tags:
      - 'v*'  # Trigger on version tags (v1.0, v1.1, etc.)

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Push to GOS repo
        run: |
          git remote add gos git@github.com:greeningofstreaming/gos-rem.git || true
          git push gos master --tags
        env:
          GITHUB_TOKEN: ${{ secrets.GOS_SYNC_TOKEN }}
```

**To set this up:**
1. Create a Personal Access Token (Settings → Developer settings → Personal access tokens)
2. Give it `repo` permissions
3. Add it as a secret in your personal repo: Settings → Secrets → Actions → `GOS_SYNC_TOKEN`
4. When you create a tag (like `v1.1`), it will automatically sync to GOS

## Alternative: Transfer + Fork Approach

If you want GOS to "own" the official repo:

1. **Transfer** your repo to GOS organization (Settings → Transfer ownership)
2. **Fork** it back to your personal account
3. Develop on your fork
4. Create Pull Requests to the GOS repo when ready to release
5. GOS admins can review and merge

**Pros:**
- GOS owns the "official" repo
- Clear separation between development and production
- Pull requests provide review process

**Cons:**
- You lose direct push access (unless you're an admin)
- More workflow overhead for quick updates

## Recommendation

**Use the Dual Remote Setup** (Option 1) because:
- ✅ You keep full control of your development repo
- ✅ Simple to push updates to GOS when ready
- ✅ GOS can still contribute via pull requests to your repo
- ✅ Easy to set up and maintain
- ✅ No need for complex workflows

**Then add GitHub Actions** (Option 2) if you want automatic syncing on releases.

## Permissions Setup

Since you're an admin on both accounts:

1. In GOS repo: Ensure you have write/admin access
2. In your personal repo: You already have full access
3. Consider adding other GOS members as collaborators if needed

## Next Steps

1. Create the repo in GOS organization
2. Add it as a remote: `git remote add gos <gos-repo-url>`
3. Push initial code: `git push gos master --tags`
4. Update README to mention GOS organization repo
5. Set up aliases or GitHub Actions for easy syncing

## Testing the Setup

```bash
# Make a test change
echo "# Test" >> TEST.md
git add TEST.md
git commit -m "Test dual remote setup"
git push origin master      # Push to your repo
git push gos master         # Push to GOS repo

# Check both repos on GitHub - both should have the change
```


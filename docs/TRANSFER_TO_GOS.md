# Transferring GOS REM Repository to Greening of Streaming Organization

## Overview

This document explains how to transfer the GOS REM repository from your personal GitHub account (`dom-robinson/stats`) to the Greening of Streaming organization.

## Prerequisites

- Admin access to the Greening of Streaming GitHub organization
- Your personal GitHub account with the current repository
- Confirmation that the organization should own this repository

## Step 1: Prepare the Repository

### Clean Up

1. **Review all files** - Ensure no sensitive data is committed:
   ```bash
   # Check for secrets
   grep -r "password\|secret\|token" --exclude-dir=.git --exclude="*.md" .
   ```

2. **Ensure .env is in .gitignore**:
   ```bash
   grep "^\.env$" .gitignore || echo ".env" >> .gitignore
   ```

3. **Final commit and push**:
   ```bash
   git add .
   git commit -m "Final commit before transfer to GOS organization"
   git push origin main
   ```

### Create/Update Documentation

1. **Update README.md** with organization branding
2. **Add LICENSE file** if needed
3. **Add CONTRIBUTING.md** if you want contributions
4. **Update repository description** on GitHub

## Step 2: Transfer Repository via GitHub UI

### Option A: Transfer Repository (Recommended)

1. Go to your repository: https://github.com/dom-robinson/stats
2. Click **Settings** tab
3. Scroll down to **Danger Zone**
4. Click **Transfer ownership**
5. Enter the new owner: `greeningofstreaming` (or exact org name)
6. Type the repository name to confirm: `stats`
7. Click **I understand, transfer this repository**

**Note**: You may want to rename it to something like `gos-rem` or `gos-remote-energy-measurement` before or after transfer.

### Option B: Create New Repository in Organization

1. Create new repository in GOS organization: `greeningofstreaming/gos-rem`
2. Add your personal account as a collaborator (or maintainer)
3. Push code to new repository:
   ```bash
   git remote set-url origin git@github.com:greeningofstreaming/gos-rem.git
   git push -u origin main
   ```

## Step 3: Post-Transfer Steps

### Update Repository Settings

1. **Description**: Add clear description of what the project does
2. **Topics/Tags**: Add relevant tags (energy, monitoring, streaming, etc.)
3. **Website**: Add link to GOS website if applicable
4. **Visibility**: Set to Public or Private based on org policy

### Update Documentation

1. **README.md**: Update with organization branding
   - Replace personal references with organization references
   - Update author/contact information
   - Add organization logo if available

2. **Update repository references** in all documentation files:
   ```bash
   # Find all references to old repo
   grep -r "dom-robinson/stats" .
   
   # Replace with new repo path
   sed -i '' 's/dom-robinson\/stats/greeningofstreaming\/gos-rem/g' *.md
   ```

### Set Up Organization Permissions

1. **Teams**: Add appropriate teams (developers, maintainers, etc.)
2. **Collaborators**: Add key people who need access
3. **Branch Protection**: Set up branch protection rules for main branch
4. **Actions/CI**: Set up GitHub Actions if needed (for automated testing/deployment)

### Update Deployment Instructions

1. Update all clone URLs in documentation:
   ```bash
   # OLD
   git clone git@github.com:dom-robinson/stats.git
   
   # NEW
   git clone git@github.com:greeningofstreaming/gos-rem.git
   ```

2. Update any CI/CD pipelines
3. Update any webhooks or integrations

## Step 4: Notify Team

Send a message to the GOS team:

```
Subject: GOS REM Repository Now Available in Organization

Hi Team,

The GOS Remote Energy Measurement (REM) system repository has been transferred to the Greening of Streaming organization.

Repository: https://github.com/greeningofstreaming/gos-rem

This repository contains:
- Docker-based energy monitoring system
- Integration with TP-Link Tapo P110 smart plugs
- InfluxDB time-series database
- Grafana dashboards
- Admin UI for data exploration

Quick start: See DEPLOYMENT_SIMPLE.md in the repository.

Please review and let me know if you need access or have questions.

Thanks!
```

## Step 5: Archive Personal Repository (Optional)

After confirming the transfer worked:

1. Go to your old repository: https://github.com/dom-robinson/stats
2. **Settings** → **Danger Zone** → **Archive this repository**
3. Or add a note in README pointing to new location:
   ```markdown
   # ⚠️ This repository has moved
   
   This repository has been transferred to the Greening of Streaming organization.
   
   **New location**: https://github.com/greeningofstreaming/gos-rem
   ```

## Alternative: Fork Instead of Transfer

If you want to keep a personal copy:

1. Keep your repository as-is
2. Have the organization fork it
3. Make the fork the primary development repository
4. Your repo can stay as a mirror/backup

## Repository Naming Considerations

Current name: `stats`  
Suggested name: `gos-rem` or `gos-remote-energy-measurement`

To rename after transfer:
1. Go to repository Settings
2. Scroll to Repository name
3. Change name
4. Update all references (see Step 3 above)

## Checklist

- [ ] Repository cleaned of sensitive data
- [ ] .env is in .gitignore
- [ ] Documentation updated
- [ ] Repository transferred to organization
- [ ] Repository settings configured
- [ ] Team permissions set up
- [ ] Clone URLs updated in documentation
- [ ] Team notified
- [ ] Old repository archived/redirected

## Post-Transfer Support

After transfer, you may want to:
- Set up issue templates
- Add pull request templates
- Configure project board
- Set up automated releases
- Add CODE_OF_CONDUCT.md
- Add SECURITY.md

## Questions?

If you need help with any step, the GitHub documentation is excellent:
- https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository


# Branch Protection Setup Instructions

This document provides instructions for setting up branch protection rules for the OpenHands repository.

## Required Branch Protection Settings

### For `main` branch:

1. **Require pull request reviews before merging**
   - Required number of reviewers: 1
   - Dismiss stale reviews when new commits are pushed: ✅
   - Require review from code owners: ✅

2. **Require status checks to pass before merging**
   - Require branches to be up to date before merging: ✅
   - Required status checks:
     - `Lint / lint-frontend`
     - `Lint / lint-backend`
     - `Run Python Tests / test-on-linux`
     - `Run Frontend Unit Tests / test-frontend`
     - `Run UI Component Build / ui-build`
     - `VSCode Extension CI / build-extension`

3. **Restrict pushes that create files**
   - Restrict pushes to matching branches: ✅

4. **Do not allow bypassing the above settings**
   - Allow force pushes: ❌
   - Allow deletions: ❌

### For `development` branch:

1. **Require pull request reviews before merging**
   - Required number of reviewers: 1
   - Dismiss stale reviews when new commits are pushed: ✅
   - Require review from code owners: ✅

2. **Require status checks to pass before merging**
   - Require branches to be up to date before merging: ✅
   - Required status checks:
     - `Lint / lint-frontend`
     - `Lint / lint-backend`
     - `Run Python Tests / test-on-linux`
     - `Run Frontend Unit Tests / test-frontend`
     - `Run UI Component Build / ui-build`
     - `VSCode Extension CI / build-extension`

3. **Restrict pushes that create files**
   - Restrict pushes to matching branches: ✅

4. **Do not allow bypassing the above settings**
   - Allow force pushes: ❌
   - Allow deletions: ❌

## How to Configure

1. Go to the repository settings: `https://github.com/kmatskevich/OpenHands/settings`
2. Navigate to "Branches" in the left sidebar
3. Click "Add rule" for each branch (`main` and `development`)
4. Configure the settings as specified above

## Verification

After setting up branch protection:
1. Try to push directly to `main` or `development` - should be blocked
2. Create a test PR and verify status checks are required
3. Verify that PRs cannot be merged without passing status checks

## CI Workflows Updated

The following CI workflows have been updated to run on both `main` and `development` branches:
- Lint workflow (`.github/workflows/lint.yml`)
- Python tests workflow (`.github/workflows/py-tests.yml`)
- Frontend unit tests workflow (`.github/workflows/fe-unit-tests.yml`)
- UI build workflow (`.github/workflows/ui-build.yml`)
- VSCode extension build workflow (`.github/workflows/vscode-extension-build.yml`)

# Branch Protection Configuration

## Setting Up Required Checks

To make the comprehensive integration check workflow a required check for PR merging, follow these steps:

### 1. Navigate to Repository Settings
- Go to your repository on GitHub
- Click on "Settings" tab
- Navigate to "Branches" in the left sidebar

### 2. Add Branch Protection Rule
- Click "Add rule" or edit existing rule for `main` branch
- Set branch name pattern to `main`

### 3. Configure Protection Settings
Enable the following options:

#### Required Status Checks
- ✅ **Require status checks to pass before merging**
- ✅ **Require branches to be up to date before merging**

Search and add these required status checks:
- `Integration Check Status` - The final status check that validates all jobs
- `Unit Tests (Python 3.12)` - Primary Python version unit tests
- `Code Quality Checks` - Linting and formatting checks

#### Additional Recommended Settings
- ✅ **Require a pull request before merging**
- ✅ **Dismiss stale pull request approvals when new commits are pushed**
- ✅ **Include administrators** (optional but recommended)

### 4. Save Changes
Click "Create" or "Save changes" to apply the branch protection rules.

## Workflow Status Checks

The `integration-check.yml` workflow provides these status checks:

### Required Checks (Must Pass)
1. **Integration Check Status** - Overall workflow status
2. **Unit Tests** - Runs on Python 3.9, 3.10, 3.11, 3.12
3. **Code Quality Checks** - Ruff linting and MyPy type checking

### Informational Checks
1. **Integration Tests** - Real API testing (requires secrets)
2. **Performance Tests** - Benchmark comparisons
3. **Compatibility Tests** - Cross-feature validation
4. **Security Scan** - Vulnerability detection
5. **Test Results Summary** - Aggregated test report

## Secrets Configuration

For full functionality, configure these repository secrets:

1. `INTERCOM_TEST_TOKEN` - Intercom API token for integration tests
2. `INTERCOM_TEST_WORKSPACE_ID` - Workspace ID for integration tests

Navigate to Settings → Secrets and variables → Actions to add these.

## Monitoring Workflow Performance

The workflow includes:
- Test result comments on PRs
- Coverage reports with threshold checking (80% default)
- Performance regression detection (10% tolerance)
- JUnit test result artifacts
- Security vulnerability scanning

All results are automatically posted as PR comments for easy review.
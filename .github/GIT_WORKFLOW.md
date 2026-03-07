# Git Workflow Best Practices

This guide demonstrates proper Git workflows for academic and professional CI/CD practices.

## 🌿 Branching Strategy

### Branch Types

```
main (production)              ← protected, requires PR
  ├── develop (integration)    ← active development
  ├── feature/xyz              ← new features
  ├── fix/abc                  ← bug fixes
  └── hotfix/urgent            ← critical production fixes
```

### Branch Naming Convention

```bash
# Feature branches
feature/user-authentication
feature/add-monitoring-dashboard
feature/implement-caching

# Bug fix branches  
fix/vault-connection-error
fix/jwt-token-expiry
fix/frontend-401-handling

# Hotfix branches
hotfix/critical-security-patch
hotfix/database-connection-pool
```

## 📝 Daily Workflow

### 1. Start Your Day

```bash
# Update your local main branch
git checkout main
git pull origin main

# Create a new feature branch
git checkout -b feature/add-rate-limiting

# Verify you're on the right branch
git branch --show-current
```

### 2. Make Changes with Meaningful Commits

```bash
# Stage specific files (recommended)
git add backend/ai_engine/views.py backend/ai_engine/rag_logic.py

# Or stage all changes
git add .

# Commit with descriptive message
git commit -m "feat(backend): implement rate limiting for API endpoints

- Add Redis-based rate limiter middleware
- Configure 100 requests/minute per user
- Add rate limit headers in responses
- Update API documentation

Addresses: #45"
```

### 3. Push and Create Pull Request

```bash
# Push your branch
git push origin feature/add-rate-limiting

# Create PR via GitHub CLI (optional)
gh pr create \
  --title "feat: Add rate limiting for API endpoints" \
  --body "Implements rate limiting using Redis. Closes #45" \
  --base main
```

## 🎯 Commit Message Examples

### Feature Addition
```bash
git commit -m "feat(rag): add batch processing for document ingestion

- Process documents in batches of 80 chunks
- Add 62-second delay between batches to respect rate limits
- Implement progress tracking with Celery
- Add tests for batch processing logic

Performance: Reduces rate limit errors by 95%
Closes #23"
```

### Bug Fix
```bash
git commit -m "fix(auth): resolve JWT token refresh loop

- Fix infinite refresh loop in api.js
- Add request queuing during token refresh
- Prevent concurrent refresh requests
- Update error handling for 401 responses

Before: Users logged out after 5 minutes
After: Seamless 2-hour sessions with auto-refresh
Fixes #34"
```

### Documentation
```bash
git commit -m "docs: add comprehensive API testing guide

- Document all 11 API test scenarios
- Add PowerShell test script examples
- Include expected responses and error codes
- Add troubleshooting section

Helps with: Developer onboarding and QA testing"
```

### Infrastructure Changes
```bash
git commit -m "ci(pipeline): migrate from ACR to Docker Hub

- Update GitHub Actions to use Docker Hub
- Configure build caching for faster builds
- Add automated deployment to Azure Container Apps
- Implement security scanning with Trivy

Benefits: Eliminates ACR costs, faster builds
Related: #56"
```

### Refactoring
```bash
git commit -m "refactor(frontend): centralize API client with auto-refresh

- Create lib/api.js with axios instance
- Add request interceptor for JWT attachment
- Add response interceptor for token refresh
- Update all components to use centralized client

Impact: Eliminates code duplication, improves maintainability
No functional changes"
```

## 🔄 Pull Request Workflow

### Creating a Quality PR

```markdown
## 🎯 Purpose
This PR implements dual-agent RAG verification system for hallucination detection.

## 📋 Changes
- Added Generator Agent (Gemini 2.0 Flash)
- Added Critic Agent (Groq/Llama-3)
- Implemented faithfulness scoring (0-1 scale)
- Added retry logic for rate limit handling
- Updated models to latest versions

## 🧪 Testing
- [x] All 11 API tests pass
- [x] Verified locally with test-api.ps1
- [x] Tested with 64-chunk Cilium PDF
- [x] Faithfulness score: 1.0 on test queries

## 📸 Screenshots
[Attach relevant screenshots]

## 📚 Documentation
- Updated README.md with new architecture
- Added ARCHITECTURE.md diagram
- Updated API_SPEC.md with new endpoints

## ✅ Checklist
- [x] Code follows project conventions
- [x] Tests added/updated
- [x] Documentation updated
- [x] No security vulnerabilities
- [x] Commits are meaningful and atomic

## 🔗 Related Issues
Closes #12, #15
```

### Responding to Review Comments

**Scenario**: Reviewer requests changes

```bash
# Make the requested changes
git add .
git commit -m "refactor: address PR review comments

- Simplify error handling in call_gemini()
- Add type hints to get_verified_answer()
- Extract magic numbers to constants
- Improve docstring clarity"

# Push to the same branch
git push origin feature/add-rate-limiting
```

**In GitHub**: Reply to each comment
```markdown
> Consider extracting this to a constant

✅ Done! Moved to `MAX_RETRIES` constant in line 42.

> Add error handling here

✅ Added try-catch block with specific exception handling.

> This could be simplified

Good catch! Refactored to use list comprehension. Committed in abc1234.
```

## 🔥 Common Scenarios

### Sync with Main (Keep Branch Updated)

```bash
# From your feature branch
git checkout feature/add-monitoring

# Fetch latest changes
git fetch origin

# Rebase on main (preferred) or merge
git rebase origin/main

# Or if you prefer merge
git merge origin/main

# Push (force push if you rebased)
git push origin feature/add-monitoring --force-with-lease
```

### Fixing Mistakes

**Typo in last commit message**:
```bash
git commit --amend -m "feat: correct commit message"
git push --force-with-lease
```

**Need to add more changes to last commit**:
```bash
git add forgotten-file.py
git commit --amend --no-edit
git push --force-with-lease
```

**Accidentally committed to main**:
```bash
# Create branch from current position
git branch feature/my-changes

# Reset main to origin
git reset --hard origin/main

# Switch to your new branch
git checkout feature/my-changes
git push origin feature/my-changes
```

### Squashing Commits Before Merge

```bash
# Interactive rebase last 3 commits
git rebase -i HEAD~3

# In editor, change 'pick' to 'squash' for commits to combine
# Save and close
# Edit the combined commit message
# Force push
git push --force-with-lease
```

## 📊 Demonstrating Activity

### Weekly Activity Goals

**Minimum for Academic Evaluation**:
- 5+ meaningful commits per week
- 2+ pull requests per week
- Review 2+ teammate PRs per week
- Update documentation regularly
- Respond to feedback within 24 hours

### Example Weekly Schedule

**Monday**:
```bash
# Sprint planning - create feature branches
git checkout -b feature/add-monitoring-dashboard
# Make initial commit
git commit -m "feat(monitoring): scaffold monitoring dashboard component"
git push origin feature/add-monitoring-dashboard
gh pr create --draft
```

**Tuesday-Thursday**:
```bash
# Daily progress commits
git commit -m "feat(monitoring): add real-time metrics display"
git commit -m "feat(monitoring): integrate Chart.js for visualizations"
git commit -m "feat(monitoring): add filtering and date range selection"
git push
```

**Friday**:
```bash
# Complete PR, request review
gh pr ready  # Convert draft to ready
gh pr edit --add-reviewer teammate1,teammate2

# Review teammate PRs
gh pr checkout 42
# Test locally
gh pr review --approve -b "LGTM! Tested locally, all tests pass."
```

## 🛡️ CI/CD Integration

### Trigger Pipeline on Push

```bash
# Every push to main triggers full pipeline
git push origin main

# Watch pipeline progress
gh run watch
```

### Check Pipeline Status

```bash
# View recent workflow runs
gh run list --limit 5

# View specific run details
gh run view 123456789

# Download artifacts
gh run download 123456789
```

### Fix Failed Pipeline

```bash
# Pipeline failed on test stage
# Fix the issue locally
git commit -m "fix(tests): resolve failing test in test_rag_logic.py"
git push

# GitHub Actions automatically re-runs the pipeline
```

## 📈 Git Statistics (Good for Evaluation)

### Check Your Contribution Stats

```bash
# Your commits this month
git log --author="Your Name" --since="1 month ago" --oneline | wc -l

# Lines added/removed
git log --author="Your Name" --since="1 month ago" --stat

# Contribution summary
git shortlog --summary --numbered --since="1 month ago"
```

### Generate Activity Report

```bash
# Create monthly activity report
git log --author="Your Name" \
  --since="1 month ago" \
  --pretty=format:"- %s (%h)" \
  --reverse > MONTHLY_ACTIVITY.md
```

## ✅ Pre-Push Checklist

Before every push:
- [ ] Code is properly formatted
- [ ] All tests pass locally
- [ ] Commit messages are meaningful
- [ ] No sensitive data in commits (API keys, passwords)
- [ ] Documentation is updated
- [ ] Branch is up to date with main

## 🎓 Academic Best Practices Summary

1. **Commit Often**: Small, atomic commits > large monolithic commits
2. **Write Clear Messages**: Explain "why", not just "what"
3. **Use Branches**: Never commit directly to main
4. **Create PRs**: Show collaborative workflow
5. **Review Code**: Actively participate in code reviews
6. **Document**: Update docs with every feature
7. **Respond Promptly**: Address feedback within 24 hours
8. **Follow Conventions**: Use standard commit formats
9. **Show Progress**: Regular activity throughout the sprint
10. **Be Professional**: Treat it like a real team project

## 📚 Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Best Practices](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project)
- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)
- [Writing Better Commit Messages](https://chris.beams.io/posts/git-commit/)

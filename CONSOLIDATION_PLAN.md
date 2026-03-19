# GitHub Actions CI/CD Consolidation Plan

## Current State (7 workflows) ❌

1. `ci.yml` — Test backend + frontend + Docker build checks
2. `ci-cd.yml` — Full pipeline: validate → test → build → push → deploy
3. `deploy-aca.yml` — Manual ACA deployment
4. `simple-deploy.yml` — Simplified deploy
5. `backend-security.yml` — Trivy backend scans
6. `frontend-security.yml` — Frontend security
7. `security-remediation-check.yml` — Remediation tracking

## Recommended State (1 workflow) ✅

**Single unified pipeline:** `.github/workflows/deploy.yml`

### When it runs:
- **On PR to main**: Run tests + security scans (no deploy)
- **On merge to main**: Run tests → security scans → build → push to ACR → deploy to ACA

### Jobs:
1. `validate` — Check required secrets/variables
2. `test` — Run Django + frontend tests
3. `security` — Trivy scans (backend + frontend)
4. `build-and-push` — Docker build → push to ACR
5. `deploy` — Deploy to ACA

## Benefits
- ✅ Single source of truth
- ✅ Easier to maintain
- ✅ Clear execution flow
- ✅ Better for portfolio/interview review

## Migration Steps
1. Keep current workflows as backup
2. Create new `deploy.yml`
3. Test on PR first
4. Once validated, delete old workflows (except temporarily)
5. Commit single consolidated workflow

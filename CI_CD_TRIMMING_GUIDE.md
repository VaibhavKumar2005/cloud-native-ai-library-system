# CI/CD Pipeline Trimming Guide for VeriRAG with Terraform IaC

## Executive Summary

Your Terraform `main.tf` already provisions all infrastructure (ACR, ACA, PostgreSQL, Redis, networking). Your CI/CD pipeline's **only job** is: build image → push to ACR → trigger ACA revision update.

**Current state:** 4 jobs, ~45 minutes, multiple redundant checks.  
**Target state:** 3 jobs, ~10 minutes, single source of truth (Terraform for infrastructure, Pipeline for deployments).

---

## Sections to Remove from CI/CD

### ❌ REMOVE ENTIRELY (No Value = Noise)

| Section | Why Remove | Impact |
| --- | --- | --- |
| **validate-environment job** | Terraform guarantees ACR, ACA, databases exist. Nothing to validate at runtime. | Saves ~2 min, reduces failure points |
| **security job (Trivy)** | Not tied to infrastructure. Useful as scheduled weekly scan later, not on every push. | Saves ~15 min per run |
| **Pre-deployment health checks** | `az containerapp show` loops verify apps exist — but Terraform created them. Redundant. | Saves ~30 sec, one less thing to break |
| **Collect logs on failure** step | Production ops concern, not CI/CD. Debug via `az containerapp logs` locally when needed. | Saves cleanup time |
| **Artifact uploads** (test results, coverage) | Nice visual dashboard, not needed for solo project or initial stages. Keep if team grows. | Reduces storage, faster cleanup |
| **45-second sleep** before health checks | Replace with proper retry logic or remove entirely. Sleeping doesn't fix things. | Saves 45 sec |

### ✅ KEEP & SIMPLIFY

| Section | How to Simplify | Why Keep |
| --- | --- | --- |
| **test job** | Keep as-is (unit tests stay important). | Catch bugs before building image |
| **build-push job** | Merge validate step into it. Use GitHub Variables, not hardcoded names. | Core value: build & push |
| **deploy-aca job** | Remove pre-checks. Just run three `az containerapp update` calls. | Trigger ACA to use new image |
| **OIDC login** | Keep this. Use `az acr login` instead of credential discovery. | Secure, no secret management |

---

## What Terraform Owns (Pipeline Leaves Alone)

```
Terraform provisions:
├── Resource Group
├── Azure Container Registry (ACR)
├── PostgreSQL (database + firewall)
├── Redis (cache)
├── Container Apps Environment
├── Backend Container App (ca-verirag-dev-backend)
├── Celery Container App (ca-verirag-dev-celery)
└── Frontend Container App (ca-verirag-dev-frontend)

Pipeline's job:
├── Build backend image → push to ACR
├── Build frontend image → push to ACR
├── Tell each ACA to use new image tag
└── Done. Terraform handles the rest.
```

---

## The Prompt for Copilot Haiku

Copy this exactly and paste into Copilot Chat along with your current `deploy.yml` file:

```
You are a GitHub Actions expert. Refactor this CI/CD workflow to remove infrastructure validation cruft, given that Terraform IaC owns all resource provisioning.

CONTEXT:
- Project: VeriRAG (Django backend + React frontend + Celery worker)
- Infrastructure: Fully provisioned by Terraform (main.tf)
  * ACR, ACA, databases, networks all created by Terraform
  * Deterministic names: ca-verirag-dev-backend, ca-verirag-dev-frontend, ca-verirag-dev-celery
  * ACR location: ${{ vars.ACR_NAME }}.azurecr.io (set in GitHub repo variables)
  * Constraint: Pipeline runs AFTER Terraform (infra always exists)

TASK:
1. DELETE the entire `security` job (Trivy scanning).

2. MERGE the `validate-environment` job into `build-push` as the first step.
   - Output the short SHA for image tagging.
   - Remove all app existence checks — Terraform guarantees they exist.

3. DELETE the `pre-deployment-checks` step from `deploy-aca`.
   - No `az containerapp show` loops.
   - Terraform created the apps; they exist.

4. FIX ACR authentication:
   Replace:
     LOGIN_SERVER=$(az acr show --name "acrvaibhavrag2026" ...)
   With:
     ACR_NAME="${{ vars.ACR_NAME }}"
     az acr login --name "${ACR_NAME}"

5. SIMPLIFY health checks:
   - Remove 5+ retry loops.
   - Single `curl -f <app-url> || true` is enough.
   - Or remove health checks entirely (ACA liveness probes handle this).

6. DELETE artifact uploads (test results, coverage).

7. FIX deprecated actions:
   - azure/login@v1 → azure/login@v2
   - actions/checkout@v3 → actions/checkout@v4
   - docker/build-push-action@v5 → docker/build-push-action@v6

8. Keep only THREE jobs in this order:
   test → build-push-acr → deploy-aca

9. Return ONLY the corrected YAML file, no explanation.

GitHub Variables you have set:
- ACR_NAME (the actual ACR name)
- BACKEND_APP_NAME
- CELERY_APP_NAME
- FRONTEND_APP_NAME
- AZURE_RESOURCE_GROUP

GitHub Secrets you have set:
- AZURE_CLIENT_ID
- AZURE_TENANT_ID
- AZURE_SUBSCRIPTION_ID
```

---

## Example: Before & After

### BEFORE (What You Have Now)

```yaml
name: VeriRAG CI/CD Pipeline

jobs:
  validate-environment:  # ← DELETE THIS
    runs-on: ubuntu-latest
    steps:
      - run: |
          [ -n "${{ secrets.AZURE_CLIENT_ID }}" ] || exit 1
          [ -n "${{ vars.BACKEND_APP_NAME }}" ] || exit 1
          # ... 5 more checks
          echo "✓ All variables set"

  security:  # ← DELETE THIS ENTIRE JOB
    needs: validate-environment
    runs-on: ubuntu-latest
    steps:
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
        # ... 15 minutes of scanning

  test:
    needs: validate-environment
    runs-on: ubuntu-latest
    steps:
      - run: npm test
      - run: python manage.py test
      - uses: actions/upload-artifact@v4  # ← DELETE
        with:
          name: test-results
          path: coverage/

  build-push-acr:
    needs: [test, validate-environment]  # ← validate gone
    runs-on: ubuntu-latest
    steps:
      - uses: azure/login@v1  # ← FIX TO v2
        with: ...
      
      - run: |  # ← REPLACE THIS
          LOGIN_SERVER=$(az acr show --name "acrvaibhavrag2026" --query loginServer -o tsv)
        # This fails because ACR might not exist yet
      
      - uses: docker/build-push-action@v5  # ← v6

  deploy-aca:
    needs: build-push-acr
    runs-on: ubuntu-latest
    steps:
      - name: Pre-deployment checks  # ← DELETE THIS ENTIRE BLOCK
        run: |
          for app in backend celery frontend; do
            for i in {1..5}; do
              az containerapp show --name ca-verirag-dev-$app \
                --resource-group ${{ vars.AZURE_RESOURCE_GROUP }} \
                && break || sleep 10
            done
          done
      
      - name: Health checks  # ← SIMPLIFY OR DELETE
        run: curl -f ${{ secrets.BACKEND_URL }} || true
          # ... 4 more curl with retry loops, 45 second sleep, etc.

  collect-logs:  # ← DELETE IF FAILS
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - run: az containerapp logs ...  # ← Handle manually when debugging
```

### AFTER (Lean & Simple)

```yaml
name: VeriRAG CI/CD Pipeline

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run backend tests
        run: |
          cd apps/backend
          pip install -r requirements.txt
          python manage.py test
      
      - name: Run frontend tests
        run: |
          cd apps/frontend
          npm install
          npm test

  build-push-acr:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.tag.outputs.value }}
    steps:
      - uses: actions/checkout@v4
      
      - id: tag
        run: echo "value=${GITHUB_SHA:0:8}" >> "$GITHUB_OUTPUT"
      
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Login to ACR
        run: az acr login --name ${{ vars.ACR_NAME }}
      
      - uses: docker/setup-buildx-action@v3
      
      - name: Build & push backend image
        uses: docker/build-push-action@v6
        with:
          context: ./apps/backend
          push: true
          tags: |
            ${{ vars.ACR_NAME }}.azurecr.io/verirag-backend:latest
            ${{ vars.ACR_NAME }}.azurecr.io/verirag-backend:${{ steps.tag.outputs.value }}
      
      - name: Build & push frontend image
        uses: docker/build-push-action@v6
        with:
          context: ./apps/frontend
          push: true
          tags: |
            ${{ vars.ACR_NAME }}.azurecr.io/verirag-frontend:latest
            ${{ vars.ACR_NAME }}.azurecr.io/verirag-frontend:${{ steps.tag.outputs.value }}

  deploy-aca:
    needs: build-push-acr
    runs-on: ubuntu-latest
    steps:
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Update backend container app
        run: |
          az containerapp update \
            --name ${{ vars.BACKEND_APP_NAME }} \
            --resource-group ${{ vars.AZURE_RESOURCE_GROUP }} \
            --image ${{ vars.ACR_NAME }}.azurecr.io/verirag-backend:${{ needs.build-push-acr.outputs.image-tag }}
      
      - name: Update celery container app
        run: |
          az containerapp update \
            --name ${{ vars.CELERY_APP_NAME }} \
            --resource-group ${{ vars.AZURE_RESOURCE_GROUP }} \
            --image ${{ vars.ACR_NAME }}.azurecr.io/verirag-backend:${{ needs.build-push-acr.outputs.image-tag }}
      
      - name: Update frontend container app
        run: |
          az containerapp update \
            --name ${{ vars.FRONTEND_APP_NAME }} \
            --resource-group ${{ vars.AZURE_RESOURCE_GROUP }} \
            --image ${{ vars.ACR_NAME }}.azurecr.io/verirag-frontend:${{ needs.build-push-acr.outputs.image-tag }}
```

**Savings:**
- Removed: 80+ lines of noise
- Execution time: 45 min → ~10 min (tests + build + deploy)
- Failure points: 15 → 3 (test, build, deploy only)

---

## One-Time Setup Before Running Pipeline

### 1. Create the ACR (if it doesn't exist yet)

```bash
az acr create \
  --name acrvaibhavrag2026 \
  --resource-group <your-rg-name> \
  --sku Basic \
  --admin-enabled false
```

### 2. Set GitHub Repo Variables

Go to **Settings → Secrets and variables → Variables** and add:

```
ACR_NAME = acrvaibhavrag2026
BACKEND_APP_NAME = ca-verirag-dev-backend
CELERY_APP_NAME = ca-verirag-dev-celery
FRONTEND_APP_NAME = ca-verirag-dev-frontend
AZURE_RESOURCE_GROUP = <your-rg-name>
```

### 3. Check Terraform Bootstrap

In your `main.tf`, ensure the image references `:latest`:

```hcl
resource "azurerm_container_app" "backend" {
  ...
  template {
    container {
      image = "${azurerm_container_registry.acr.login_server}/verirag-backend:latest"
      name  = "backend"
      ...
    }
  }
}
```

Run Terraform once to provision infrastructure:

```bash
terraform apply
```

### 4. Bootstrap First Image (Optional but Recommended)

Run the pipeline once in build-only mode to ensure `:latest` images exist in ACR before ACA tries to pull them:

```bash
# Manually run just the build-push-acr job, or push to main to trigger it
# After images are in ACR, terraform apply can proceed safely
```

---

## What to Tell Haiku: Context Checklist

When you paste your `deploy.yml` into the prompt, also provide:

**This information (copy-paste into chat):**

```
Current workflow file location: .github/workflows/deploy.yml
Terraform file location: ops/infrastructure/main.tf

Container app names (from Terraform output or az):
- Backend: ca-verirag-dev-backend
- Celery: ca-verirag-dev-celery
- Frontend: ca-verirag-dev-frontend

GitHub repo has these variables set:
- ACR_NAME
- BACKEND_APP_NAME
- CELERY_APP_NAME
- FRONTEND_APP_NAME
- AZURE_RESOURCE_GROUP

GitHub repo has these secrets set:
- AZURE_CLIENT_ID
- AZURE_TENANT_ID
- AZURE_SUBSCRIPTION_ID
```

---

## Quick Checklist: Post-Refactor Validation

- [ ] Paste refactored YAML into `.github/workflows/deploy.yml`
- [ ] ACR exists: `az acr show --name acrvaibhavrag2026`
- [ ] GitHub Variables are set (5 total)
- [ ] GitHub Secrets are set (3 total)
- [ ] Push to main branch
- [ ] Monitor first run — should complete in ~10 min
- [ ] If it fails, check: ACR name in logs matches `vars.ACR_NAME`
- [ ] If ACA update fails, verify container app names match `vars.*_APP_NAME`

---

## Optional: Add Trivy Back Later (Scheduled, Not on Every Push)

Once pipeline is stable, add Trivy as a weekly scheduled job:

```yaml
security:
  runs-on: ubuntu-latest
  if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
  steps:
    - uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
```

Then add to the `on:` trigger:

```yaml
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * 0'  # Sunday 2 AM UTC
```

---

## Summary

| Before | After |
| --- | --- |
| 4 jobs + diagnostics | 3 lean jobs |
| ~45 min per run | ~10 min per run |
| 7 validation/check steps | 0 (Terraform owns this) |
| Hardcoded ACR name | GitHub Variable |
| Multiple failure points | 3 clear stages |
| Security job on every push | Weekly scheduled scan |

You're now deploying **like infrastructure exists** — because it does, thanks to Terraform. The pipeline's single responsibility: build & push images, trigger ACA to use them. That's it.

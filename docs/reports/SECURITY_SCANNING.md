# Security Scanning Guide

## Overview

This document describes how to scan container images and dependencies for security vulnerabilities using Trivy and other tools.

## Prerequisites

- Docker installed and running
- Trivy CLI installed (or use Docker image)
- Access to build the container images locally

## Installing Trivy

### Windows (PowerShell)
```powershell
# Using Chocolatey
choco install trivy

# Or download binary from GitHub releases
# https://github.com/aquasecurity/trivy/releases
```

### macOS
```bash
brew install aquasecurity/trivy/trivy
```

### Linux
```bash
# Debian/Ubuntu
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

### Using Docker (no installation required)
```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image [IMAGE_NAME]
```

## Scanning Locally Built Images

### 1. Build Images Locally

#### Build Frontend
```bash
cd frontend
docker build -t verirag-frontend:local .
```

#### Build Backend
```bash
cd backend
docker build -t verirag-backend:local .
```

### 2. Scan Images with Trivy

#### Scan Frontend Image
```bash
# Full scan with all severities
trivy image verirag-frontend:local

# Scan only HIGH and CRITICAL vulnerabilities
trivy image --severity HIGH,CRITICAL verirag-frontend:local

# Output as JSON
trivy image --format json --output frontend-scan.json verirag-frontend:local

# Scan OS packages only
trivy image --vuln-type os verirag-frontend:local

# Scan dependency libraries only (Python, npm, etc.)
trivy image --vuln-type library verirag-frontend:local
```

#### Scan Backend Image
```bash
# Full scan with all severities
trivy image verirag-backend:local

# Scan only HIGH and CRITICAL vulnerabilities
trivy image --severity HIGH,CRITICAL verirag-backend:local

# Output as JSON
trivy image --format json --output backend-scan.json verirag-backend:local

# Scan OS packages only
trivy image --vuln-type os verirag-backend:local

# Scan Python dependencies only
trivy image --vuln-type library verirag-backend:local
```

### 3. Scan Published Images

```bash
# If images are published to Docker Hub or ACR
trivy image vaibhavkumar0412/verirag-frontend:latest
trivy image vaibhavkumar0412/verirag-backend:latest

# Or from Azure Container Registry
trivy image yourregistry.azurecr.io/verirag-frontend:latest
trivy image yourregistry.azurecr.io/verirag-backend:latest
```

## Scanning Source Code and Dependencies

### Scan Python Dependencies
```bash
# Scan requirements.txt directly
trivy fs --scanners vuln backend/requirements.txt

# Scan entire backend directory
trivy fs backend/
```

### Scan Node.js Dependencies
```bash
# Scan package.json and package-lock.json
trivy fs frontend/

# Or scan just the package files
trivy fs frontend/package.json
```

## Scanning in CI/CD

The GitHub Actions workflow automatically scans images during the build process. To enable Trivy scanning in CI/CD:

### Add to `.github/workflows/ci-cd.yml`

```yaml
- name: Run Trivy vulnerability scanner (Frontend)
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.FRONTEND_IMAGE }}:${{ steps.meta.outputs.sha_short }}
    format: 'sarif'
    output: 'trivy-frontend-results.sarif'
    severity: 'CRITICAL,HIGH'

- name: Upload Trivy results to GitHub Security tab
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-frontend-results.sarif'
    category: 'frontend-trivy'

- name: Run Trivy vulnerability scanner (Backend)
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.BACKEND_IMAGE }}:${{ steps.meta.outputs.sha_short }}
    format: 'sarif'
    output: 'trivy-backend-results.sarif'
    severity: 'CRITICAL,HIGH'

- name: Upload Trivy results to GitHub Security tab
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-backend-results.sarif'
    category: 'backend-trivy'
```

## Understanding Trivy Output

### Severity Levels
- **CRITICAL**: Immediate fix required - exploitable vulnerabilities
- **HIGH**: Important fix - significant security risk
- **MEDIUM**: Moderate risk - should be addressed
- **LOW**: Minor risk - fix when convenient
- **UNKNOWN**: Severity not yet determined

### Vulnerability Information
- **CVE ID**: Common Vulnerabilities and Exposures identifier
- **Package**: Affected library or OS package
- **Installed Version**: Current vulnerable version
- **Fixed Version**: Version that fixes the vulnerability
- **Severity**: Risk level
- **Description**: Details about the vulnerability

## Remediation Best Practices

### For OS Package Vulnerabilities

1. **Upgrade base images** to latest stable tags:
   ```dockerfile
   # Keep base images up to date
   FROM node:20-alpine  # Uses latest Alpine with security patches
   FROM nginx:stable-alpine  # Uses stable nginx with latest Alpine
   FROM python:3.11-slim  # Uses latest Debian security updates
   ```

2. **Add OS package upgrades** during build:
   ```dockerfile
   # Alpine-based images
   RUN apk update && apk upgrade --no-cache
   
   # Debian-based images
   RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
   ```

3. **Use minimal base images** to reduce attack surface:
   - Prefer `alpine` over full images
   - Prefer `slim` over full Python images
   - Use multi-stage builds to exclude build tools from runtime

### For Python Dependency Vulnerabilities

1. **Pin minimum versions** with security fixes:
   ```
   Django>=5.1.7  # Instead of Django==5.0.2
   gunicorn>=23.0.0  # Instead of gunicorn==21.2.0
   ```

2. **Regularly update dependencies**:
   ```bash
   # Check for outdated packages
   pip list --outdated
   
   # Update specific packages
   pip install --upgrade Django gunicorn
   
   # Regenerate requirements with versions
   pip freeze > requirements.txt
   ```

3. **Use Python security tools**:
   ```bash
   # Install safety checker
   pip install safety
   
   # Check for known vulnerabilities
   safety check
   
   # Or use pip-audit
   pip install pip-audit
   pip-audit
   ```

### For Node.js Dependency Vulnerabilities

1. **Update npm/Node.js packages**:
   ```bash
   # Check for vulnerabilities
   npm audit
   
   # Automatically fix vulnerabilities
   npm audit fix
   
   # Update specific packages
   npm update axios
   
   # Regenerate package-lock.json
   npm install
   ```

2. **Keep Node.js version current**:
   ```dockerfile
   FROM node:20-alpine  # Use LTS version
   ```

## Automated Vulnerability Monitoring

### GitHub Dependabot
Enable Dependabot in repository settings to automatically:
- Scan dependencies for vulnerabilities
- Create pull requests to update vulnerable packages
- Monitor security advisories

### GitHub Security Alerts
- Automatically enabled for public repositories
- Shows vulnerabilities in dependency graph
- Provides remediation guidance

### Trivy in Pre-commit Hooks
```bash
# Add to .pre-commit-config.yaml
- repo: https://github.com/aquasecurity/trivy
  rev: v0.48.0
  hooks:
    - id: trivy
      args: ['fs', '--severity', 'HIGH,CRITICAL', '.']
```

## Regular Maintenance Schedule

### Weekly
- Review Dependabot/security alerts
- Update critical vulnerabilities

### Monthly
- Run full Trivy scans on all images
- Update base images to latest tags
- Review and update pinned dependencies

### Quarterly
- Audit all dependencies for necessity
- Consider alternative packages with better security records
- Update security scanning tools (Trivy, etc.)

## Resources

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)
- [GitHub Security Advisories](https://github.com/advisories)
- [National Vulnerability Database](https://nvd.nist.gov/)

## Troubleshooting

### Trivy Database Update Issues
```bash
# Clear and re-download vulnerability database
trivy image --clear-cache
```

### False Positives
If a vulnerability is a false positive:
1. Verify it doesn't apply to your use case
2. Document the reasoning
3. Add to `.trivyignore` with justification (use sparingly)

### Performance Issues
```bash
# Run lightweight OS-only scan
trivy image --vuln-type os [IMAGE]

# Skip file scanning for faster results
trivy image --skip-files '**/test/**' [IMAGE]
```

## Contact

For security vulnerability reports, please email: security@verirag.dev (or your team email)

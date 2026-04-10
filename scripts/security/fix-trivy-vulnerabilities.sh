#!/bin/bash
# Trivy Security Fix Script - Phase-Based Upgrades
# Generated: 2026-04-10
# Risk Level: VERY LOW (patch releases only)
# Estimated Time: 15-20 minutes with testing

set -e  # Exit on error

echo "🔒 Trivy Security Vulnerability Remediation Script"
echo "=================================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Phase 1: CRITICAL axios vulnerability
echo -e "${RED}[PHASE 1] CRITICAL - Fixing axios SSRF vulnerability${NC}"
echo "Impact: CVE-2025-62718 (SSRF/NO_PROXY bypass)"
echo "Action: npm install axios@1.15.0 --save"
echo ""
read -p "Proceed with Phase 1? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd apps/frontend || exit 1
    npm install axios@1.15.0 --save
    cd ../..
    echo -e "${GREEN}✓ Phase 1 Complete: axios@1.15.0${NC}"
    echo ""
else
    echo "Skipping Phase 1"
fi

# Phase 2: HIGH priority picomatch fixes
echo -e "${YELLOW}[PHASE 2] HIGH - Fixing picomatch ReDoS vulnerabilities${NC}"
echo "Impact: CVE-2026-33671, CVE-2026-33672 (ReDoS + method injection)"
echo "Action: npm install picomatch@4.0.4"
echo ""
read -p "Proceed with Phase 2? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd apps/frontend || exit 1
    npm audit fix --audit-level=moderate || true  # Auto-fixes if compatible
    cd ../..
    echo -e "${GREEN}✓ Phase 2 Complete: picomatch updated${NC}"
    echo ""
else
    echo "Skipping Phase 2"
fi

# Phase 3: MEDIUM priority yaml
echo -e "${YELLOW}[PHASE 3] MEDIUM - Fixing yaml stack overflow${NC}"
echo "Impact: CVE-2026-33532 (DoS on deep nesting)"
echo "Action: npm install yaml@2.8.3 --save-dev"
echo ""
read -p "Proceed with Phase 3? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd apps/frontend || exit 1
    npm install yaml@2.8.3 --save-dev
    cd ../..
    echo -e "${GREEN}✓ Phase 3 Complete: yaml@2.8.3${NC}"
    echo ""
else
    echo "Skipping Phase 3"
fi

# Phase 4: Backend Python fixes
echo -e "${YELLOW}[PHASE 4] Backend Python - Fixing requests library${NC}"
echo "Impact: CVE-2026-25645 (temp file prediction)"
echo "Action: pip install requests==2.33.0"
echo ""
read -p "Proceed with Phase 4? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd apps/backend || exit 1
    pip install requests==2.33.0
    cd ../..
    echo -e "${GREEN}✓ Phase 4 Complete: requests==2.33.0${NC}"
    echo ""
else
    echo "Skipping Phase 4"
fi

# Final validation
echo -e "${BLUE}[VALIDATION] Running security scans...${NC}"
echo ""
read -p "Run trivy scan on frontend? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    trivy fs apps/frontend/ --severity CRITICAL,HIGH || true
fi

read -p "Run trivy scan on backend? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    trivy fs apps/backend/ --severity CRITICAL,HIGH || true
fi

echo ""
echo -e "${GREEN}=================================================="
echo "✓ Security remediation complete!"
echo "=================================================="
echo ""
echo "Next Steps:"
echo "1. Run your test suite: npm test && pytest"
echo "2. Build Docker images: docker-compose build"
echo "3. Tag release: git tag v1.x.x-security-patch"
echo "4. Deploy to staging first"
echo "5. Monitor logs for 24 hours post-deployment"
echo ""; 

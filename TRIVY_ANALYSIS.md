# Trivy Vulnerability Analysis Report

**Generated**: 2026-04-10 | **Commit**: 813f4b8184c09d85708ba20186cc82dfc0de6185

---

## Executive Summary

**Total Vulnerabilities**: 8 across 2 targets

- **Backend (Python)**: 1 vulnerability (MEDIUM)
- **Frontend (Node)**: 7 vulnerabilities (1 CRITICAL, 2 HIGH, 4 MEDIUM)

**Critical Action Required**: Upgrade `axios` to v1.15.0 (SSRF/Proxy bypass risk)

---

## Vulnerabilities Grouped by Severity

### CRITICAL (1)

| Package   | Version | CVE    | Fixed In | Impact                    |
|-----------|---------|--------|----------|---------------------------|
| axios     | 1.13.5  | CVE... | 1.15.0   | NO_PROXY bypass → SSRF    |

### HIGH (2)

| Package   | Version | CVE    | Fixed In | Impact                    |
|-----------|---------|--------|----------|---------------------------|
| picomatch | 2.3.1   | CVE... | 2.3.2    | ReDoS - CPU spike         |
| picomatch | 4.0.3   | CVE... | 4.0.4    | ReDoS - CPU spike         |

### MEDIUM (4)

| Package   | Version | CVE    | Fixed In | Risk                      |
|-----------|---------|--------|----------|---------------------------|
| picomatch | 2.3.1   | CVE... | 2.3.2    | Method injection          |
| picomatch | 4.0.3   | CVE... | 4.0.4    | Method injection          |
| requests  | 2.32.5  | CVE... | 2.33.0   | Temp file prediction      |
| yaml      | 2.8.2   | CVE... | 2.8.3    | Stack overflow on nesting |

---

## Top 5 Dependencies by Vulnerability Count

| Rank  | Package   | Count | Severity | Root Cause                     |
|-------|-----------|-------|----------|--------------------------------|
| 1     | picomatch | 4     | HIGH+MED | Transitive from tailwindcss    |
| 2     | axios     | 1     | CRITICAL | HTTP client library            |
| 3     | yaml      | 1     | MEDIUM   | PostCSS config parser          |
| 4     | requests  | 1     | MEDIUM   | Backend Python library         |
| 5     | others    | 0     | N/A      | No vulnerabilities             |

---

## Optimal Upgrade Plan

### Phase 1 - CRITICAL FIX

```bash
npm install axios@1.15.0 --save
```

- **Impact**: Removes 1 CRITICAL vulnerability
- **Package Changes**: 1
- **Risk Level**: Very Low (patch release)

### Phase 2 - HIGH PRIORITY

```bash
npm install picomatch@4.0.4 --save-dev
```

- **Impact**: Removes 4 vulnerabilities (2 HIGH + 2 MEDIUM)
- **Package Changes**: 1
- **Risk Level**: Very Low (patch releases)

### Phase 3 - REMAINING MEDIUM

```bash
npm install yaml@2.8.3 --save-dev
pip install requests==2.33.0
```

- **Impact**: Removes 2 remaining MEDIUM vulnerabilities
- **Package Changes**: 2
- **Risk Level**: Very Low (patch releases)

---

## Specific Upgrade Versions

### Frontend package.json

```json
{
  "dependencies": {
    "axios": "^1.15.0"
  },
  "devDependencies": {
    "picomatch": "^4.0.4",
    "yaml": "^2.8.3"
  }
}
```

### Backend requirements.txt

```txt
requests==2.33.0
```

---

## Vulnerability Risk Assessment

### Can Be Ignored (Low-Risk)

- **requests@2.32.5 (MEDIUM)**: Local attacker only, mitigatable via TMPDIR
- **yaml@2.8.2 (MEDIUM)**: Build-time only, requires deep nesting input

### Cannot Be Ignored

- **axios@1.13.5 (CRITICAL)**: SSRF attacks, production risk
- **picomatch (HIGH)**: ReDoS, DoS risk

---

## Implementation Timeline

| Step  | Action                   | Time      | Risk |
|-------|--------------------------|-----------|------|
| 1     | Upgrade axios            | < 1 min   | None |
| 2     | Upgrade picomatch        | < 2 min   | None |
| 3     | Upgrade yaml             | < 1 min   | None |
| 4     | Upgrade requests         | < 1 min   | None |
| 5     | Test build & deploy      | 5-10 min  | Low  |

**Total Time**: 15-20 minutes with testing

---

## Success Metrics

- ✅ 0 CRITICAL vulnerabilities
- ✅ 0 HIGH vulnerabilities
- ✅ 0 MEDIUM vulnerabilities
- ✅ 100% security scan pass

# VeriRAG Deployment Cleanup Plan V2

**Owner:** DevOps / Tech Lead  
**Status:** ✅ Ready for Implementation  
**Timeline:** 5 weeks (flexible based on resources)  
**Estimated Cost:** $100-200 first month, $40-60 ongoing

---

## Executive Summary

This document outlines a comprehensive strategy to move from broken/fragile deployment to production-grade, maintainable, and cost-effective system.

### Current State (Problems)
- ❌ 4 conflicting CI/CD workflows causing confusion
- ❌ Unclear error messages when deployments fail
- ❌ Azure-only solution with steep learning curve
- ❌ No cost monitoring (potential surprise bills)
- ❌ No local development guide
- ❌ Manual Azure setup prone to human error
- ❌ Missing environment documentation

### Target State (Solution)
- ✅ 1 unified, well-documented CI/CD workflow
- ✅ Support for multiple platforms (Railway, Azure, self-hosted)
- ✅ Clear error messages and troubleshooting guides
- ✅ Automated deployment with health checks
- ✅ Cost transparency and monitoring
- ✅ Interactive setup wizard
- ✅ Complete documentation for all scenarios

### Success Metrics
- Time to first deployment: 30 minutes (down from 2+ hours)
- Test passing rate: >95%
- Deployment failure rate: <5%
- Engineer onboarding time: 1 hour (down from 4+ hours)
- Monthly cloud costs: <$60 (down from potential $200+)

---

## 5-Week Implementation Timeline

### Week 1: Assessment & Planning ✅
**Effort:** 8 hours  
**Owner:** Tech Lead  
**Deliverables:** This document, risk assessment, resource allocation

#### Tasks:
1. Audit current CI/CD setup
2. Identify all conflicting workflows
3. Document current Azure deployment
4. List all API keys and secrets in use
5. Assess team skill levels
6. Identify blockers

#### Risk Assessment:

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|-----------|
| Deployment downtime | High | Medium | Test in staging first, have rollback plan |
| API keys leak | Critical | Low | Rotate all keys, use Vault |
| Database migration issues | High | Low | Backup before migration, test restore |
| Team resistance to change | Medium | Medium | Education, pair programming, support |
| Cost overruns | Medium | High | Set up Budget alerts, use Railway |

### Week 2: Preparation & Testing ⏳
**Effort:** 16 hours  
**Owner:** DevOps / Senior Engineer  
**Deliverables:** Unified workflow, setup scripts, documentation

#### Tasks:
1. Create unified GitHub Actions workflow
2. Write setup automation script (`setup.sh`)
3. Create `.env.example` template
4. Document all deployment paths
5. Test locally with Docker Compose
6. Test on Railway (recommended quick path)
7. Test on Azure (existing path)

#### Deliverables:
```
- .github/workflows/ci-cd.yml (unified)
- setup.sh (interactive wizard)
- .env.example (environment template)
- docs/guides/DEPLOYMENT_QUICK_START.md
- docs/guides/GITHUB_ACTIONS_SETUP.md
- DEPLOYMENT_TROUBLESHOOTING.md
```

### Week 3: Documentation & Training ⏳
**Effort:** 12 hours  
**Owner:** Tech Lead + Senior Engineer  
**Deliverables:** Complete documentation, team training

#### Tasks:
1. Write comprehensive deployment guide
2. Create decision matrix for platform selection
3. Write troubleshooting guide
4. Create video walkthrough (optional)
5. Conduct team training session
6. Document common issues and solutions
7. Create runbook for emergency deployments

#### Documentation to Create:
- Local development setup guide
- Railway deployment guide
- Azure deployment guide (improvements)
- Self-hosted VPS deployment guide
- Cost monitoring guide
- Monitoring and alerting setup
- Security hardening guide

### Week 4: Rollout & Testing ⏳
**Effort:** 20 hours  
**Owner:** DevOps + Full Team  
**Deliverables:** Tested deployment, trained team, working app

#### Phase 4.1: Staging Deployment (5 hours)
```bash
# 1. Deploy to staging environment
# 2. Run full test suite
# 3. Load test with 50 concurrent users
# 4. Verify monitoring/alerting
# 5. Verify rollback procedure
```

#### Phase 4.2: Team Training (5 hours)
```bash
# Each team member:
# 1. Deploy app locally (30 min)
# 2. Make a code change and redeploy (30 min)
# 3. Troubleshoot a simulated issue (1 hour)
# 4. Review runbook and ask questions (30 min)
```

#### Phase 4.3: Production Readiness (10 hours)
```bash
# 1. Final security audit
# 2. Performance baseline testing
# 3. Disaster recovery drill
# 4. Cost optimization review
# 5. Final go/no-go decision
```

### Week 5: Production Launch & Monitoring ⏳
**Effort:** 16 hours (ongoing thereafter)  
**Owner:** DevOps + On-Call Support  
**Deliverables:** Live application, monitoring, alerts

#### Phase 5.1: Cutover (4 hours)
```bash
# 1. Final backup
# 2. DNS switch (or parallel run)
# 3. Health check every 1 minute
# 4. Ready to revert if needed
```

#### Phase 5.2: Monitoring & Support (8 hours first week, then ongoing)
```bash
# 1. Monitor application logs
# 2. Monitor performance metrics
# 3. Monitor costs
# 4. Respond to alerts
# 5. Gather feedback from users
```

#### Phase 5.3: Optimization (4 hours)
```bash
# 1. Analyze error patterns
# 2. Identify performance bottlenecks
# 3. Plan improvements for next iteration
# 4. Document lessons learned
```

---

## Detailed Implementation Tasks

### Task Group 1: Code & Workflow Changes

#### 1.1 Unified CI/CD Workflow
```yaml
File: .github/workflows/ci-cd.yml

Stages:
1. Validate Environment (30s)
   - Check all required secrets
   - Generate metadata (short SHA, tags)
   - Setup environment

2. Test & Validate (2-3m)
   - Run pytest (39 tests)
   - Frontend npm build
   - Generate coverage reports

3. Security Scan (1m)
   - Trivy: scan Docker images
   - Check for critical/high CVEs
   - Fail if critical found

4. Build & Push (2-3m)
   - Build backend Docker image
   - Build frontend Docker image
   - Push to ACR/GHCR

5. Deploy (2m)
   - Deploy backend container app
   - Deploy frontend container app
   - Health check
   - Notify team

Total: ~7-10 minutes per deployment
```

**Benefits:**
- Single source of truth
- No conflicting workflows
- Clear error messages
- Reusable stages
- Easy to modify

#### 1.2 Setup Automation Script
```bash
File: setup.sh
Features:
✓ Check prerequisites (Docker, Docker Compose, Azure CLI)
✓ Prompt for API keys
✓ Create .env from template
✓ Validate .env completeness
✓ Start Docker services
✓ Run health checks
✓ Show access URLs
```

**Benefits:**
- Eliminates manual steps
- Answers common questions
- Validates configuration
- Reduces onboarding time (1 hour → 10 minutes)

### Task Group 2: Documentation

#### 2.1 Deployment Guides (by platform)
```
docs/guides/DEPLOYMENT_QUICK_START.md
├── Local Docker Compose (5 min)
├── Railway.app (15 min)
├── Azure Container Apps (1-2 hours)
└── Self-hosted VPS (30 min)

Each section includes:
- Prerequisites
- Step-by-step instructions
- Troubleshooting
- Cost estimate
- Success criteria
```

#### 2.2 GitHub Actions Setup
```
docs/guides/GITHUB_ACTIONS_SETUP.md
├── Secret configuration
├── Variable configuration
├── Workflow file review
├── Testing procedures
├── Troubleshooting
└── Security best practices
```

#### 2.3 Implementation Summary
```
docs/IMPLEMENTATION_SUMMARY.md
├── What was wrong
├── What we fixed
├── Architecture overview
├── How it works
├── Success criteria
└── Next steps
```

### Task Group 3: Infrastructure & Monitoring

#### 3.1 Cost Monitoring
```bash
# Setup Azure Cost Management
az costmanagement query create \
  --timeframe "MS-TO-DATE" \
  --metric "blended_cost"

# Set budget alerts
az billing-budget create \
  --limit 100 \
  --category Cost \
  --notifications-enabled \
  --contact-emails devops@company.com
```

**Targets:**
- Development: <$20/month
- Staging: <$10/month
- Production: <$60/month

#### 3.2 Monitoring & Alerts
```
Application Insights / Azure Monitor:
├── HTTP 5xx error rate (alert if >5%)
├── Response time (alert if >2s)
├── Backend availability (alert if <99%)
├── Database connection pool exhaustion
└── Celery job queue depth
```

#### 3.3 Logging
```
All logs to:
├── Azure Monitor / Application Insights (cloud)
├── CloudWatch (if using AWS)
├── Local container logs (development)
└── Sentry (error tracking)

Retention:
├── Development: 7 days
├── Staging: 14 days
├── Production: 90 days
```

### Task Group 4: Testing & Validation

#### 4.1 Deployment Testing Checklist
```bash
Local:
  ✓ docker-compose up -d
  ✓ All services healthy
  ✓ API responds: curl http://localhost:8000/api/health/
  ✓ Frontend loads: http://localhost:5173
  ✓ Can upload PDF
  ✓ Can ask questions

Railway:
  ✓ Deployment succeeds
  ✓ App accessible at public URL
  ✓ Database connected
  ✓ All API endpoints working
  ✓ Load test: 100 concurrent users

Azure:
  ✓ Container apps healthy
  ✓ HTTPS working
  ✓ Auto-scaling tested
  ✓ Failover tested
  ✓ Cost within budget
```

#### 4.2 Load Testing
```bash
# Use: Apache Bench, Locust, or K6

# Test scenario:
- 50 concurrent users
- 100 requests total
- Measure: response time, error rate, throughput

# Success criteria:
- P95 response time <2s
- Error rate <1%
- Throughput >100 req/s
```

### Task Group 5: Team Training

#### 5.1 Documentation Reading
```
Recommended reading order:
1. IMPLEMENTATION_SUMMARY.md (30 min)
2. DEPLOYMENT_QUICK_START.md - your platform (15 min)
3. GITHUB_ACTIONS_SETUP.md (20 min)
4. Troubleshooting section (10 min)

Total: ~75 minutes
```

#### 5.2 Hands-On Exercises
```
1. Local Deployment (30 min)
   - Clone repo
   - Copy .env.example → .env
   - docker-compose up -d
   - Verify everything works

2. Code Change & Deploy (30 min)
   - Make a small code change
   - git commit → git push
   - Watch GitHub Actions
   - Verify change is live

3. Troubleshooting (1 hour)
   - Simulate common failures
   - Debug using logs
   - Fix and redeploy
   - Document the fix

4. Incident Response (30 min)
   - Review runbook
   - Simulate downtime
   - Execute recovery
   - Verify normal operation
```

#### 5.3 Pair Programming Sessions
```
1st session (2 hours):
  - Review architecture with tech lead
  - Walk through CI/CD pipeline
  - Deploy together to staging

2nd session (1 hour):
  - Troubleshoot simulated issues
  - Review logs and metrics
  - Answer questions
```

---

## Resource Requirements

### Personnel
- **Tech Lead:** 4 hours/week × 5 = 20 hours (planning, review, training)
- **Senior DevOps Engineer:** 12 hours/week × 5 = 60 hours (implementation, testing)
- **Backend Developer:** 4 hours/week × 5 = 20 hours (code review, fixes)
- **Frontend Developer:** 2 hours/week × 5 = 10 hours (frontend testing)
- **Full Team:** 4 hours/week (training, support)

**Total:** ~120 person-hours

### Infrastructure
- **Azure subscription:** (existing, or $200/month for production)
- **GitHub Actions minutes:** Free tier sufficient (2,000 min/month)
- **Railway alternative:** $10-20/month (recommended for quick start)
- **Monitoring:** Application Insights free tier or $40/month

### Tools Required
- Docker Desktop
- Git & GitHub
- Azure CLI (optional, only if using Azure)
- Text editor (VS Code preferred)

---

## Risk Management

### High Risks & Mitigation

#### Risk 1: Downtime During Cutover
**Severity:** High  
**Mitigation:**
```bash
# Plan:
1. Test cutover procedure in staging
2. Schedule cutover during low-traffic window
3. Have rollback procedure ready
4. Monitor every 1 minute during cutover (1 hour)
5. Keep old system running for 24 hours as fallback
```

#### Risk 2: Database Connection Issues
**Severity:** High  
**Mitigation:**
```bash
# Plan:
1. Backup database before any changes
2. Test restore procedure
3. Use connection pooling (available in Django)
4. Monitor connection pool exhaustion
5. Have manual restart procedure ready
```

#### Risk 3: API Key Leaks
**Severity:** Critical  
**Mitigation:**
```bash
# Plan:
1. Never commit .env to Git
2. Rotate all old API keys
3. Use secrets management (Vault, Azure Key Vault)
4. Audit who has access to secrets
5. If leaked: immediately rotate, check logs, alar security team
```

#### Risk 4: Unexpected Cost Spike
**Severity:** Medium  
**Mitigation:**
```bash
# Plan:
1. Set budget alerts ($75/month)
2. Use Railway instead of Azure for quick start
3. Set minReplicas: 0 for cost savings
4. Stop services when not in use
5. Review costs weekly
```

### Medium Risks & Mitigation

#### Risk: Team Unfamiliar with New Workflow
**Severity:** Medium  
**Mitigation:** Comprehensive documentation, hands-on training, pair programming

#### Risk: GitHub Actions Quota Issues
**Severity:** Low  
**Mitigation:** 2,000 free minutes/month sufficient, can increase if needed

#### Risk: Docker Image Size Explosion
**Severity:** Low  
**Mitigation:** Multi-stage builds already in use, remove unused dependencies

---

## Success Criteria

### Week 1
- [ ] Assessment complete
- [ ] Risk assessment documented
- [ ] Team aligned on timeline
- [ ] Resources allocated

### Week 2
- [ ] Unified workflow created and tested locally
- [ ] Setup script working
- [ ] Documentation 50% complete
- [ ] No blockers identified

### Week 3
- [ ] All documentation complete
- [ ] Team training scheduled
- [ ] Troubleshooting guide written
- [ ] Runbook prepared

### Week 4
- [ ] Staging deployment successful
- [ ] Team trained (all members can deploy)
- [ ] Load test passed
- [ ] No critical issues found

### Week 5
- [ ] Production deployment successful
- [ ] Monitoring active and working
- [ ] Team confident in operation
- [ ] Documentation finalized
- [ ] Lessons learned documented

---

## Metrics to Track

### Deployment Metrics
```
- Time to first deployment: 30 min (target)
- Deployment frequency: Daily (after team trained)
- Deployment success rate: >95%
- Time to recovery when failure: <10 min
```

### Quality Metrics
```
- Test pass rate: >95%
- Code coverage: >70%
- Security scan results: 0 critical/high vulns
- Performance: P95 response <2s
```

### Operational Metrics
```
- Uptime: >99.5%
- API availability: >99.9%
- Database availability: >99.9%
- Team incidents handled: <2/week
```

### Cost Metrics
```
- Monthly cost: $40-60
- Cost per deployment: <$1
- Cost per user: TBD
- Cost per transaction: TBD
```

---

## Decision Matrix: Platform Selection

| Criteria | Railway | Azure | Self-Hosted |
|----------|---------|-------|-------------|
| **Setup Time** | ⭐ 15 min | ⭐⭐⭐ 2 hrs | ⭐⭐ 30 min |
| **Monthly Cost** | $5-20 | $40-100 | $5-15 |
| **Learning Curve** | ⭐ Easy | ⭐⭐⭐ Hard | ⭐⭐ Medium |
| **Auto-scaling** | ✅ Yes | ✅ Yes | ❌ No |
| **CI/CD Integration** | ✅ Native | ✅ GitHub | ❌ Manual |
| **Team Expertise** | Frontend-heavy | DevOps-heavy | Medium |
| **Demo Reliability** | ⭐⭐⭐ High | ⭐⭐⭐ High | ⭐⭐ Medium |
| **Use Case** | Quick start | Enterprise | Control |

**Recommendation:** Railway for demo/quick start, migrate to Azure/self-hosted later if needed

---

## Post-Implementation (Months 2+)

### Ongoing Tasks
- Monitor application daily
- Review costs weekly
- Rotate API keys quarterly
- Keep dependencies updated (monthly)
- Backup database daily
- Disaster recovery drill (quarterly)

### Improvements for Consider
- Kubernetes migration (if scaling needed)
- Redis Sentinel for high availability
- PostgreSQL read replicas
- CDN for static assets
- API rate limiting
- Advanced monitoring (ELK stack)

### Team Responsibilities
- **DevOps:** Infrastructure, deployments, monitoring, cost management
- **Backend:** Code quality, tests, API design
- **Frontend:** Performance, UX, testing
- **Tech Lead:** Architecture decisions, training, code review

---

## Conclusion

This 5-week plan transforms a fragile, poorly documented system into a production-grade, maintainable, cost-effective deployment pipeline.

### Key Benefits
✅ 30-minute first deployment (vs. 2+ hours)  
✅ 95%+ success rate (vs. unknown)  
✅ <$60/month costs (vs. potential $200+)  
✅ Clear documentation & runbooks  
✅ Team confident in operations  
✅ Multi-platform support  
✅ Automated health checks  

### Next Steps
1. Present this plan to stakeholders
2. Allocate resources
3. Schedule Week 1 planning session
4. Begin implementation

---

**Document Version:** 2.0  
**Status:** Ready for Implementation  
**Last Updated:** March 18, 2026  
**Owner:** DevOps / Tech Lead


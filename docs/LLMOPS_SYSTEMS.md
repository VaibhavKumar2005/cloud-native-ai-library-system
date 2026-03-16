# VeriRAG LLMOps Systems

Complete guide to the five integrated LLMOps systems that power operational intelligence for VeriRAG's RAG pipeline.

## Overview

VeriRAG integrates five complementary systems for end-to-end operational monitoring and optimization:

| System | Purpose | Key Metrics | Integration |
|--------|---------|-------------|-------------|
| **CostOps** | Azure OpenAI cost tracking | Daily cost, budget %, cost/operation | Auto-logged in query pipeline |
| **QualityOps** | Response quality evaluation | Combined score, component scores, trend | RAGAS + auto-evaluation |
| **PromptOps** | Prompt versioning & A/B testing | Active version, test variants, winner score | Manual prompt management |
| **EvalOps** | Continuous evaluation pipelines | Test datasets, evaluation runs, pass rates | Manual batch evaluation |
| **DriftOps** | Model behavior monitoring | Embedding drift, quality drift, alerts | Auto-monitored in pipeline |

---

## 1. CostOps System

Real-time cost tracking for Azure OpenAI operations.

### Location
- **Module**: `apps/backend/ai_engine/costops.py`
- **API Endpoints**: 
  - `GET /api/ai/ops/cost/today/` - Daily spend
  - `GET /api/ai/ops/cost/week/` - Weekly trends
  - `GET /api/ai/ops/cost/budget-alert/` - Budget alerts

### Usage

**Automatic Integration** (in RAG pipeline):
```python
# Auto-logged on every query
cost_tracker.log_request(
    operation="rag_query",
    model="gpt-4-turbo",
    tokens_used=1450,
    cost=0.0435,  # model.pricing_per_1k_tokens * (tokens_used / 1000)
    metadata={
        "query_id": "req-123",
        "user_id": 5,
        "verification_passed": True,
    }
)
```

**Check Budget Status**:
```python
budget_alert = cost_tracker.check_budget_alert()
# Returns: {
#     "alert_active": True,
#     "message": "Daily budget alert",
#     "current_spend": 45.23,
#     "daily_limit": 50.00,
#     "percentage": 90.46
# }
```

### Configuration
```bash
# .env or environment
COSTOPS_ENABLED=true
COSTOPS_PATH=/tmp/verirag_costs.jsonl
BUDGET_DAILY_LIMIT_USD=50.00
BUDGET_MONTHLY_LIMIT_USD=1000.00
```

### API Response Example
```json
{
  "status": "success",
  "period": "last_7_days",
  "metrics": {
    "total_cost": 234.56,
    "total_tokens": 125000,
    "requests_count": 1250,
    "budget_remaining": 765.44,
    "budget_utilization_percent": 19.05
  }
}
```

---

## 2. QualityOps System

Automatic quality evaluation using RAGAS metrics.

### Location
- **Module**: `apps/backend/ai_engine/qualityops.py`
- **API Endpoints**:
  - `GET /api/ai/ops/quality/week/` - Weekly quality metrics
  - `GET /api/ai/ops/quality/month/` - Monthly quality metrics

### Quality Tiers

Responses are automatically classified by quality score:

| Tier | Score Range | Description |
|------|-------------|-------------|
| 🟢 Excellent | 0.85+ | High quality, production-ready |
| 🔵 Good | 0.75–0.84 | Good quality, minor issues |
| 🟡 Acceptable | 0.60–0.74 | Acceptable, needs monitoring |
| 🔴 Poor | < 0.60 | Critical quality issues |

### Component Scoring

Each response is evaluated on four RAGAS metrics:

- **Faithfulness** (0–1): Is the answer grounded in the retrieved context?
- **Answer Relevancy** (0–1): Does the answer address the user's question?
- **Context Precision** (0–1): Are the retrieved chunks relevant?
- **Context Recall** (0–1): Did we retrieve enough context to answer?

### Automatic Integration (in RAG pipeline)
```python
# Auto-evaluated on every response
quality_assessment = quality_gate.evaluate_response(
    query="What is machine learning?",
    response="Machine learning is...",
    context_chunks=5,
    model_used="gpt-4-turbo",
    scores={
        "faithfulness": 0.89,
        "answer_relevancy": 0.92,
        "context_precision": 0.85,
        "context_recall": 0.78,
    }
)
# Returns: quality_tier, combined_score, alerts (if any)
```

### Configuration
```bash
QUALITYOPS_ENABLED=true
QUALITYOPS_THRESHOLDS_FAITHFULNESS=0.6
QUALITYOPS_THRESHOLDS_ANSWER_RELEVANCY=0.7
QUALITYOPS_THRESHOLDS_CONTEXT_PRECISION=0.75
QUALITYOPS_THRESHOLDS_CONTEXT_RECALL=0.65
```

### API Response Example
```json
{
  "status": "success",
  "metrics": {
    "total_evaluations": 1234,
    "average_score": 0.82,
    "tier_distribution": {
      "excellent": 456,
      "good": 504,
      "acceptable": 234,
      "poor": 40
    },
    "components_passing_percent": 87.2,
    "trending": "improving"
  }
}
```

---

## 3. PromptOps System

Prompt versioning and A/B testing framework.

### Location
- **Module**: `apps/backend/ai_engine/promptops.py`
- **API Endpoints**:
  - `GET /api/ai/ops/prompt/versions/<name>/` - List versions
  - `GET /api/ai/ops/prompt/active/<name>/` - Active version
  - `POST /api/ai/ops/prompt/promote/` - Promote to active
  - `GET/POST /api/ai/ops/prompt/ab-tests/` - Manage tests
  - `GET /api/ai/ops/prompt/ab-tests/<id>/results/` - Test results

### Workflow: Version Management

**1. Create New Prompt Version**
```bash
curl -X POST http://localhost:8000/api/ai/ops/prompt/versions/rag_query/ \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "system_prompt": "You are an expert RAG assistant...",
    "user_prompt_template": "Question: {query}\nContext: {context}\nAnswer:",
    "temperature": 0.7,
    "max_tokens": 2048,
    "tags": ["production", "v2"]
  }'
```

**2. Test New Version (Draft)**
- Version is created with status `draft`
- Deploy to staging and test
- Collect feedback

**3. Promote to Testing**
```bash
curl -X POST http://localhost:8000/api/ai/ops/prompt/promote/ \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{
    "prompt_name": "rag_query",
    "version_id": "rag_query_v1710700000"
  }'
```
- Old active version moves to `testing`  
- New version becomes `active`
- 100% traffic uses new version

### Workflow: A/B Testing

**1. Create A/B Test**
```bash
curl -X POST http://localhost:8000/api/ai/ops/prompt/ab-tests/ \
  -d '{
    "prompt_name": "rag_query",
    "variant_a_version_id": "rag_query_v1710700000",  # Current active
    "variant_b_version_id": "rag_query_v1710701000",  # New version
    "split_ratio": 0.5,  # 50/50 split
    "duration_days": 7
  }'
```

**2. User Assignment (Deterministic)**
```python
# For each user, consistently assign to one variant
variant = prompt_ops.select_variant(test_id="test_123", user_id=user_id)
# Returns: "variant_a" or "variant_b" (deterministic based on user_id hash)
```

**3. View Test Results**
```bash
curl http://localhost:8000/api/ai/ops/prompt/ab-tests/test_123/results/ \
  -H "Authorization: Bearer YOUR_JWT"
```

Returns:
```json
{
  "status": "success",
  "test_id": "test_123",
  "results": {
    "variant_a": {
      "requests": 512,
      "avg_quality": 0.81,
      "avg_cost": 0.0435
    },
    "variant_b": {
      "requests": 488,
      "avg_quality": 0.84,
      "avg_cost": 0.0440
    },
    "winner": "variant_b",
    "confidence": 0.92
  }
}
```

---

## 4. EvalOps System

Continuous evaluation pipelines with test datasets.

### Location
- **Module**: `apps/backend/ai_engine/evalops.py`
- **API Endpoints**:
  - `GET/POST /api/ai/ops/eval/datasets/` - Manage test datasets
  - `GET/POST /api/ai/ops/eval/runs/` - Manage evaluation runs
  - `GET /api/ai/ops/eval/runs/<id>/summary/` - Run results

### Workflow: Create Test Dataset

**1. Create Dataset**
```bash
curl -X POST http://localhost:8000/api/ai/ops/eval/datasets/ \
  -d '{
    "name": "RAG Q&A Benchmark",
    "queries": [
      "What is machine learning?",
      "Define supervised learning",
      "How does neural networks work?"
    ],
    "expected_answers": [
      "Machine learning is a subset of AI...",
      "Supervised learning uses labeled data...",
      "Neural networks are inspired by..."
    ],
    "context_sources": [
      "ml_textbook.pdf",
      "ai_guide.pdf"
    ],
    "tags": ["rag", "qa", "benchmark"]
  }'
```

**2. Run Evaluation**
```bash
curl -X POST http://localhost:8000/api/ai/ops/eval/runs/ \
  -d '{
    "dataset_id": "dataset_1710700000",
    "prompt_version_id": "rag_query_v1710700000",
    "model": "gpt-4-turbo"
  }'
```

Status: `pending` → `running` → `completed`

**3. Check Results**
```bash
curl http://localhost:8000/api/ai/ops/eval/runs/eval_1710700000/summary/ \
  -H "Authorization: Bearer YOUR_JWT"
```

Returns:
```json
{
  "status": "success",
  "run": {
    "run_id": "eval_1710700000",
    "dataset_id": "dataset_1710700000",
    "prompt_version": "rag_query_v1710700000",
    "status": "completed",
    "total_questions": 3,
    "passed": 3,
    "pass_rate": 100.0,
    "avg_quality_score": 0.87,
    "avg_cost": 0.0440
  }
}
```

### Use Cases

- **Regression Testing**: Run same dataset on new prompt versions
- **Benchmark Tracking**: Monitor quality over time
- **Baseline Comparison**: Compare against known good performance
- **Release Validation**: Ensure quality before production

---

## 5. DriftOps System

Automatic detection of model behavior changes.

### Location
- **Module**: `apps/backend/ai_engine/driftops.py`
- **API Endpoints**:
  - `GET /api/ai/ops/drift/summary/` - Overall drift status
  - `GET /api/ai/ops/drift/alerts/` - Recent alerts
  - `POST /api/ai/ops/drift/alerts/<id>/acknowledge/` - Mark alert acknowledged

### Drift Types

**1. Embedding Drift**
- Measures cosine similarity of embedding vectors over time
- Detects when vector representations shift significantly
- **Threshold**: 0.15 (cosine distance)
- **Severity**: Warning at 0.15, Critical at 0.25+

**2. Response Pattern Shift**
- Monitors quality score consistency
- Detects when model quality degrades
- **Threshold**: 15% change from historical baseline
- **Severity**: Warning at 15%, Critical at 20%+

### Automatic Integration (in RAG pipeline)

Every response is monitored:
```python
try:
    drift_ops.log_response_pattern(
        query=user_query,
        response_length=len(result["answer"]),
        quality_score=result["evaluation"]["combined_score"],
        latency_ms=latency_ms,
        has_hallucinations=not result["verification_passed"],
        avg_token_confidence=result["evaluation"]["faithfulness"],
    )
except Exception as e:
    logger.warning(f"DriftOps logging failed: {e}")
```

### Configuration
```bash
DRIFTOPS_ENABLED=true
DRIFT_EMBEDDING_THRESHOLD=0.15
DRIFT_QUALITY_THRESHOLD=0.10  # 10% change threshold
DRIFT_WINDOW_SIZE=100  # Lookback window for baseline
```

### API Response Example
```json
{
  "status": "success",
  "drift": {
    "monitoring_enabled": true,
    "embedding_drift": {
      "detected": false,
      "severity": null,
      "threshold": 0.15
    },
    "recent_alerts": {
      "total": 2,
      "critical": 0,
      "last_hour": [
        {
          "alert_id": "drift_123",
          "timestamp": "2024-03-15T12:30:00Z",
          "drift_type": "response_pattern",
          "severity": "warning",
          "description": "Quality drift detected: 12.3%"
        }
      ]
    }
  }
}
```

---

## Integration Architecture

### Query Pipeline Flow
```
User submits query
        ↓
[query_llm() endpoint]
        ↓
┌───────┴──────────┬──────────────────────────────────┬───────────────────┐
│                  │                                  │                    │
PromptOps ────→ Get Active Prompt Variant ────────────┐                    │
                                                       ↓                    │
                                    [get_verified_answer()]                │
                                            ↓                              │
                        ┌──────────────────┴────────────────────┐          │
                        │ - Retrieve context from PGVector      │          │
                        │ - Call Azure OpenAI (GPT-4 Turbo)     │          │
                        │ - Fallback to Groq if needed          │          │
                        │ - Evaluate with RAGAS                 │          │
                        └──────────────────┬────────────────────┘          │
                                           │                              │
              ┌────────────────────────────┼────────────────────────────┐  │
              │                            │                            │  │
CostOps ─→ Log Cost     QualityOps ─→ Evaluate Quality    DriftOps ─→ │  │
  - Cost          - Component scores     Monitor Drift   │  │
  - Model         - Tier classification  - Response       │  │
  - Tokens        - Trend analysis       patterns         │  │
              │                            │                            │  │
              └────────────────────────────┼────────────────────────────┘  │
                                           │                              │
                                    Return Response ◄──────────────────────┘
                                  + quality_assessment
                                  + drift_alerts (if any)
```

### Data Flow (Storage)

All ops data is persisted as line-delimited JSON (JSONL):

```
CostOps:     /tmp/verirag_costs.jsonl
QualityOps:  /tmp/verirag_quality_evaluations.jsonl
PromptOps:   /tmp/verirag_prompts.jsonl, /tmp/verirag_prompt_ab_tests.jsonl
EvalOps:     /tmp/verirag_eval_datasets.jsonl, /tmp/verirag_eval_runs.jsonl
DriftOps:    /tmp/verirag_drift_embeddings.jsonl, /tmp/verirag_drift_patterns.jsonl, /tmp/verirag_drift_alerts.jsonl
```

Each file appends new records; in production, consider:
- Rotating files by date
- Archiving to S3/Azure Blob
- Exporting to data warehouse

---

## Monitoring & Alerts

### Grafana Dashboard
- **Location**: `ops/monitoring/grafana-dashboard.json`
- **Metrics**: Cost, quality, drift, query performance
- **Refresh Rate**: 30 seconds
- **Time Range**: 6 hours (default)

### Prometheus Alert Rules
- **Location**: `ops/monitoring/alert_rules.yml`
- **Coverage**:
  - Budget exceeded
  - Quality below threshold
  - Drift detection
  - RAG query failures
  - Infrastructure health

### Alert Examples
```yaml
- alert: DailyBudgetExceeded
  expr: sum(cost_ops_daily_cost_usd) > 50
  severity: critical

- alert: QualityScoreBelowThreshold
  expr: avg(quality_ops_combined_score) < 0.65
  severity: critical

- alert: EmbeddingDriftDetected
  expr: drift_ops_embedding_drift_distance > 0.20
  severity: warning
```

---

## Best Practices

### Cost Management
- Set realistic daily/monthly budgets
- Monitor cost trends weekly
- Review cost-per-operation breakdown  
- Optimize prompt length and token usage

### Quality Assurance
- Track component scores (not just combined score)
- Investigate poor-quality spikes
- Use EvalOps for regression testing
- Reserve 10% of traffic for quality evaluation

### Prompt Management
- Version every production prompt change
- A/B test before full rollout
- Maintain 2–3 recent versions
- Archive old versions after 30 days

### Drift Detection
- Set thresholds based on domain tolerance
- Review alerts weekly
- Respond to critical drifts within hours
- Use EvalOps to diagnose root cause

### Dashboard Usage
- Daily checklist: Budget, quality, drift alerts
- Weekly review: Cost trends, quality components, pass rate
- Monthly deep-dive: Cost optimization, quality patterns, model behavior

---

## Troubleshooting

### CostOps Not Logging
- Check `COSTOPS_ENABLED=true`
- Verify Azure OpenAI API calls are being made
- Storage path `/tmp/verirag_costs.jsonl` writable

### QualityOps Scores Missing
- Ensure RAGAS evaluation succeeds (check logs)
- Verify LLM model supports evaluation
- Run test evaluation manually

### DriftOps False Positives
- Increase `DRIFT_WINDOW_SIZE` for stable baseline
- Adjust `DRIFT_QUALITY_THRESHOLD` based on domain
- Review historical patterns before tuning

### PromptOps A/B Test Not Running
- Verify prompt versions exist and are valid
- Check test duration hasn't expired
- Ensure split_ratio and user assignment logic correct

---

## Next Steps

1. **Enable All Systems**: Verify all configurations in `.env`
2. **Test Pipeline**: Run sample query, check all ops logs
3. **Configure Alerts**: Customize thresholds for your domain
4. **Set Up Grafana**: Import dashboard, configure datasources
5. **Create Baseline**: Run EvalOps on current version to establish baseline
6. **Schedule Reviews**: Weekly cost & quality review, monthly deep-dive

---

## Performance Impact

Ops systems add minimal overhead to query pipeline (~50–100 ms):
- **CostOps**: ~10 ms (simple arithmetic)
- **QualityOps**: ~20 ms (RAGAS evaluation, cached)
- **DriftOps**: ~10 ms (pattern logging)
- **Total**: ~40–60 ms (< 5% of typical query latency)

All ops data is logged asynchronously where possible to avoid blocking responses.

---

## API Authentication

All ops endpoints require JWT authentication:
```bash
curl -X GET http://localhost:8000/api/ai/ops/cost/today/ \
  -H "Authorization: Bearer eyJhbGc..."
```

For service-to-service calls, use service account tokens with appropriate scopes.

---

## Support & Escalation

- **Documentation**: See [LLMOPS_SYSTEMS.md](LLMOPS_SYSTEMS.md)
- **Issues**: GitHub issues with label `ops`
- **On-Call**: `#verirag-ops` Slack channel
- **Runbook**: `docs/OPERATIONS_RUNBOOK.md`

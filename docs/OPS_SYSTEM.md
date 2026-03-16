# VeriRAG Operations (Ops) System

## Overview

VeriRAG now includes comprehensive **CostOps** and **QualityOps** systems for production-grade observability:

- **CostOps**: Real-time Azure OpenAI cost tracking with budget alerts
- **QualityOps**: Automated quality gates with RAGAS evaluation metrics

## Architecture

```
RAG Pipeline
    ├── Query Processing
    │   ├── LLM Call (OpenAI API)
    │   └── [CostOps] Log cost
    │
    ├── Answer Generation
    │   ├── Response Generation
    │   └── [QualityOps] Evaluate quality
    │
    └── Response Delivery
        ├── Return to user
        └── Log both cost + quality metrics
```

---

## CostOps: Cost Tracking & Budget Management

### Features

- **Real-time Cost Calculation**: Track Azure OpenAI spend per API call
- **Per-Model Pricing**: Accurate pricing for GPT-4, GPT-3.5, Embeddings
- **Per-Operation Tracking**: Segment costs by `rag_query`, `embedding`, `reranking`, etc.
- **Budget Monitoring**: Daily/monthly budget alerts at configurable thresholds
- **Cost Optimization**: Recommendations for cheaper models per task

### Pricing Model (March 2026)

```python
gpt-4-turbo:
  - Input: $0.01 per 1K tokens
  - Output: $0.03 per 1K tokens

gpt-3.5-turbo:
  - Input: $0.0005 per 1K tokens
  - Output: $0.0015 per 1K tokens

text-embedding-3-small:
  - Input: $0.000002 per 1K tokens (Approx $0.02 per 1M)
  - Output: Free
```

### Environment Variables

```bash
# Enable/disable CostOps
COSTOPS_ENABLED=true

# Monthly budget (USD)
MONTHLY_BUDGET=1000

# Where to store cost logs
COST_LOG_PATH=/tmp/verirag_costs.jsonl
```

### API Endpoints

#### Get daily costs:
```bash
GET /api/ai/ops/cost/today/

Response:
{
  "status": "success",
  "period": "last_1_days",
  "metrics": {
    "total_cost": 12.45,
    "total_tokens": 45000,
    "avg_cost_per_request": 0.101,
    "requests_count": 123,
    "most_expensive_operation": "rag_query",
    "cost_by_operation": {
      "rag_query": 10.23,
      "embedding": 2.22
    },
    "budget_remaining": 987.55,
    "budget_utilization_percent": 1.25
  }
}
```

#### Get weekly costs:
```bash
GET /api/ai/ops/cost/week/
```

#### Check budget alert:
```bash
GET /api/ai/ops/cost/budget-alert/

Response (if alert active):
{
  "status": "success",
  "alert_active": true,
  "alert": {
    "severity": "warning",
    "message": "Budget alert: 82.5% of daily budget used",
    "daily_cost": 82.50,
    "daily_budget": 100.00,
    "remaining": 17.50
  }
}
```

### Python API

```python
from ai_engine.costops import get_cost_tracker

tracker = get_cost_tracker()

# Log a cost
tracker.log_request(
    model="gpt-4-turbo",
    input_tokens=150,
    output_tokens=200,
    operation="rag_query",
    request_id="req_123",
    user_id="user_456"
)

# Get metrics
metrics = tracker.get_metrics(days=1)
print(f"Today's cost: ${metrics.total_cost}")
print(f"Budget used: {metrics.budget_utilization_percent}%")

# Check budget alert
alert = tracker.check_budget_alert()
if alert:
    print(f"⚠️ {alert['message']}")
```

---

## QualityOps: Quality Gates & Evaluation

### Features

- **Quality Scoring**: Automatic RAGAS evaluation (0-1 scale)
- **Tiered Classification**: Excellent (0.85+), Good (0.75+), Acceptable (0.60+), Poor
- **Component Thresholds**: Track individual RAGAS metrics with per-component gates
- **Production Gates**: Block deployments if quality drops below threshold
- **Trend Analysis**: Detect quality degradation over time
- **Critical Alerts**: Automatic alerts for quality regressions

### Quality Tiers

| Tier | Score Range | Status |
|------|-------------|--------|
| **Excellent** | ≥ 0.85 | ✅ Production ready |
| **Good** | 0.75 - 0.84 | ✅ Acceptable |
| **Acceptable** | 0.60 - 0.74 | ⚠️ Needs review |
| **Poor** | < 0.60 | ❌ Fails gate |

### Component Thresholds

```python
Faithfulness:         >= 0.70  # Answer grounded in context?
Answer Relevancy:     >= 0.75  # Does answer address question?
Context Precision:    >= 0.70  # Are chunks relevant?
Context Recall:       >= 0.65  # Enough context retrieved?
```

### Environment Variables

```bash
# Enable/disable QualityOps
QUALITYOPS_ENABLED=true

# Where to store quality logs
QUALITY_LOG_PATH=/tmp/verirag_quality.jsonl
```

### API Endpoints

#### Get weekly quality metrics:
```bash
GET /api/ai/ops/quality/week/

Response:
{
  "status": "success",
  "metrics": {
    "total_evaluations": 234,
    "average_score": 0.82,
    "tier_distribution": {
      "excellent": 95,
      "good": 110,
      "acceptable": 25,
      "poor": 4
    },
    "component_averages": {
      "faithfulness": 0.88,
      "answer_relevancy": 0.85,
      "context_precision": 0.79,
      "context_recall": 0.78
    },
    "components_passing_percent": 87.2,
    "trending": "improving",
    "critical_issues": []
  }
}
```

#### Get monthly quality metrics:
```bash
GET /api/ai/ops/quality/month/
```

### Python API

```python
from ai_engine.qualityops import get_quality_gate

gate = get_quality_gate(environment="production")

# Evaluate a response
record = gate.evaluate_response(
    request_id="req_001",
    query="What is AI?",
    answer="Artificial Intelligence...",
    contexts=["AI is...", "Machine learning is..."],
    ragas_scores={
        "faithfulness": 0.92,
        "answer_relevancy": 0.88,
        "context_precision": 0.85,
        "context_recall": 0.82,
    },
    user_id="user_123"
)

# Check production gate
gate_result = gate.check_production_gate(combined_score=0.87)
if gate_result["passed"]:
    print(f"✅ {gate_result['message']}")
else:
    print(f"❌ {gate_result['message']}")

# Get metrics
metrics = gate.get_quality_metrics(days=7)
print(f"Average quality: {metrics.average_score}")
print(f"Trend: {metrics.trending}")

if metrics.critical_issues:
    print("Critical issues:")
    for issue in metrics.critical_issues:
        print(f"  - {issue}")
```

---

## Unified Ops Dashboard

Get both cost and quality metrics in one request:

```bash
GET /api/ai/ops/dashboard/

Response:
{
  "status": "success",
  "timestamp": "2026-03-17T10:30:00",
  "cost": {
    "today": {
      "total_cost": 12.45,
      "requests": 123,
      "budget_utilization": 1.25,
      "budget_remaining": 987.55
    },
    "week": {
      "total_cost": 78.90,
      "requests": 823,
      "avg_cost_per_request": 0.096
    },
    "alert": null
  },
  "quality": {
    "week": {
      "average_score": 0.82,
      "evaluations": 234,
      "components_passing": 87.2,
      "trending": "improving"
    },
    "month": {
      "average_score": 0.80,
      "evaluations": 945
    },
    "critical_issues": []
  },
  "health": {
    "cost_ops_enabled": true,
    "quality_ops_enabled": true,
    "overall_status": "healthy"
  }
}
```

---

## Integration with RAG Pipeline

### Auto-logging with RAG calls

When you call the RAG pipeline:

```python
from ai_engine.views import query_llm  # Your existing RAG endpoint

# This now automatically:
# 1. Tracks cost via CostOps
# 2. Tracks quality via QualityOps
# 3. Updates all metrics
# 4. Checks quality gates
# 5. Alerts if budget exceeded
```

### Manual Integration

If you need to manually log costs/quality:

```python
from ai_engine.costops import get_cost_tracker
from ai_engine.qualityops import get_quality_gate

# Log cost
tracker = get_cost_tracker()
tracker.log_request(
    model="gpt-4-turbo",
    input_tokens=150,
    output_tokens=200,
    operation="rag_query",
    request_id=request_id,
)

# Log quality
gate = get_quality_gate()
gate.evaluate_response(
    request_id=request_id,
    query=query,
    answer=answer,
    contexts=contexts,
    ragas_scores=ragas_scores,
)
```

---

## Monitoring & Alerts

### Budget Alert Thresholds

```
80% → Warning (check your usage)
90% → Critical (very close to limit)
100% → Hard stop (all requests fail)
```

### Quality Alert Triggers

- Average score drops below 0.75 (Good threshold)
- Any component below threshold
- 10+ consecutive poor responses
- Quality trending "degrading" for 2+ days

---

## Production Deployment Checklist

- [ ] Enable CostOps: `COSTOPS_ENABLED=true`
- [ ] Enable QualityOps: `QUALITYOPS_ENABLED=true`
- [ ] Set `MONTHLY_BUDGET` based on your Azure subscription
- [ ] Configure log storage paths
- [ ] Monitor daily via `/ops/dashboard/`
- [ ] Set up alerts (via Prometheus/Azure Monitor)
- [ ] Review quality metrics weekly
- [ ] Optimize expensive operations monthly

---

## Next Steps

1. **Integration**: Update RAG pipeline to auto-log costs/quality
2. **Dashboards**: Create Grafana dashboards for visualization
3. **Alerts**: Configure Slack/email alerts for budget/quality issues
4. **PromptOps**: Add prompt versioning & A/B testing (coming next)
5. **DriftOps**: Add model drift detection (coming next)

---

## Troubleshooting

### Costs not being logged?
- Check `COSTOPS_ENABLED=true`
- Verify `COST_LOG_PATH` is writable
- Check logs for permission errors

### Quality metrics showing 0?
- Ensure RAGAS evaluation is running
- Check `QUALITYOPS_ENABLED=true`
- Verify RAGAS scores are being passed

### Budget alerts not triggering?
- Verify `MONTHLY_BUDGET` is set
- Check alert threshold (`ALERT_THRESHOLD` default: 0.8)
- Review budget calculation logic

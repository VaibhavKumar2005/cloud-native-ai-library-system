# VeriRAG LLMOps Systems

This guide describes the five LLMOps systems used by VeriRAG for cost,
quality, prompt control, evaluation, and drift monitoring.

## System Summary

VeriRAG includes five operational systems:

- CostOps: tracks token usage, spend, and budget signals.
- QualityOps: scores output quality with RAGAS-style metrics.
- PromptOps: manages prompt versions and A/B tests.
- EvalOps: runs batch evaluations on curated datasets.
- DriftOps: detects behavior shifts and quality regressions.

## CostOps

### CostOps Location

- Module: `apps/backend/ai_engine/costops.py`
- Endpoints:
  - `GET /api/ai/ops/cost/today/`
  - `GET /api/ai/ops/cost/week/`
  - `GET /api/ai/ops/cost/budget-alert/`

### CostOps Integration Example

```python
cost_tracker.log_request(
    operation="rag_query",
    model="gpt-4-turbo",
    tokens_used=1450,
    cost=0.0435,
    metadata={"query_id": "req-123", "user_id": 5},
)
```

### CostOps Configuration

```bash
COSTOPS_ENABLED=true
COSTOPS_PATH=/tmp/verirag_costs.jsonl
BUDGET_DAILY_LIMIT_USD=50.00
BUDGET_MONTHLY_LIMIT_USD=1000.00
```

## QualityOps

### QualityOps Location

- Module: `apps/backend/ai_engine/qualityops.py`
- Endpoints:
  - `GET /api/ai/ops/quality/week/`
  - `GET /api/ai/ops/quality/month/`

### QualityOps Metrics

QualityOps evaluates these components:

- Faithfulness
- Answer relevancy
- Context precision
- Context recall

### QualityOps Integration Example

```python
quality_gate.evaluate_response(
    query="What is machine learning?",
    response="Machine learning is ...",
    context_chunks=5,
    model_used="gpt-4-turbo",
    scores={
        "faithfulness": 0.89,
        "answer_relevancy": 0.92,
        "context_precision": 0.85,
        "context_recall": 0.78,
    },
)
```

### QualityOps Configuration

```bash
QUALITYOPS_ENABLED=true
QUALITYOPS_THRESHOLDS_FAITHFULNESS=0.6
QUALITYOPS_THRESHOLDS_ANSWER_RELEVANCY=0.7
QUALITYOPS_THRESHOLDS_CONTEXT_PRECISION=0.75
QUALITYOPS_THRESHOLDS_CONTEXT_RECALL=0.65
```

## PromptOps

### PromptOps Location

- Module: `apps/backend/ai_engine/promptops.py`
- Endpoints:
  - `GET /api/ai/ops/prompt/versions/<name>/`
  - `GET /api/ai/ops/prompt/active/<name>/`
  - `POST /api/ai/ops/prompt/promote/`
  - `GET/POST /api/ai/ops/prompt/ab-tests/`
  - `GET /api/ai/ops/prompt/ab-tests/<id>/results/`

### PromptOps Workflow

1. Create a draft prompt version.
2. Validate in staging.
3. Promote the version.
4. Start an A/B test for high-risk changes.
5. Keep the winner and archive stale variants.

### PromptOps Create Version Example

```bash
curl -X POST http://localhost:8000/api/ai/ops/prompt/versions/rag_query/ \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"system_prompt":"You are an expert RAG assistant"}'
```

### PromptOps A/B Assignment Example

```python
variant = prompt_ops.select_variant(test_id="test_123", user_id=user_id)
```

## EvalOps

### EvalOps Location

- Module: `apps/backend/ai_engine/evalops.py`
- Endpoints:
  - `GET/POST /api/ai/ops/eval/datasets/`
  - `GET/POST /api/ai/ops/eval/runs/`
  - `GET /api/ai/ops/eval/runs/<id>/summary/`

### EvalOps Workflow

1. Create a benchmark dataset.
2. Launch an evaluation run.
3. Track status until complete.
4. Compare pass rate and quality against baseline.

### EvalOps Run Example

```bash
curl -X POST http://localhost:8000/api/ai/ops/eval/runs/ \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{"dataset_id":"dataset_1710700000","prompt_version_id":"v1"}'
```

## DriftOps

### DriftOps Location

- Module: `apps/backend/ai_engine/driftops.py`
- Endpoints:
  - `GET /api/ai/ops/drift/summary/`
  - `GET /api/ai/ops/drift/alerts/`
  - `POST /api/ai/ops/drift/alerts/<id>/acknowledge/`

### DriftOps Signals

- Embedding drift using cosine distance.
- Response-pattern drift using quality changes.

Default thresholds:

- Warning around embedding distance `0.15`.
- Critical around embedding distance `0.25`.
- Warning around quality delta `15%`.

### DriftOps Integration Example

```python
drift_ops.log_response_pattern(
    query=user_query,
    response_length=len(result["answer"]),
    quality_score=result["evaluation"]["combined_score"],
    latency_ms=latency_ms,
    has_hallucinations=not result["verification_passed"],
)
```

### DriftOps Configuration

```bash
DRIFTOPS_ENABLED=true
DRIFT_EMBEDDING_THRESHOLD=0.15
DRIFT_QUALITY_THRESHOLD=0.10
DRIFT_WINDOW_SIZE=100
```

## Pipeline Integration

### Query Flow

```text
User query
  -> query endpoint
  -> active prompt selection
  -> retrieval and LLM response
  -> verification and quality scoring
  -> CostOps + QualityOps + DriftOps logging
  -> response payload
```

### Data Storage

Ops records are stored as JSONL files:

```text
/tmp/verirag_costs.jsonl
/tmp/verirag_quality_evaluations.jsonl
/tmp/verirag_prompts.jsonl
/tmp/verirag_prompt_ab_tests.jsonl
/tmp/verirag_eval_datasets.jsonl
/tmp/verirag_eval_runs.jsonl
/tmp/verirag_drift_alerts.jsonl
```

## Monitoring And Alerting

### Dashboard Assets

- Grafana dashboard: `ops/monitoring/grafana-dashboard.json`
- Alert rules: `ops/monitoring/alert_rules.yml`

### Sample Alerts

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

## Operational Practices

### Cost Practices

- Set daily and monthly budgets.
- Track cost by model and operation.
- Review spikes before changing prompts.

### Quality Practices

- Monitor each quality component, not only combined score.
- Run EvalOps before major prompt or model changes.
- Keep a baseline dataset for regression checks.

### Prompt Practices

- Version every production prompt change.
- Roll out with staged or A/B release.
- Archive old versions on a schedule.

### Drift Practices

- Tune thresholds for your domain tolerance.
- Investigate repeated warnings quickly.
- Use EvalOps to confirm root cause.

## Troubleshooting

### Missing CostOps Data

- Confirm `COSTOPS_ENABLED=true`.
- Confirm write access to the configured JSONL path.
- Check backend logs for write errors.

### Missing Quality Scores

- Verify evaluation stage is enabled.
- Verify model output has all required fields.
- Check logs for RAGAS evaluation failures.

### Excess Drift Alerts

- Increase `DRIFT_WINDOW_SIZE`.
- Raise drift thresholds gradually.
- Re-evaluate after one full traffic cycle.

### Prompt A/B Not Producing Results

- Ensure both versions are valid and active in the test.
- Ensure enough samples are collected per variant.
- Confirm the test has not expired.

## API Authentication

All ops endpoints require JWT authentication.

```bash
curl -X GET http://localhost:8000/api/ai/ops/cost/today/ \
  -H "Authorization: Bearer eyJhbGc..."
```

## References

- Ops overview: `docs/README_LLMOPS.md`
- Main docs index: `docs/README.md`
- Architecture: `docs/ARCHITECTURE.md`

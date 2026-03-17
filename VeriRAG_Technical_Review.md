# VeriRAG – Deep Technical Review
**Cloud-Native AI Library System | Team 96 – Vaibhav Kumar**

---

## Overview

This review is based on direct inspection of your repository code. It covers six major areas: CI/CD and ACR wiring, LangChain quality and MCP fit, backend architecture improvements, frontend enhancements, CNCF/production tooling, and experiment tracking with MLflow and W&B. At the end, there is a calibrated comparison with the referenced multi-agent-mediation repo.

---

## 1. CI/CD & Azure Container Registry – What's Actually Broken

Your two workflows (`ci.yml` and `deploy-aca.yml`) are architecturally sound in their separation of concerns, which is genuinely good. The CI does not touch Azure, and deployment is manual-dispatch only. The **root problem** is that the deploy workflow defaults to GHCR and uses username/password authentication for the registry, which is not Azure-native and will fail as soon as you point it at ACR.

### The exact failure chain

`deploy-aca.yml` uses this logic:

```yaml
REGISTRY_SERVER: ${{ vars.REGISTRY_SERVER || 'ghcr.io' }}
```

If you never set `REGISTRY_SERVER` as a GitHub Actions variable, it defaults to `ghcr.io`. When you try to push to ACR with that default, nothing reaches Azure. Even when you *do* set `REGISTRY_SERVER` to `youracr.azurecr.io`, the login step tries to use `secrets.REGISTRY_PASSWORD`, which doesn't exist for ACR unless you've specifically enabled the **admin account** on the registry (disabled by default, and considered a security antipattern).

### The correct Azure-native fix: Workload Identity Federation

Replace the current `AZURE_CREDENTIALS` JSON secret with OIDC-based authentication. This eliminates long-lived credentials entirely.

**Step 1 – Configure federated credentials on your Service Principal:**

```bash
az ad app federated-credential create \
  --id <YOUR_SP_APP_ID> \
  --parameters '{
    "name": "github-verirag",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:VaibhavKumar2005/cloud-native-ai-library-system:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

**Step 2 – Add three *variables* (not secrets) to GitHub Actions:**
- `AZURE_CLIENT_ID` = your Service Principal's App/Client ID
- `AZURE_TENANT_ID` = your tenant ID
- `AZURE_SUBSCRIPTION_ID` = your subscription ID

**Step 3 – Replace the login block in `deploy-aca.yml`:**

```yaml
- name: Login to Azure
  uses: azure/login@v2
  with:
    client-id: ${{ vars.AZURE_CLIENT_ID }}
    tenant-id: ${{ vars.AZURE_TENANT_ID }}
    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

**Step 4 – Replace the registry login block:**

```yaml
- name: Login to ACR via Azure managed identity
  run: az acr login --name ${{ vars.ACR_NAME }}
```

**Step 5 – Grant ACA's managed identity the `acrPull` role on ACR:**

```bash
ACR_ID=$(az acr show --name <acr-name> --query id -o tsv)
ACA_PRINCIPAL=$(az containerapp show \
  --name <app-name> \
  --resource-group <rg> \
  --query identity.principalId -o tsv)

az role assignment create \
  --assignee $ACA_PRINCIPAL \
  --role AcrPull \
  --scope $ACR_ID
```

After this, remove all the `az containerapp registry set` steps in the deploy workflow. The Container App pulls images through its own managed identity without ever storing credentials.

### The `REGISTRY_SERVER` variable flow

Set these in **Settings → Environments → production → Variables**:

| Variable | Value |
|---|---|
| `REGISTRY_SERVER` | `youracr.azurecr.io` |
| `ACR_NAME` | `youracr` |
| `IMAGE_NAMESPACE` | `youracr.azurecr.io` |
| `AZURE_RESOURCE_GROUP` | your RG name |
| `BACKEND_APP_NAME` | your backend ACA name |
| `CELERY_APP_NAME` | your worker ACA name |
| `FRONTEND_APP_NAME` | your frontend ACA name |

---

## 2. LangChain – Is It Working Well? Is MCP Needed?

### LangChain assessment

LangChain is doing real work in your codebase: `PyPDFLoader`, `RecursiveCharacterTextSplitter`, `GoogleGenerativeAIEmbeddings`, and `PGVector` are all used correctly. The batch ingestion with retry logic is solid. However, there are two issues:

**Critical deprecation:** You are importing `PGVector` from `langchain_community.vectorstores`. This module is deprecated and will be removed. The correct import as of LangChain v0.3+ is:

```python
# WRONG (deprecated, will break)
from langchain_community.vectorstores import PGVector

# CORRECT
from langchain_postgres import PGVector
```

Add `langchain-postgres` to `requirements.txt` and remove the community import. The constructor signature changes slightly – you pass `embeddings` instead of `embedding_function`, and the connection string format shifts to a standard `psycopg3` DSN.

**The faithfulness verifier is naive.** Your `verify_faithfulness()` function uses word-overlap heuristics – it counts 4-letter words that appear in both the answer and the context. This will give high scores to hallucinated answers that happen to reuse common vocabulary. Industry standard here is RAGAS or BERTScore. A practical intermediate step with no external service:

```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def verify_faithfulness_semantic(answer: str, context: str, embedding_model) -> float:
    """Semantic faithfulness via embedding cosine similarity."""
    answer_emb = embedding_model.embed_query(answer)
    context_emb = embedding_model.embed_query(context)
    score = cosine_similarity([answer_emb], [context_emb])[0][0]
    return float(score)
```

This uses the same embedding model you already instantiate, costs nothing extra, and is far more robust than word overlap.

### Should you add MCP?

Yes, and it fits naturally here. MCP (Model Context Protocol) lets Claude Desktop, Claude Code, and other MCP clients call your VeriRAG backend as a set of typed tools. This transforms your project from a standalone web app into an AI-agent-composable service.

A minimal FastMCP server would expose three tools:

```python
# mcp_server.py
from fastmcp import FastMCP
import httpx

mcp = FastMCP("verirag-librarian")

@mcp.tool()
async def query_library(question: str, user_id: int = 1) -> dict:
    """Query the VeriRAG document library with hallucination prevention."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8000/api/query/",
            json={"query": question, "user_id": user_id},
            headers={"Authorization": f"Bearer {TOKEN}"}
        )
        return resp.json()

@mcp.tool()
async def get_document_status(document_id: int) -> dict:
    """Check the indexing status and progress of a document."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://localhost:8000/api/documents/{document_id}/")
        return resp.json()

if __name__ == "__main__":
    mcp.run()
```

This adds maybe 50 lines of code and makes your project composable with the entire MCP ecosystem. For a hackathon or evaluation context, this is a strong differentiator.

---

## 3. Backend Improvements

### 3a. PGVector connection is recreated on every query

In `get_verified_answer()`, you instantiate `PGVector(...)` inside the function body. This creates a new database connection pool on every request. Fix with module-level initialization:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_vector_store() -> PGVector:
    return PGVector(
        collection_name=COLLECTION_NAME,
        connection_string=CONNECTION_STRING,
        embeddings=get_embedding_model(),  # also cache this
    )
```

### 3b. Use `tenacity` for LLM retries

Your retry logic uses manual `time.sleep` loops with `attempt` counters. Replace with `tenacity`, which handles exponential backoff, jitter, and error classification declaratively:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(lambda e: '429' in str(e))
)
def call_gemini_with_retry(prompt: str, api_key: str) -> str:
    ...
```

### 3c. Celery task status missing from the API

`tasks.py` dispatches the ingestion job but the `views.py` doesn't expose real-time task state from Celery. Add a status endpoint:

```python
from celery.result import AsyncResult

@api_view(['GET'])
def task_status(request, task_id):
    result = AsyncResult(task_id)
    return Response({
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    })
```

### 3d. Document deduplication

Currently the same PDF can be uploaded and indexed multiple times, wasting vector storage and distorting retrieval. Add a content hash check at ingestion:

```python
import hashlib

def compute_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(8192), b''):
            sha256.update(block)
    return sha256.hexdigest()
```

Store `file_hash` on the `Document` model and check before ingestion.

### 3e. Multi-tenant vector isolation is incomplete

You filter by `user_id` in metadata, but `PGVector.similarity_search(filter={"user_id": str(user_id)})` with the community pgvector implementation does a **post-retrieval filter**, not a pre-filter at the SQL level. This means you're paying the cost of retrieving all matches and then discarding most of them. The `langchain-postgres` `PGVectorStore` with `EmbeddingStore` backend supports proper SQL WHERE clauses. Alternatively, use separate collections per user (prefix `collection_{user_id}`).

---

## 4. Frontend Improvements

Your frontend has a Dashboard, Monitoring, Analytics, and Login flow – that's a solid structure. Areas to improve:

**Real-time ingestion progress:** The backend tracks `progress_percent` and `processed_chunks` on the Document model. Wire this to the frontend via polling or SSE so users see a live progress bar instead of a spinner. A simple 2-second polling loop against the document status endpoint is enough.

**Faithfulness score visualization:** The most distinctive feature of your system is the dual-agent faithfulness score. Surface this prominently – a colored badge (green ≥ 0.8, yellow 0.6–0.8, red < 0.6) next to every answer makes the hallucination prevention visible and tangible.

**Evidence panel:** Your API already returns `evidence_items` with source document, page, and excerpt. Render these as collapsible citation cards below the answer, so users can click to see which chunk supported the response.

**Analytics dashboard upgrade:** The `Analytics.jsx` component exists. Add a time-series chart of faithfulness scores across queries using Recharts (already in the React ecosystem). Show model fallback frequency – how often did Groq take over from Gemini. These are the metrics a judge or evaluator will want to see.

---

## 5. CNCF Stack – Kubernetes, OpenTelemetry, and Beyond

### OpenTelemetry (you're ahead here)

Your `tracing.py` is one of the most mature parts of the codebase. `trace_context`, `add_span_attributes`, and `record_event` are wired throughout the RAG pipeline. What's missing is the **collector deployment**. Without an OTel Collector receiving spans, all traces go to the console exporter.

Add this to your Kubernetes manifests:

```yaml
# otel-collector.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:latest
        args: ["--config=/etc/otel/config.yaml"]
        volumeMounts:
        - name: config
          mountPath: /etc/otel
      volumes:
      - name: config
        configMap:
          name: otel-collector-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
    exporters:
      azuremonitor:
        connection_string: "${APPLICATIONINSIGHTS_CONNECTION_STRING}"
      prometheus:
        endpoint: 0.0.0.0:8889
    service:
      pipelines:
        traces:
          receivers: [otlp]
          exporters: [azuremonitor]
        metrics:
          receivers: [otlp]
          exporters: [prometheus]
```

Then set `OTEL_EXPORTER_ENDPOINT=http://otel-collector:4317` in your backend's environment. This makes you Azure-native: traces go to Application Insights, metrics flow to Prometheus.

### Kubernetes – HPA for large traffic

Add Horizontal Pod Autoscaler with custom metrics from your Prometheus counters:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: verirag-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: verirag-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  - type: Pods
    pods:
      metric:
        name: verirag_queries_total
      target:
        type: AverageValue
        averageValue: "50"
```

For the Celery workers, use KEDA (Kubernetes Event-Driven Autoscaling) with a Redis queue length trigger. This is a CNCF project:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: verirag-celery-scaler
spec:
  scaleTargetRef:
    name: verirag-celery-worker
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
  - type: redis
    metadata:
      address: redis:6379
      listName: celery
      listLength: "5"
```

### Kafka for ingestion at scale

Your current ingestion path: HTTP upload → Celery task → Redis queue → worker. This works up to moderate volume. For high-throughput document ingestion (thousands of PDFs per hour), replace Redis as the Celery broker with Kafka using `celery[kafka]` or restructure ingestion as Kafka consumer groups. For your current use case, Redis/Celery is appropriate – Kafka would be the next step if you had multiple document sources ingesting concurrently.

### Vector DB scaling

PGVector with pgvector extension is a valid production choice for up to roughly 1 million vectors. Beyond that or for multi-region deployments, consider Weaviate (CNCF sandbox) or Qdrant. These support distributed sharding, built-in HNSW tuning, and REST/gRPC APIs. The LangChain abstraction you already use makes this a mostly mechanical swap – change the vector store class, keep the rest of the RAG pipeline identical.

---

## 6. MLflow and Weights & Biases – Do You Need Both?

Your `benchmarks.py` is genuinely well-designed: `BenchmarkResult`, `BenchmarkSuite`, and the `evaluate_response` logic with per-category expected behaviors are solid. The only gap is that results go to a JSON file with no experiment tracking, no comparison across runs, and no visualization.

### MLflow integration (recommended for Azure)

MLflow runs on your own infrastructure and integrates with Azure ML:

```python
import mlflow

def run_suite_with_mlflow(self, test_cases=None, user_id=1):
    mlflow.set_experiment("verirag-hallucination-benchmarks")
    
    with mlflow.start_run(run_name=f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        # Log hyperparameters
        mlflow.log_params({
            "faithfulness_threshold": FAITHFULNESS_THRESHOLD,
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "embedding_model": "gemini-embedding-001",
            "primary_llm": "gemini-2.0-flash",
            "fallback_llm": "llama-3.3-70b-versatile",
            "chunk_size": 1000,
            "chunk_overlap": 200,
        })
        
        suite = self.run_suite(test_cases, user_id)
        
        # Log aggregate metrics
        mlflow.log_metrics({
            "pass_rate": suite.passed_tests / suite.total_tests,
            "avg_faithfulness": suite.avg_faithfulness,
            "hallucination_prevention_rate": suite.hallucination_prevention_rate,
            "avg_latency_ms": suite.avg_latency_ms,
            "model_fallback_rate": suite.model_fallback_count / suite.total_tests,
        })
        
        # Log per-test results as a table
        import pandas as pd
        df = pd.DataFrame(suite.results)
        mlflow.log_table(df, "benchmark_results.json")
        
        # Log the full result JSON as artifact
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(asdict(suite), f, indent=2)
            mlflow.log_artifact(f.name, "benchmark_suite")
        
        return suite
```

This gives you run comparison, parameter tracking, and an artifact store with zero infrastructure if you use `mlflow.set_tracking_uri("azureml://...")` pointing at Azure ML.

### Weights & Biases

W&B is better for iterative model evaluation and visualization of score distributions. If you want to compare faithfulness score histograms across different prompt templates or chunk sizes:

```python
import wandb

wandb.init(project="verirag", name="faithfulness-eval")
wandb.log({
    "faithfulness_histogram": wandb.Histogram(
        [r["faithfulness_score"] for r in suite.results]
    ),
    "latency_p95": sorted([r["latency_ms"] for r in suite.results])[int(len(suite.results)*0.95)],
})
wandb.finish()
```

**Recommendation:** Use MLflow for experiment tracking (it's free, self-hostable, Azure-integrated), and add W&B only if you need richer visualizations or are sharing results with an external audience. For a student project, MLflow is the better ROI.

---

## 7. Comparison with multi-agent-mediation (the 26-star repo)

The referenced repository is a **multi-agent governance and mediation simulation framework** – it simulates AI agents negotiating, mediating disputes, and operating under hierarchical governance models. It is not a production RAG system. It has 26 stars likely because the conceptual problem (multi-agent conflict resolution with HITL reset mechanisms) is interesting to AI safety and alignment researchers.

The comparison is not apples-to-apples. That repo is a research simulation; yours is a production-oriented service. But there are two specific patterns from it worth borrowing:

**HITL (Human-in-the-Loop) gates.** The mediation repo has an explicit HITL gate mechanism where human intervention can reset or override agent decisions. Your dual-agent (generator + critic) pipeline currently runs fully automated. Adding an optional HITL gate when faithfulness falls below a threshold – instead of auto-regenerating with Groq – would be a meaningful addition. The user could see the low-confidence response flagged and choose whether to accept it.

**Agent state logging.** The mediation repo logs every agent decision with structured metadata (rank transitions, confidence levels, loop detection). Your `tracing.py` does something similar via OTel spans, but the benchmark results don't log which specific verification rule failed. Surfacing per-rule failure in the benchmark output would make your evaluation framework more useful for debugging prompt regressions.

**What your repo does better:** infrastructure, deployment, secret management, observability scaffolding, and the separation of concerns between ingestion, generation, and verification. The other repo has essentially no deployment story (it's a collection of Python scripts). Your project is more mature as a system, even if the conceptual novelty of the other repo's governance model is higher.

---

## Priority Fix List

| Priority | Item | Effort |
|---|---|---|
| Critical | Fix ACR auth via Workload Identity Federation | 1–2 hours |
| Critical | Replace deprecated `langchain_community.PGVector` with `langchain_postgres` | 30 min |
| High | Cache `PGVector` and embedding model at module level | 30 min |
| High | Replace word-overlap faithfulness verifier with cosine similarity | 1 hour |
| High | Integrate MLflow into `benchmarks.py` | 2 hours |
| Medium | Deploy OTel Collector + wire to Application Insights | 2 hours |
| Medium | Add MCP server exposing RAG as callable tools | 3 hours |
| Medium | Add HPA manifest for backend + KEDA for Celery | 2 hours |
| Low | Frontend: faithfulness badge + evidence citation cards | 3 hours |
| Low | Add W&B histogram logging to benchmark suite | 1 hour |

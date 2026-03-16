"""
VeriRAG CostOps: Azure OpenAI Cost Tracking & Optimization
Provides real-time cost monitoring, budget alerts, and optimization metrics.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)

# ============================================================================
# COST CONFIGURATION (Azure OpenAI Pricing - March 2026)
# ============================================================================

PRICING_MODELS = {
    "gpt-4-turbo": {
        "input_cost_per_1k": 0.01,      # $0.01 per 1K tokens
        "output_cost_per_1k": 0.03,     # $0.03 per 1K tokens
        "model_family": "gpt-4",
    },
    "gpt-4": {
        "input_cost_per_1k": 0.03,
        "output_cost_per_1k": 0.06,
        "model_family": "gpt-4",
    },
    "gpt-3.5-turbo": {
        "input_cost_per_1k": 0.0005,
        "output_cost_per_1k": 0.0015,
        "model_family": "gpt-3.5",
    },
    "text-embedding-3-small": {
        "input_cost_per_1k": 0.000002,  # $0.02 per 1M tokens
        "output_cost_per_1k": 0.0,      # No output tokens for embeddings
        "model_family": "embedding",
    },
    "text-embedding-3-large": {
        "input_cost_per_1k": 0.000013,  # $0.13 per 1M tokens
        "output_cost_per_1k": 0.0,
        "model_family": "embedding",
    },
}

# Budget thresholds (USD)
MONTHLY_BUDGET = float(os.environ.get("MONTHLY_BUDGET", "1000"))  # Default $1000/month
DAILY_BUDGET = MONTHLY_BUDGET / 30
ALERT_THRESHOLD = 0.8  # Alert at 80% of budget


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class TokenUsage:
    """Token count for a single API call."""
    input_tokens: int
    output_tokens: int
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class CostRecord:
    """Single API call cost record."""
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    request_id: str
    operation: str  # "rag_query", "embedding", "reranking", etc.
    user_id: Optional[str] = None
    document_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CostMetrics:
    """Aggregated cost metrics."""
    period: str  # "today", "week", "month"
    total_cost: float
    total_tokens: int
    avg_cost_per_request: float
    requests_count: int
    most_expensive_operation: str
    tokens_by_model: Dict[str, int]
    cost_by_operation: Dict[str, float]
    budget_remaining: float
    budget_utilization_percent: float


# ============================================================================
# COST TRACKING
# ============================================================================

class CostTracker:
    """Track Azure OpenAI API costs in real-time."""
    
    def __init__(self):
        self.enabled = os.environ.get('COSTOPS_ENABLED', 'true').lower() == 'true'
        self.storage_path = os.environ.get(
            'COST_LOG_PATH',
            '/tmp/verirag_costs.jsonl'
        )
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Create storage directory if needed."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create cost log dir: {e}")
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Dict[str, float]:
        """Calculate cost for API call."""
        if model not in PRICING_MODELS:
            logger.warning(f"Unknown model: {model}, using gpt-3.5-turbo pricing")
            model = "gpt-3.5-turbo"
        
        pricing = PRICING_MODELS[model]
        input_cost = (input_tokens / 1000) * pricing["input_cost_per_1k"]
        output_cost = (output_tokens / 1000) * pricing["output_cost_per_1k"]
        
        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(input_cost + output_cost, 6),
        }
    
    def log_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str,
        request_id: str,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> CostRecord:
        """Log API call costs."""
        if not self.enabled:
            return None
        
        cost_breakdown = self.calculate_cost(model, input_tokens, output_tokens)
        
        record = CostRecord(
            timestamp=datetime.utcnow().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=cost_breakdown["input_cost"],
            output_cost=cost_breakdown["output_cost"],
            total_cost=cost_breakdown["total_cost"],
            request_id=request_id,
            operation=operation,
            user_id=user_id,
            document_id=document_id,
        )
        
        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(record.to_dict()) + '\n')
            logger.debug(f"Logged cost: ${record.total_cost:.4f} for {operation}")
        except Exception as e:
            logger.error(f"Failed to log cost: {e}")
        
        return record
    
    def get_costs_for_period(
        self,
        days: int = 1,
    ) -> List[CostRecord]:
        """Retrieve cost records for time period."""
        if not os.path.exists(self.storage_path):
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        records = []
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    ts = datetime.fromisoformat(data['timestamp'])
                    if ts > cutoff_time:
                        records.append(CostRecord(**data))
        except Exception as e:
            logger.error(f"Failed to read costs: {e}")
        
        return records
    
    def get_metrics(self, days: int = 1) -> CostMetrics:
        """Generate cost metrics for period."""
        records = self.get_costs_for_period(days)
        
        if not records:
            return CostMetrics(
                period=f"last_{days}_days",
                total_cost=0.0,
                total_tokens=0,
                avg_cost_per_request=0.0,
                requests_count=0,
                most_expensive_operation="N/A",
                tokens_by_model={},
                cost_by_operation={},
                budget_remaining=DAILY_BUDGET if days == 1 else MONTHLY_BUDGET,
                budget_utilization_percent=0.0,
            )
        
        # Aggregate metrics
        total_cost = sum(r.total_cost for r in records)
        total_tokens = sum(r.input_tokens + r.output_tokens for r in records)
        
        # By model
        tokens_by_model = {}
        for record in records:
            model = record.model
            tokens_by_model[model] = tokens_by_model.get(model, 0) + (
                record.input_tokens + record.output_tokens
            )
        
        # By operation
        cost_by_operation = {}
        for record in records:
            op = record.operation
            cost_by_operation[op] = cost_by_operation.get(op, 0) + record.total_cost
        
        most_expensive_op = max(
            cost_by_operation.items(),
            key=lambda x: x[1],
            default=("N/A", 0)
        )[0]
        
        # Budget
        budget = DAILY_BUDGET if days == 1 else MONTHLY_BUDGET
        budget_remaining = budget - total_cost
        budget_utilization = (total_cost / budget * 100) if budget > 0 else 0
        
        return CostMetrics(
            period=f"last_{days}_days",
            total_cost=round(total_cost, 4),
            total_tokens=total_tokens,
            avg_cost_per_request=round(
                total_cost / len(records) if records else 0, 6
            ),
            requests_count=len(records),
            most_expensive_operation=most_expensive_op,
            tokens_by_model=tokens_by_model,
            cost_by_operation={k: round(v, 4) for k, v in cost_by_operation.items()},
            budget_remaining=round(budget_remaining, 4),
            budget_utilization_percent=round(budget_utilization, 2),
        )
    
    def check_budget_alert(self) -> Optional[Dict[str, Any]]:
        """Check if budget threshold exceeded."""
        metrics = self.get_metrics(days=1)
        
        if metrics.budget_utilization_percent >= (ALERT_THRESHOLD * 100):
            return {
                "severity": "warning" if metrics.budget_utilization_percent < 100 else "critical",
                "message": f"Budget alert: {metrics.budget_utilization_percent:.1f}% of daily budget used",
                "daily_cost": metrics.total_cost,
                "daily_budget": DAILY_BUDGET,
                "remaining": metrics.budget_remaining,
            }
        
        return None


# Global instance
_cost_tracker = None


def get_cost_tracker() -> CostTracker:
    """Get or create global cost tracker."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


# ============================================================================
# COST OPTIMIZATION UTILITIES
# ============================================================================

def estimate_request_cost(
    model: str,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
) -> float:
    """Estimate cost before making request."""
    tracker = get_cost_tracker()
    cost = tracker.calculate_cost(model, estimated_input_tokens, estimated_output_tokens)
    return cost["total_cost"]


def get_cheapest_model_for_task(task: str) -> str:
    """Recommend cheapest model for task."""
    if task == "embedding":
        return "text-embedding-3-small"
    elif task == "fast_response":
        return "gpt-3.5-turbo"
    elif task == "quality_response":
        return "gpt-4-turbo"
    else:
        return "gpt-4-turbo"  # Default


if __name__ == "__main__":
    # Example usage
    tracker = get_cost_tracker()
    
    # Log some requests
    tracker.log_request(
        model="gpt-4-turbo",
        input_tokens=150,
        output_tokens=200,
        operation="rag_query",
        request_id="req_123",
        user_id="user_456",
    )
    
    tracker.log_request(
        model="text-embedding-3-small",
        input_tokens=1000,
        output_tokens=0,
        operation="embedding",
        request_id="req_124",
    )
    
    # Get metrics
    metrics = tracker.get_metrics(days=1)
    print(f"\n📊 Cost Metrics (Last 24h):")
    print(f"  Total Cost: ${metrics.total_cost:.4f}")
    print(f"  Requests: {metrics.requests_count}")
    print(f"  Avg Cost/Request: ${metrics.avg_cost_per_request:.6f}")
    print(f"  Budget Used: {metrics.budget_utilization_percent:.1f}%")
    print(f"  Budget Remaining: ${metrics.budget_remaining:.2f}")
    
    # Check alerts
    alert = tracker.check_budget_alert()
    if alert:
        print(f"\n⚠️ {alert['message']}")

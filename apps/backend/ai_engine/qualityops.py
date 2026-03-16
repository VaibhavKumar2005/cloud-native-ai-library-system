"""
VeriRAG QualityOps: Quality Gates & RAGAS Evaluation Orchestration
Ensures RAG response quality meets production standards with automated gates.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# QUALITY CONFIGURATION
# ============================================================================

class QualityTier(str, Enum):
    """Quality tiers for RAG responses."""
    EXCELLENT = "excellent"      # >= 0.85
    GOOD = "good"                # >= 0.75
    ACCEPTABLE = "acceptable"    # >= 0.60
    POOR = "poor"                # < 0.60
    FAILED = "failed"            # Error in evaluation


# Quality thresholds (RAGAS scores 0-1)
QUALITY_THRESHOLDS = {
    QualityTier.EXCELLENT: 0.85,
    QualityTier.GOOD: 0.75,
    QualityTier.ACCEPTABLE: 0.60,
    QualityTier.POOR: 0.0,
}

# Component-level thresholds
COMPONENT_THRESHOLDS = {
    "faithfulness": 0.70,           # Answer grounded in context
    "answer_relevancy": 0.75,       # Answer addresses question
    "context_precision": 0.70,      # Retrieved chunks relevant
    "context_recall": 0.65,         # Retrieved enough context
}

# Production deployment gates
PRODUCTION_GATE_THRESHOLD = 0.75  # Fail deployment if below this
STAGING_GATE_THRESHOLD = 0.65     # Warning for staging


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class RAGASScores:
    """RAGAS evaluation metrics."""
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    
    @property
    def combined_score(self) -> float:
        """Weighted average of all metrics."""
        return (
            self.faithfulness * 0.30 +
            self.answer_relevancy * 0.30 +
            self.context_precision * 0.20 +
            self.context_recall * 0.20
        )
    
    @property
    def is_all_components_passing(self) -> bool:
        """Check if all components exceed thresholds."""
        return (
            self.faithfulness >= COMPONENT_THRESHOLDS["faithfulness"] and
            self.answer_relevancy >= COMPONENT_THRESHOLDS["answer_relevancy"] and
            self.context_precision >= COMPONENT_THRESHOLDS["context_precision"] and
            self.context_recall >= COMPONENT_THRESHOLDS["context_recall"]
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "faithfulness": round(self.faithfulness, 3),
            "answer_relevancy": round(self.answer_relevancy, 3),
            "context_precision": round(self.context_precision, 3),
            "context_recall": round(self.context_recall, 3),
            "combined_score": round(self.combined_score, 3),
        }


@dataclass
class QualityRecord:
    """Single quality evaluation record."""
    timestamp: str
    request_id: str
    query: str
    answer: str
    contexts: List[str]
    ragas_scores: Dict[str, float]
    combined_score: float
    quality_tier: str
    components_passing: bool
    user_id: Optional[str] = None
    model: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityMetrics:
    """Aggregated quality metrics."""
    period: str
    total_evaluations: int
    average_score: float
    tier_distribution: Dict[str, int]
    component_averages: Dict[str, float]
    components_passing_percent: float
    trending: str  # "improving", "stable", "degrading"
    critical_issues: List[str]


# ============================================================================
# QUALITY GATES & EVALUATION
# ============================================================================

class QualityGate:
    """Enforce quality standards for RAG responses."""
    
    def __init__(self, environment: str = "production"):
        self.enabled = os.environ.get('QUALITYOPS_ENABLED', 'true').lower() == 'true'
        self.environment = environment
        self.storage_path = os.environ.get(
            'QUALITY_LOG_PATH',
            '/tmp/verirag_quality.jsonl'
        )
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Create storage directory if needed."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create quality log dir: {e}")
    
    def determine_tier(self, combined_score: float) -> QualityTier:
        """Map score to quality tier."""
        for tier, threshold in sorted(
            QUALITY_THRESHOLDS.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if combined_score >= threshold:
                return tier
        return QualityTier.POOR
    
    def evaluate_response(
        self,
        request_id: str,
        query: str,
        answer: str,
        contexts: List[str],
        ragas_scores: Dict[str, float],
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> QualityRecord:
        """Evaluate and record RAG response quality."""
        if not self.enabled:
            return None
        
        # Extract RAGAS scores
        try:
            scores = RAGASScores(
                faithfulness=ragas_scores.get("faithfulness", 0.0),
                answer_relevancy=ragas_scores.get("answer_relevancy", 0.0),
                context_precision=ragas_scores.get("context_precision", 0.0),
                context_recall=ragas_scores.get("context_recall", 0.0),
            )
        except Exception as e:
            logger.error(f"Failed to parse RAGAS scores: {e}")
            scores = RAGASScores(0.0, 0.0, 0.0, 0.0)
        
        # Determine quality tier
        tier = self.determine_tier(scores.combined_score)
        
        # Create record
        record = QualityRecord(
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            query=query,
            answer=answer,
            contexts=contexts,
            ragas_scores=scores.to_dict(),
            combined_score=scores.combined_score,
            quality_tier=tier,
            components_passing=scores.is_all_components_passing,
            user_id=user_id,
            model=model,
        )
        
        # Log record
        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(record.to_dict()) + '\n')
            logger.debug(f"Quality record: {tier} ({scores.combined_score:.3f})")
        except Exception as e:
            logger.error(f"Failed to log quality record: {e}")
        
        return record
    
    def check_production_gate(
        self,
        combined_score: float,
    ) -> Dict[str, Any]:
        """
        Check if response passes production quality gate.
        Returns: {passed: bool, score: float, threshold: float, message: str}
        """
        threshold = PRODUCTION_GATE_THRESHOLD
        tier = self.determine_tier(combined_score)
        passed = combined_score >= threshold
        
        return {
            "passed": passed,
            "score": round(combined_score, 3),
            "threshold": threshold,
            "tier": tier,
            "message": (
                f"✅ PASS: Quality score {combined_score:.3f} >= {threshold}"
                if passed
                else f"❌ FAIL: Quality score {combined_score:.3f} < {threshold}"
            ),
        }
    
    def get_quality_metrics(self, days: int = 7) -> QualityMetrics:
        """Generate quality metrics for time period."""
        if not os.path.exists(self.storage_path):
            return self._empty_metrics(days)
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        records = []
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    ts = datetime.fromisoformat(data['timestamp'])
                    if ts > cutoff_time:
                        records.append(data)
        except Exception as e:
            logger.error(f"Failed to read quality records: {e}")
            return self._empty_metrics(days)
        
        if not records:
            return self._empty_metrics(days)
        
        # Aggregate metrics
        scores = [r['combined_score'] for r in records]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Tier distribution
        tier_dist = {}
        for r in records:
            tier = r['quality_tier']
            tier_dist[tier] = tier_dist.get(tier, 0) + 1
        
        # Component averages
        comp_avg = {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
        }
        
        for r in records:
            for comp in comp_avg.keys():
                comp_avg[comp] += r['ragas_scores'].get(comp, 0.0)
        
        for comp in comp_avg:
            comp_avg[comp] = round(comp_avg[comp] / len(records), 3)
        
        # Components passing percentage
        passing_count = sum(1 for r in records if r['components_passing'])
        components_passing_pct = (passing_count / len(records)) * 100 if records else 0
        
        # Trend analysis
        if len(records) >= 2:
            recent = records[-10:] if len(records) >= 10 else records
            recent_avg = sum(r['combined_score'] for r in recent) / len(recent)
            older = records[:-10] if len(records) >= 10 else []
            older_avg = sum(r['combined_score'] for r in older) / len(older) if older else recent_avg
            
            if recent_avg > older_avg + 0.05:
                trending = "improving"
            elif recent_avg < older_avg - 0.05:
                trending = "degrading"
            else:
                trending = "stable"
        else:
            trending = "insufficient_data"
        
        # Critical issues
        critical_issues = []
        for comp, threshold in COMPONENT_THRESHOLDS.items():
            if comp_avg.get(comp, 0) < threshold:
                critical_issues.append(
                    f"{comp}: {comp_avg[comp]:.3f} (threshold: {threshold})"
                )
        
        if avg_score < PRODUCTION_GATE_THRESHOLD:
            critical_issues.insert(
                0,
                f"Overall score: {avg_score:.3f} below production threshold {PRODUCTION_GATE_THRESHOLD}"
            )
        
        return QualityMetrics(
            period=f"last_{days}_days",
            total_evaluations=len(records),
            average_score=round(avg_score, 3),
            tier_distribution=tier_dist,
            component_averages=comp_avg,
            components_passing_percent=round(components_passing_pct, 1),
            trending=trending,
            critical_issues=critical_issues,
        )
    
    def _empty_metrics(self, days: int) -> QualityMetrics:
        """Return empty metrics structure."""
        return QualityMetrics(
            period=f"last_{days}_days",
            total_evaluations=0,
            average_score=0.0,
            tier_distribution={},
            component_averages={
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0,
            },
            components_passing_percent=0.0,
            trending="insufficient_data",
            critical_issues=[],
        )


# Global instance
_quality_gate = None


def get_quality_gate(environment: str = "production") -> QualityGate:
    """Get or create global quality gate."""
    global _quality_gate
    if _quality_gate is None:
        _quality_gate = QualityGate(environment)
    return _quality_gate


if __name__ == "__main__":
    # Example usage
    gate = get_quality_gate()
    
    # Simulate quality evaluation
    gate.evaluate_response(
        request_id="req_001",
        query="What is the capital of France?",
        answer="Paris",
        contexts=["France is a country in Europe. The capital of France is Paris."],
        ragas_scores={
            "faithfulness": 0.95,
            "answer_relevancy": 0.92,
            "context_precision": 0.88,
            "context_recall": 0.90,
        },
        user_id="user_123",
    )
    
    # Check gate
    gate_result = gate.check_production_gate(0.91)
    print(f"\n🎯 Production Gate Check:")
    print(f"  {gate_result['message']}")
    print(f"  Score: {gate_result['score']} (Tier: {gate_result['tier']})")
    
    # Get metrics
    metrics = gate.get_quality_metrics(days=7)
    print(f"\n📊 Quality Metrics (Last 7 Days):")
    print(f"  Total Evaluations: {metrics.total_evaluations}")
    print(f"  Average Score: {metrics.average_score:.3f}")
    print(f"  Trend: {metrics.trending}")
    print(f"  Components Passing: {metrics.components_passing_percent:.1f}%")
    
    if metrics.critical_issues:
        print(f"\n⚠️ Critical Issues:")
        for issue in metrics.critical_issues:
            print(f"  - {issue}")

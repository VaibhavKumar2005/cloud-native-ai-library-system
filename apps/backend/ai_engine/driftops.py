"""
VeriRAG DriftOps: Model Drift Detection
Monitor for embedding drift, response pattern shifts, and model degradation.
"""

import os
import json
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class DriftLevel(str, Enum):
    """Drift alert severity levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class EmbeddingSnapshot:
    """Snapshot of embedding for drift detection."""
    timestamp: str
    query: str
    embedding: List[float]  # Store as list for JSON serialization
    model: str
    dimension: int


@dataclass
class ResponsePattern:
    """Track response characteristics for pattern drift."""
    timestamp: str
    query: str
    response_length: int
    avg_token_confidence: float  # From logits
    has_hallucinations: bool
    quality_score: float
    latency_ms: float


@dataclass
class DriftAlert:
    """Alert when drift is detected."""
    alert_id: str
    timestamp: str
    drift_type: str  # "embedding", "response_pattern", "quality"
    severity: str  # DriftLevel
    description: str
    baseline_value: float
    current_value: float
    threshold: float
    acknowledged: bool = False


class DriftMonitor:
    """Monitor for model and response drift."""
    
    def __init__(self):
        self.enabled = os.environ.get('DRIFTOPS_ENABLED', 'true').lower() == 'true'
        self.embeddings_path = os.environ.get(
            'DRIFTOPS_EMBEDDINGS_PATH',
            '/tmp/verirag_drift_embeddings.jsonl'
        )
        self.patterns_path = os.environ.get(
            'DRIFTOPS_PATTERNS_PATH',
            '/tmp/verirag_drift_patterns.jsonl'
        )
        self.alerts_path = os.environ.get(
            'DRIFTOPS_ALERTS_PATH',
            '/tmp/verirag_drift_alerts.jsonl'
        )
        
        # Configuration
        self.embedding_drift_threshold = float(os.environ.get(
            'DRIFT_EMBEDDING_THRESHOLD', '0.15'
        ))
        self.quality_drift_threshold = float(os.environ.get(
            'DRIFT_QUALITY_THRESHOLD', '0.10'
        ))
        self.window_size = int(os.environ.get('DRIFT_WINDOW_SIZE', '100'))
        
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Create storage directory if needed."""
        try:
            for path in [self.embeddings_path, self.patterns_path, self.alerts_path]:
                os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create drift ops dir: {e}")
    
    def log_embedding(
        self,
        query: str,
        embedding: List[float],
        model: str = "text-embedding-3-small",
    ) -> bool:
        """Log embedding for drift tracking."""
        if not self.enabled:
            return True
        
        snapshot = EmbeddingSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            query=query,
            embedding=embedding,
            model=model,
            dimension=len(embedding),
        )
        
        try:
            with open(self.embeddings_path, 'a') as f:
                f.write(json.dumps(asdict(snapshot)) + '\n')
            return True
        except Exception as e:
            logger.error(f"Failed to log embedding: {e}")
            return False
    
    def log_response_pattern(
        self,
        query: str,
        response_length: int,
        quality_score: float,
        latency_ms: float,
        has_hallucinations: bool = False,
        avg_token_confidence: float = 0.95,
    ) -> bool:
        """Log response pattern for drift detection."""
        if not self.enabled:
            return True
        
        pattern = ResponsePattern(
            timestamp=datetime.utcnow().isoformat(),
            query=query,
            response_length=response_length,
            avg_token_confidence=avg_token_confidence,
            has_hallucinations=has_hallucinations,
            quality_score=quality_score,
            latency_ms=latency_ms,
        )
        
        try:
            with open(self.patterns_path, 'a') as f:
                f.write(json.dumps(asdict(pattern)) + '\n')
            
            # Check for drift
            self._check_pattern_drift(pattern)
            return True
        except Exception as e:
            logger.error(f"Failed to log pattern: {e}")
            return False
    
    def check_embedding_drift(self) -> Optional[DriftAlert]:
        """Detect embedding drift using cosine similarity."""
        if not os.path.exists(self.embeddings_path):
            return None
        
        try:
            embeddings = []
            with open(self.embeddings_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    embeddings.append(data)
            
            if len(embeddings) < self.window_size:
                return None
            
            # Get recent window
            recent = embeddings[-self.window_size:]
            baseline = embeddings[:-self.window_size][-self.window_size:]
            
            if not baseline or not recent:
                return None
            
            # Calculate mean embeddings
            baseline_mean = np.mean([e['embedding'] for e in baseline], axis=0)
            recent_mean = np.mean([e['embedding'] for e in recent], axis=0)
            
            # Cosine similarity
            similarity = np.dot(baseline_mean, recent_mean) / (
                np.linalg.norm(baseline_mean) * np.linalg.norm(recent_mean)
            )
            
            drift_distance = 1 - similarity
            
            if drift_distance > self.embedding_drift_threshold:
                severity = DriftLevel.CRITICAL if drift_distance > 0.25 else DriftLevel.WARNING
                
                alert = DriftAlert(
                    alert_id=f"drift_{int(datetime.utcnow().timestamp())}",
                    timestamp=datetime.utcnow().isoformat(),
                    drift_type="embedding",
                    severity=severity,
                    description=f"Embedding drift detected: {drift_distance:.3f}",
                    baseline_value=float(similarity),
                    current_value=float(drift_distance),
                    threshold=self.embedding_drift_threshold,
                )
                
                self._save_alert(alert)
                logger.warning(f"Embedding drift alert: {drift_distance:.3f}")
                return alert
        
        except Exception as e:
            logger.error(f"Failed to check embedding drift: {e}")
        
        return None
    
    def _check_pattern_drift(self, pattern: ResponsePattern) -> Optional[DriftAlert]:
        """Check if response pattern deviates from baseline."""
        try:
            patterns = []
            if os.path.exists(self.patterns_path):
                with open(self.patterns_path, 'r') as f:
                    for line in f:
                        patterns.append(json.loads(line))
            
            if len(patterns) < self.window_size:
                return None
            
            # Get baseline (older samples)
            baseline = patterns[:-self.window_size][-self.window_size:]
            
            # Calculate baseline quality
            baseline_quality = np.mean([p['quality_score'] for p in baseline])
            
            # Check current quality drift
            quality_drift = abs(pattern.quality_score - baseline_quality) / baseline_quality if baseline_quality > 0 else 0
            
            if quality_drift > self.quality_drift_threshold:
                severity = DriftLevel.CRITICAL if quality_drift > 0.20 else DriftLevel.WARNING
                
                alert = DriftAlert(
                    alert_id=f"drift_{int(datetime.utcnow().timestamp())}",
                    timestamp=datetime.utcnow().isoformat(),
                    drift_type="response_pattern",
                    severity=severity,
                    description=f"Quality drift detected: {quality_drift:.1%}",
                    baseline_value=baseline_quality,
                    current_value=pattern.quality_score,
                    threshold=self.quality_drift_threshold,
                )
                
                self._save_alert(alert)
                logger.warning(f"Quality drift alert: {quality_drift:.1%}")
                return alert
        
        except Exception as e:
            logger.error(f"Failed to check pattern drift: {e}")
        
        return None
    
    def _save_alert(self, alert: DriftAlert) -> bool:
        """Save alert to storage."""
        try:
            with open(self.alerts_path, 'a') as f:
                f.write(json.dumps(asdict(alert)) + '\n')
            return True
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")
            return False
    
    def get_recent_alerts(self, minutes: int = 60, severity: Optional[str] = None) -> List[DriftAlert]:
        """Get recent drift alerts."""
        alerts = []
        if not os.path.exists(self.alerts_path):
            return alerts
        
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        try:
            with open(self.alerts_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    alert_time = datetime.fromisoformat(data['timestamp'])
                    
                    if alert_time < cutoff:
                        continue
                    
                    if severity and data['severity'] != severity:
                        continue
                    
                    alerts.append(DriftAlert(**data))
        
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark alert as acknowledged."""
        try:
            alerts = []
            updated = False
            
            if os.path.exists(self.alerts_path):
                with open(self.alerts_path, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        if data['alert_id'] == alert_id:
                            data['acknowledged'] = True
                            updated = True
                        alerts.append(data)
            
            if updated:
                with open(self.alerts_path, 'w') as f:
                    for alert in alerts:
                        f.write(json.dumps(alert) + '\n')
                return True
        
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
        
        return False
    
    def get_drift_summary(self) -> Dict[str, Any]:
        """Get overall drift monitoring summary."""
        embedding_drift = self.check_embedding_drift()
        recent_alerts = self.get_recent_alerts(minutes=60)
        critical_alerts = [a for a in recent_alerts if a.severity == DriftLevel.CRITICAL]
        
        return {
            "monitoring_enabled": self.enabled,
            "embedding_drift": {
                "detected": embedding_drift is not None,
                "severity": embedding_drift.severity if embedding_drift else None,
                "threshold": self.embedding_drift_threshold,
            },
            "recent_alerts": {
                "total": len(recent_alerts),
                "critical": len(critical_alerts),
                "last_hour": [asdict(a) for a in recent_alerts[:5]],
            },
            "configuration": {
                "embedding_threshold": self.embedding_drift_threshold,
                "quality_threshold": self.quality_drift_threshold,
                "window_size": self.window_size,
            },
        }


# Global instance
_drift_monitor = None


def get_drift_ops() -> DriftMonitor:
    """Get or create global DriftMonitor instance."""
    global _drift_monitor
    if _drift_monitor is None:
        _drift_monitor = DriftMonitor()
    return _drift_monitor

"""
VeriRAG EvalOps: Continuous Evaluation Pipelines
Run automated evaluations against test datasets for quality monitoring.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EvalStatus(str, Enum):
    """Evaluation lifecycle status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TestDataset:
    """Test dataset for evaluations."""
    dataset_id: str
    name: str
    description: str
    queries: List[str]  # Query samples
    expected_answers: List[str]  # Expected answers
    context_sources: List[str]  # Document sources
    created_at: str = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.tags is None:
            self.tags = []


@dataclass
class EvaluationRun:
    """Single evaluation run."""
    run_id: str
    dataset_id: str
    prompt_version_id: str
    model: str
    start_time: str = None
    end_time: Optional[str] = None
    status: str = EvalStatus.PENDING
    total_questions: int = 0
    passed_count: int = 0
    avg_quality_score: float = 0.0
    avg_cost: float = 0.0
    results: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.utcnow().isoformat()
        if self.results is None:
            self.results = []
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_questions == 0:
            return 0.0
        return (self.passed_count / self.total_questions) * 100


class EvalOps:
    """Continuous evaluation pipeline management."""
    
    def __init__(self):
        self.enabled = os.environ.get('EVALOPS_ENABLED', 'true').lower() == 'true'
        self.datasets_path = os.environ.get(
            'EVALOPS_DATASETS_PATH',
            '/tmp/verirag_eval_datasets.jsonl'
        )
        self.runs_path = os.environ.get(
            'EVALOPS_RUNS_PATH',
            '/tmp/verirag_eval_runs.jsonl'
        )
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Create storage directory if needed."""
        try:
            for path in [self.datasets_path, self.runs_path]:
                os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create eval ops dir: {e}")
    
    def create_dataset(
        self,
        name: str,
        queries: List[str],
        expected_answers: List[str],
        context_sources: List[str],
        description: str = "",
        tags: List[str] = None,
    ) -> TestDataset:
        """Create test dataset for evaluations."""
        if not self.enabled:
            return None
        
        dataset_id = f"dataset_{int(datetime.utcnow().timestamp())}"
        
        dataset = TestDataset(
            dataset_id=dataset_id,
            name=name,
            description=description,
            queries=queries,
            expected_answers=expected_answers,
            context_sources=context_sources,
            tags=tags or [],
        )
        
        try:
            with open(self.datasets_path, 'a') as f:
                f.write(json.dumps(asdict(dataset)) + '\n')
            logger.info(f"Created eval dataset: {dataset_id}")
        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
        
        return dataset
    
    def get_dataset(self, dataset_id: str) -> Optional[TestDataset]:
        """Get dataset by ID."""
        if not os.path.exists(self.datasets_path):
            return None
        
        try:
            with open(self.datasets_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if data['dataset_id'] == dataset_id:
                        return TestDataset(**data)
        except Exception as e:
            logger.error(f"Failed to get dataset: {e}")
        
        return None
    
    def create_eval_run(
        self,
        dataset_id: str,
        prompt_version_id: str,
        model: str = "gpt-4-turbo",
    ) -> EvaluationRun:
        """Create evaluation run."""
        if not self.enabled:
            return None
        
        run_id = f"eval_{int(datetime.utcnow().timestamp())}"
        
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            logger.error(f"Dataset {dataset_id} not found")
            return None
        
        run = EvaluationRun(
            run_id=run_id,
            dataset_id=dataset_id,
            prompt_version_id=prompt_version_id,
            model=model,
            total_questions=len(dataset.queries),
        )
        
        try:
            with open(self.runs_path, 'a') as f:
                f.write(json.dumps(asdict(run)) + '\n')
            logger.info(f"Created eval run: {run_id}")
        except Exception as e:
            logger.error(f"Failed to create eval run: {e}")
        
        return run
    
    def get_eval_run(self, run_id: str) -> Optional[EvaluationRun]:
        """Get evaluation run by ID."""
        if not os.path.exists(self.runs_path):
            return None
        
        try:
            with open(self.runs_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if data['run_id'] == run_id:
                        return EvaluationRun(**data)
        except Exception as e:
            logger.error(f"Failed to get eval run: {e}")
        
        return None
    
    def log_eval_result(
        self,
        run_id: str,
        question: str,
        expected_answer: str,
        actual_answer: str,
        quality_score: float,
        cost: float,
        passed: bool,
    ) -> bool:
        """Log individual evaluation result."""
        run = self.get_eval_run(run_id)
        if not run:
            logger.error(f"Run {run_id} not found")
            return False
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "expected_answer": expected_answer,
            "actual_answer": actual_answer,
            "quality_score": quality_score,
            "cost": cost,
            "passed": passed,
        }
        
        run.results.append(result)
        if passed:
            run.passed_count += 1
        
        # Update averages
        run.avg_quality_score = sum(r['quality_score'] for r in run.results) / len(run.results)
        run.avg_cost = sum(r['cost'] for r in run.results) / len(run.results)
        
        # Update status
        if len(run.results) == run.total_questions:
            run.status = EvalStatus.COMPLETED
            run.end_time = datetime.utcnow().isoformat()
        else:
            run.status = EvalStatus.RUNNING
        
        # Persist
        self._update_run(run)
        
        logger.debug(f"Logged result for {run_id}: passed={passed}, score={quality_score:.3f}")
        return True
    
    def _update_run(self, run: EvaluationRun) -> bool:
        """Update evaluation run in storage."""
        try:
            runs = []
            if os.path.exists(self.runs_path):
                with open(self.runs_path, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        if data['run_id'] == run.run_id:
                            runs.append(asdict(run))
                        else:
                            runs.append(data)
            
            with open(self.runs_path, 'w') as f:
                for r in runs:
                    f.write(json.dumps(r) + '\n')
            
            return True
        except Exception as e:
            logger.error(f"Failed to update run: {e}")
            return False
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """Get summary of evaluation run."""
        run = self.get_eval_run(run_id)
        if not run:
            return None
        
        return {
            "run_id": run_id,
            "dataset_id": run.dataset_id,
            "prompt_version": run.prompt_version_id,
            "model": run.model,
            "status": run.status,
            "total_questions": run.total_questions,
            "passed": run.passed_count,
            "pass_rate": run.pass_rate,
            "avg_quality_score": round(run.avg_quality_score, 3),
            "avg_cost": round(run.avg_cost, 4),
            "start_time": run.start_time,
            "end_time": run.end_time,
        }
    
    def list_datasets(self) -> List[TestDataset]:
        """List all test datasets."""
        datasets = []
        if not os.path.exists(self.datasets_path):
            return datasets
        
        try:
            with open(self.datasets_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    datasets.append(TestDataset(**data))
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
        
        return datasets
    
    def list_eval_runs(self, dataset_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List evaluation runs, optionally filtered by dataset."""
        runs = []
        if not os.path.exists(self.runs_path):
            return runs
        
        try:
            with open(self.runs_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if dataset_id is None or data['dataset_id'] == dataset_id:
                        runs.append(self.get_run_summary(data['run_id']))
        except Exception as e:
            logger.error(f"Failed to list runs: {e}")
        
        return sorted(runs, key=lambda r: r['start_time'], reverse=True)


# Global instance
_eval_ops = None


def get_eval_ops() -> EvalOps:
    """Get or create global EvalOps instance."""
    global _eval_ops
    if _eval_ops is None:
        _eval_ops = EvalOps()
    return _eval_ops

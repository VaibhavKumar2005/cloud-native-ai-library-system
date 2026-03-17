"""
VeriRAG PromptOps: Prompt Versioning & A/B Testing
Manage prompt templates, versions, and A/B test variations.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PromptStatus(str, Enum):
    """Prompt lifecycle status."""
    DRAFT = "draft"           # Not ready for production
    TESTING = "testing"       # A/B testing
    ACTIVE = "active"         # In production
    ARCHIVED = "archived"     # No longer used


@dataclass
class PromptVersion:
    """Single prompt version."""
    version_id: str
    prompt_name: str
    system_prompt: str
    user_prompt_template: str
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    status: str = PromptStatus.DRAFT
    created_at: str = None
    created_by: Optional[str] = None
    description: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.tags is None:
            self.tags = []
    
    @property
    def hash(self) -> str:
        """Generate content hash for deduplication."""
        content = f"{self.system_prompt}{self.user_prompt_template}{self.temperature}{self.max_tokens}"
        return hashlib.sha256(content.encode()).hexdigest()[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ABTest:
    """A/B test configuration."""
    test_id: str
    prompt_name: str
    variant_a_version_id: str
    variant_b_version_id: str
    split_ratio: float = 0.5  # % of traffic to variant A
    start_date: str = None
    end_date: Optional[str] = None
    status: str = PromptStatus.TESTING
    results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.start_date is None:
            self.start_date = datetime.utcnow().isoformat()
        if self.results is None:
            self.results = {}


class PromptOps:
    """Manage prompt versions and A/B tests."""
    
    def __init__(self):
        self.enabled = os.environ.get('PROMPTOPS_ENABLED', 'true').lower() == 'true'
        self.storage_path = os.environ.get(
            'PROMPTOPS_PATH',
            '/tmp/verirag_prompts.jsonl'
        )
        self.tests_path = os.environ.get(
            'PROMPTOPS_TESTS_PATH',
            '/tmp/verirag_prompt_tests.jsonl'
        )
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Create storage directory if needed."""
        try:
            for path in [self.storage_path, self.tests_path]:
                os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create prompt ops dir: {e}")
    
    def create_version(
        self,
        prompt_name: str,
        system_prompt: str,
        user_prompt_template: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        description: str = "",
        tags: List[str] = None,
        created_by: Optional[str] = None,
    ) -> PromptVersion:
        """Create new prompt version."""
        if not self.enabled:
            return None
        
        # Generate version ID
        version_id = f"{prompt_name.lower().replace(' ', '_')}_v{int(datetime.utcnow().timestamp())}"
        
        version = PromptVersion(
            version_id=version_id,
            prompt_name=prompt_name,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            status=PromptStatus.DRAFT,
            description=description,
            tags=tags or [],
            created_by=created_by,
        )
        
        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(version.to_dict()) + '\n')
            logger.info(f"Created prompt version: {version_id}")
        except Exception as e:
            logger.error(f"Failed to create prompt version: {e}")
        
        return version
    
    def get_active_version(self, prompt_name: str) -> Optional[PromptVersion]:
        """Get current active prompt version."""
        if not os.path.exists(self.storage_path):
            return None
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if (data['prompt_name'] == prompt_name and 
                        data['status'] == PromptStatus.ACTIVE):
                        return PromptVersion(**data)
        except Exception as e:
            logger.error(f"Failed to get active version: {e}")
        
        return None
    
    def get_all_versions(self, prompt_name: str) -> List[PromptVersion]:
        """Get all versions of a prompt."""
        versions = []
        if not os.path.exists(self.storage_path):
            return versions
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if data['prompt_name'] == prompt_name:
                        versions.append(PromptVersion(**data))
        except Exception as e:
            logger.error(f"Failed to get versions: {e}")
        
        return sorted(versions, key=lambda v: v.created_at, reverse=True)
    
    def promote_to_active(self, version_id: str) -> bool:
        """Promote a version to active status."""
        if not self.enabled:
            return False
        
        try:
            # Read all versions
            versions = []
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    for line in f:
                        versions.append(json.loads(line))
            
            # Update status
            target_prompt_name = None
            for v in versions:
                if v['version_id'] == version_id:
                    v['status'] = PromptStatus.ACTIVE
                    target_prompt_name = v['prompt_name']
                elif v['prompt_name'] == target_prompt_name and v['status'] == PromptStatus.ACTIVE:
                    v['status'] = PromptStatus.TESTING
            
            # Write back
            with open(self.storage_path, 'w') as f:
                for v in versions:
                    f.write(json.dumps(v) + '\n')
            
            logger.info(f"Promoted {version_id} to ACTIVE")
            return True
        except Exception as e:
            logger.error(f"Failed to promote version: {e}")
            return False
    
    def create_ab_test(
        self,
        prompt_name: str,
        variant_a_version_id: str,
        variant_b_version_id: str,
        split_ratio: float = 0.5,
        duration_days: int = 7,
    ) -> ABTest:
        """Create A/B test for two prompt versions."""
        if not self.enabled:
            return None
        
        test_id = f"{prompt_name.lower()}_ab_{int(datetime.utcnow().timestamp())}"
        
        test = ABTest(
            test_id=test_id,
            prompt_name=prompt_name,
            variant_a_version_id=variant_a_version_id,
            variant_b_version_id=variant_b_version_id,
            split_ratio=split_ratio,
            status=PromptStatus.TESTING,
        )
        
        try:
            with open(self.tests_path, 'a') as f:
                f.write(json.dumps(asdict(test)) + '\n')
            logger.info(f"Created A/B test: {test_id}")
        except Exception as e:
            logger.error(f"Failed to create A/B test: {e}")
        
        return test
    
    def select_variant(self, test_id: str, user_id: str) -> str:
        """Select variant for user based on split ratio."""
        # Load test
        test = self._get_test(test_id)
        if not test:
            return None
        
        # Deterministic split based on user_id hash
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        ratio_threshold = test['split_ratio'] * 100
        user_bucket = user_hash % 100
        
        return (
            test['variant_a_version_id'] if user_bucket < ratio_threshold
            else test['variant_b_version_id']
        )
    
    def _get_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get test by ID."""
        if not os.path.exists(self.tests_path):
            return None
        
        try:
            with open(self.tests_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if data['test_id'] == test_id:
                        return data
        except Exception as e:
            logger.error(f"Failed to get test: {e}")
        
        return None
    
    def log_test_result(
        self,
        test_id: str,
        variant_version_id: str,
        quality_score: float,
        cost: float,
        user_id: str,
    ) -> bool:
        """Log test result for analysis."""
        # This would normally update test results
        # For now, we just log it
        logger.info(
            f"Test result: {test_id} | {variant_version_id} | "
            f"quality={quality_score:.3f}, cost=${cost:.4f}, user={user_id}"
        )
        return True
    
    def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get A/B test results and winner."""
        test = self._get_test(test_id)
        if not test:
            return None
        
        return {
            "test_id": test_id,
            "status": "collecting_data",
            "variant_a": test['variant_a_version_id'],
            "variant_b": test['variant_b_version_id'],
            "split_ratio": test['split_ratio'],
            "results": test.get('results', {}),
        }


# Global instance
_prompt_ops = None


def get_prompt_ops() -> PromptOps:
    """Get or create global PromptOps instance."""
    global _prompt_ops
    if _prompt_ops is None:
        _prompt_ops = PromptOps()
    return _prompt_ops

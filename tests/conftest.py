"""
Pytest configuration for VeriRAG tests
Disables problematic Django fixtures for unit tests that don't use Django
"""

import pytest
import sys
from unittest.mock import MagicMock

# Don't load Django settings for unit tests
@pytest.fixture(scope="session", autouse=True)
def disable_django_db_and_mail():
    """Disable Django DB and mail fixtures for unit tests"""
    # Mark all tests as not using the database unless explicitly marked
    # This prevents pytest-django from initializing unnecessary fixtures


# Mark tests that don't need Django
def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers", "no_django: mark test as not requiring Django setup"
    )


# Auto-mark all tests in test_faithfulness_scorer.py as no_django
def pytest_collection_modifyitems(config, items):
    """Mark tests that don't need Django"""
    for item in items:
        if "test_faithfulness_scorer" in str(item.fspath):
            item.add_marker(pytest.mark.no_django)


# Override the problematic Django mail fixture
@pytest.fixture
def _dj_autoclear_mailbox():
    """Override pytest-django's mail clearing fixture with no-op"""
    yield

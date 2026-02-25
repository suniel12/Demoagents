"""
Shared pytest fixtures for TechCorp Support Router tests.

Sets up the AgentCI trace processor and provides a run_agent helper
that returns AgentCI Trace objects for assertion.
"""

import asyncio
import os
import sys
import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def event_loop():
    """Create a shared event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

"""
Shared pytest fixtures for TechCorp Support Router tests.

Sets up the AgentCI trace processor and provides a run_agent helper
that returns AgentCI Trace objects for assertion.
"""

import asyncio
import os
import sys
import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--record-golden",
        action="store_true",
        default=False,
        help="Record new golden traces for regression tests",
    )
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run tests against the live OpenAI API instead of using mocks",
    )

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def event_loop():
    """Create a shared event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_openai(request):
    """
    Automatically mock OpenAI calls unless --live is specified 
    or --record-golden is active.
    """
    is_live = request.config.getoption("--live")
    is_recording = request.config.getoption("--record-golden")
    
    if is_live or is_recording:
        if is_recording:
            # We want to record the actual responses from the model
            import yaml
            from unittest.mock import patch
            import openai
            
            client = openai.AsyncOpenAI()
            from agents import set_default_openai_client
            set_default_openai_client(client)
                
            orig_create = client.responses.create
            
            mock_file = os.path.join(os.path.dirname(__file__), "fixtures", "mock_responses.yaml")
            
            async def recording_create(*args, **kwargs):
                response = await orig_create(*args, **kwargs)
                
                # We need to extract the exact tool call or text message into our mock format!
                mock_step = {}
                
                # Check output items
                if response.output:
                    item = response.output[0]
                    if item.type == "function_call":
                        mock_step["tool"] = item.name
                        import json
                        mock_step["arguments"] = json.loads(item.arguments)
                    elif item.type == "message" and item.content:
                        # Extract the final string from the message block
                        text_parts = [c.text for c in item.content if c.type == "output_text"]
                        mock_step["text"] = "\n".join(text_parts)
                        
                # Only record if we found something meaningful
                if mock_step:
                    test_name = request.node.name
                    scenario_key = test_name.split("[")[1].split("]")[0] if "[" in test_name else "default"
                    
                    # load existing, append, save
                    os.makedirs(os.path.dirname(mock_file), exist_ok=True)
                    scenarios = {}
                    if os.path.exists(mock_file):
                        with open(mock_file, "r") as f:
                            scenarios = yaml.safe_load(f) or {}
                    
                    if scenario_key not in scenarios:
                        scenarios[scenario_key] = []
                    scenarios[scenario_key].append(mock_step)
                    
                    with open(mock_file, "w") as f:
                        yaml.dump(scenarios, f, default_flow_style=False)
                        
                return response
                
            with patch.object(client.responses, 'create', side_effect=recording_create):
                yield None
            return
            
        # Don't mock, use the real API
        yield None
        return
        
    try:
        from agentci.mocks import OpenAIMocker
        import yaml
        import openai
        
        # Load mock scenarios from YAML
        mock_file = os.path.join(os.path.dirname(__file__), "fixtures", "mock_responses.yaml")
        if not os.path.exists(mock_file):
            pytest.skip("No mock_responses.yaml found and --live was not passed.")
            
        with open(mock_file, "r") as f:
            scenarios = yaml.safe_load(f)
            
        # Get the current test's name/parameter to pick the right scenario
        test_name = request.node.name
        
        # Simple heuristic: find the scenario that matches the test name
        # If it's parametrized like test_routing[billing_query], extract "billing_query"
        scenario_key = "default"
        if "[" in test_name and "]" in test_name:
            scenario_key = test_name.split("[")[1].split("]")[0]
            
        if scenario_key not in scenarios:
            # Fallback to a safe default if no explicit mock sequence exists
            scenario_key = "default"
            
        mock_sequence = scenarios.get(scenario_key, [])
            
        # Initialize mocker
        mocker = OpenAIMocker(mock_sequence)
        
        # Inject our mock client into the agents SDK
        from agents import set_default_openai_client
        set_default_openai_client(mocker.client)

        yield mocker
        
        # Teardown
        set_default_openai_client(None)
        
    except ImportError:
        pytest.skip("agentci or pyyaml not installed")

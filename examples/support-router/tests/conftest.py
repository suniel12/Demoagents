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


def _get_scenario_key(test_name: str) -> str:
    """
    Extract a scenario key from a test name for mock lookup.

    Parametrized tests:  test_foo[clear_billing0]  → 'clear_billing0'
    Non-parametrized:    test_billing_calls_lookup  → 'test_billing_calls_lookup'
    """
    if "[" in test_name and "]" in test_name:
        return test_name.split("[")[1].split("]")[0]
    return test_name


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

                # Extract the tool call or text message into our mock format
                mock_step = {}

                if response.output:
                    item = response.output[0]
                    if item.type == "function_call":
                        mock_step["tool"] = item.name
                        import json
                        mock_step["arguments"] = json.loads(item.arguments)
                    elif item.type == "message" and item.content:
                        text_parts = [c.text for c in item.content if c.type == "output_text"]
                        mock_step["text"] = "\n".join(text_parts)

                if mock_step:
                    scenario_key = _get_scenario_key(request.node.name)

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
        from ciagent.mocks import OpenAIMocker
        import yaml

        # Load mock scenarios from YAML
        mock_file = os.path.join(os.path.dirname(__file__), "fixtures", "mock_responses.yaml")
        if not os.path.exists(mock_file):
            pytest.skip("No mock_responses.yaml found and --live was not passed.")

        with open(mock_file, "r") as f:
            scenarios = yaml.safe_load(f)

        scenario_key = _get_scenario_key(request.node.name)

        if scenario_key not in scenarios:
            # Fallback: empty sequence (for guardrail tests that don't need LLM calls)
            scenario_key = "default"

        mock_sequence = scenarios.get(scenario_key, [])

        # Initialize mocker
        mocker = OpenAIMocker(mock_sequence)

        # Inject our mock client into the agents SDK
        from agents import set_default_openai_client
        set_default_openai_client(mocker.client)

        yield mocker

        # Teardown: reset to a fresh client (don't pass None — SDK crashes)
        import openai
        set_default_openai_client(openai.AsyncOpenAI(api_key="mock-teardown"))

    except ImportError:
        pytest.skip("agentci or pyyaml not installed")

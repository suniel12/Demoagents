import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_retry_on_rate_limit(trace_rate_limit):
    """
    Simulates a 403 Rate Limit error that happens twice, then succeeds.
    Verifies that the agent retries internally with exponential backoff 
    instead of crashing or returning an error to the LLM.
    """
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        trace = await trace_rate_limit()

    # The agent should succeed overall
    assert trace.success is True
    assert trace.tool_call_count > 0

    # The first tool call is github_repo_metadata
    metadata_call = trace.tool_calls[0]
    assert metadata_call.tool_name == "github_repo_metadata"
    assert metadata_call.success is True  # Ultimate success!

    # Verify that backoff occurred (sleep was called twice: 1s, then 2s)
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@pytest.mark.asyncio
async def test_graceful_missing_file(trace_missing_file):
    """
    Simulates a 404 Not Found error reading package.json.
    Verifies that the agent catches it, feeds the error to the LLM,
    and the LLM gracefully degrades the report.
    """
    trace = await trace_missing_file()

    # The trace should be successful because the agent didn't crash
    assert trace.success is True

    # Find the read file tool call
    read_call = next(tc for tc in trace.tool_calls if tc.tool_name == "github_read_file")
    
    # Verify the tool call recorded the failure
    assert read_call.success is False
    assert "404 Not Found" in read_call.error

    # Verify the LLM gracefully mentions the error in its report
    assert "Could not read the file due to an error" in trace.final_report


@pytest.mark.asyncio
async def test_complete_server_failure(trace_error):
    """
    Simulates a persistent 500 Server Error that exhausts all retries.
    Verifies that the tool call fails, the error goes to the LLM, 
    and the LLM ends the sequence gracefully.
    """
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        trace = await trace_error()

    assert trace.success is True

    # The metadata call should have failed
    metadata_call = trace.tool_calls[0]
    assert metadata_call.tool_name == "github_repo_metadata"
    assert metadata_call.success is False
    assert "500 Internal Server Error" in metadata_call.error

    # Sleep should have been called twice (for the 2 retries) before exhausting
    assert mock_sleep.call_count == 2

    # Verify the LLM explains the server error
    assert "server error" in trace.final_report.lower()

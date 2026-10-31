import pytest
from auditagent.agent.graph import run_agent_query
from auditagent.audit.logger import audit_logger
from auditagent.audit.replayer import trace_replayer

def test_trace_logging_and_replay():
    # 1. Execute query
    state = run_agent_query("What is the average credit score across all customers?")
    trace_id = state.get("trace_id")
    assert trace_id is not None
    assert trace_id.startswith("TRC-")

    # 2. Retrieve trace
    trace = audit_logger.get_trace(trace_id)
    assert trace is not None
    assert trace["trace_id"] == trace_id
    assert trace["tool_called"] == "sql_tool"

    # 3. Deterministically Replay
    replay = trace_replayer.replay_trace(trace_id)
    assert replay["success"] is True
    assert replay["is_deterministic_match"] is True
    assert replay["match_details"]["row_count_match"] is True

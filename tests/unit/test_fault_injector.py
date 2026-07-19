"""Injector and malformed-line construction unit tests."""

from __future__ import annotations

import json

import pytest

from mcp_cassette.cassette import Fault, FaultOverlay
from mcp_cassette.replay.faults import Injector, make_malformed_line


def test_consult_none_method_never_faults() -> None:
    injector = Injector(FaultOverlay(faults=[Fault.timeout("tools/call")]))
    assert injector.consult(None) is None


def test_consult_no_overlay() -> None:
    injector = Injector(None)
    assert injector.consult("tools/call") is None


def test_multiple_matching_faults_warn_and_first_fires() -> None:
    overlay = FaultOverlay(
        faults=[Fault.error("tools/call"), Fault.timeout("tools/call")]
    )
    injector = Injector(overlay)
    with pytest.warns(UserWarning, match="multiple faults"):
        fired = injector.consult("tools/call")
    assert fired is not None
    assert fired.type == "error"
    # only the fired fault leaves the unused list
    assert [f.type for f in injector.unused_faults()] == ["timeout"]


def test_malformed_not_json_line() -> None:
    line = make_malformed_line({"jsonrpc": "2.0", "id": 1}, "not_json")
    with pytest.raises(json.JSONDecodeError):
        json.loads(line)


def test_malformed_wrong_id_line() -> None:
    line = make_malformed_line({"jsonrpc": "2.0", "id": 1, "result": {}}, "wrong_id")
    obj = json.loads(line)
    assert obj["id"] == "mcp-cassette-unknown-id"


def test_malformed_truncate_line_is_invalid_json() -> None:
    response = {"jsonrpc": "2.0", "id": 1, "result": {"text": "x" * 50}}
    line = make_malformed_line(response, "truncate")
    assert line.endswith(b"\n")
    with pytest.raises(json.JSONDecodeError):
        json.loads(line)

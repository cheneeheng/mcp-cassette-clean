"""A tiny MCP-style stdio server, pure standard library, no ``mcp`` SDK.

It speaks newline-delimited JSON-RPC 2.0 over stdin/stdout — exactly the transport
mcp-cassette records and replays — so it doubles as a self-contained "real server" for
the examples. Two tools are exposed:

* ``echo`` — returns the given text, plus a per-call random ``token``. The token is the
  non-deterministic bit: recorded once, and on replay mcp-cassette returns that same
  recorded token every time, which is the whole point of a cassette.
* ``add`` — returns the sum of two integers.

Run directly over stdio::

    python examples/echo_server.py
"""

from __future__ import annotations

import json
import secrets
import sys
from typing import Any

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "echo",
        "description": "Echo text back, with a random per-call token.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "add",
        "description": "Add two integers.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    },
]


def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _text_content(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": False}


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request; return a response or ``None`` for a notification."""
    method = request.get("method")
    msg_id = request.get("id")
    if method == "initialize":
        return _result(
            msg_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "echo-example", "version": "1.0.0"},
            },
        )
    if method == "notifications/initialized":
        return None  # notification: no response
    if method == "tools/list":
        return _result(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "echo":
            token = secrets.token_hex(4)
            return _result(msg_id, _text_content(f"{args.get('text', '')} [{token}]"))
        if name == "add":
            total = int(args.get("a", 0)) + int(args.get("b", 0))
            return _result(msg_id, _text_content(str(total)))
        return _error(msg_id, -32602, f"unknown tool: {name}")
    if msg_id is None:
        return None  # unknown notification
    return _error(msg_id, -32601, f"method not found: {method}")


def main() -> None:
    """Read JSON-RPC lines from stdin and write responses to stdout until EOF."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = handle(json.loads(line))
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

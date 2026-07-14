# Examples

Runnable, self-contained demos of mcp-cassette. Nothing here needs the official `mcp`
SDK — the sample server speaks raw JSON-RPC over stdio, which is exactly the transport
mcp-cassette records and replays.

## Files

| File | What it is |
|---|---|
| `echo_server.py` | A ~90-line MCP-style stdio server (stdlib only): tools `echo` and `add`. `echo` returns a random per-call token to make non-determinism visible. |
| `mcp_client.py` | A tiny transport-level JSON-RPC client used to drive a server command. |
| `test_echo.py` | Three pytest examples built on the `mcp_cassette` fixture. |
| `cassettes/` | The committed cassettes those tests replay. |

## Run them

From the repo root:

```
uv run pytest examples/                        # replay the committed cassettes (offline, deterministic)
MCP_CASSETTE_MODE=none uv run pytest examples/ # same, but forbid recording (what CI does)
MCP_CASSETTE_MODE=all  uv run pytest examples/ # re-record against echo_server.py
```

The main test suite (`uv run pytest`) does **not** collect `examples/` — `testpaths` is
`tests`, so these stay standalone.

## What each test shows

- **`test_echo_and_add`** — the core loop. First run (no cassette) records through the
  proxy; every run after replays offline. The agent command is the only thing that
  changes, and the fixture builds it for you.
- **`test_replay_is_deterministic`** — `echo` mints a fresh random token per call, yet two
  replays of the cassette return the *same* token. A live server would not. That
  stability is the entire point of a cassette.
- **`test_survives_injected_error`** — `with_faults` overlays a fault at replay time so
  `tools/call` returns a JSON-RPC error, without touching the recorded cassette. One
  recording drives a whole resilience matrix. Faults fire *after* a request matches, so
  the faulted call must still correspond to a recorded interaction.

## Try it by hand (the CLI)

```
# record a live session into a cassette
mcp-cassette record --cassette demo.mcp.json -- python examples/echo_server.py

# inspect what was captured
mcp-cassette inspect demo.mcp.json

# replay it as a drop-in mock server (no subprocess, no randomness)
mcp-cassette serve demo.mcp.json
```

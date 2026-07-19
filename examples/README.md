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

# refresh one cassette: delete it, then a normal run re-records just that one
rm examples/cassettes/echo_and_add.mcp.json && uv run pytest examples/
```

The main test suite (`uv run pytest`) does **not** collect `examples/` — `testpaths` is
`tests`, so these stay standalone.

**On re-recording:** `MCP_CASSETTE_MODE=all` force-records *every* test against the live
`echo_server.py`, so it can't produce a green run here — `test_replay_is_deterministic`
asserts a stable token that only holds on replay, and `test_survives_injected_error` uses
faults, which are replay-only and refuse to run while recording. Refresh cassettes
per-file instead (delete + default `once` mode, as above). `fault.mcp.json` can't be
regenerated through its own test at all; record it from a plain `echo` session — e.g. the
CLI `record` command below.

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

`record` is a transparent proxy: it spawns the real server after `--` and forwards
whatever arrives on its own stdin. So to record something you have to *drive it* — send
JSON-RPC requests in, exactly as a real MCP client would. The easiest way by hand is to
pipe newline-delimited requests into the proxy's stdin:

Replay is a server, not a player — it answers requests from the cassette but emits nothing on its own, so `serve` needs the same piped requests to have anything to respond to; the pipe stands in for the client.

```bash
# record a live session — pipe requests in so there is actually traffic to capture
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cli","version":"1.0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}' \
  | mcp-cassette record --cassette demo.mcp.json -- python examples/echo_server.py

# inspect what was captured
mcp-cassette inspect demo.mcp.json

# replay it as a drop-in mock server (no subprocess, no randomness).
# same trick to send it a request — replay answers from the cassette, offline:
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cli","version":"1.0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}' \
  | mcp-cassette serve demo.mcp.json
```

The same thing in Windows PowerShell — `printf` and `\` continuations aren't native, so
pipe an array of single-quoted lines instead (single quotes keep PowerShell from mangling
the `"` inside the JSON):

```powershell
# record a live session — each array element is sent as one line on the proxy's stdin
@(
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cli","version":"1.0"}}}'
  '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}'
) | mcp-cassette record --cassette demo.mcp.json -- python examples/echo_server.py

# inspect what was captured
mcp-cassette inspect demo.mcp.json

# replay it offline; same array trick to drive it
@(
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cli","version":"1.0"}}}'
  '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}'
) | mcp-cassette serve demo.mcp.json
```

Piping closes stdin at EOF, which cleanly ends the session. In a real test the client is
your agent, not `printf` — the fixture just hands it `mcp-cassette record ... -- <server>`
(or `mcp-cassette serve <cassette>`) as the server command and the agent drives it.

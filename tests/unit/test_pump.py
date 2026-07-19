"""Unit tests for line buffering and pumping over byte streams."""

from __future__ import annotations

import anyio

from mcp_cassette.record.pump import buffered_lines, pump_lines


class _ChunkStream:
    """Fake ByteReceiveStream fed from a fixed chunk list."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    async def receive(self, max_bytes: int = 65536) -> bytes:
        if not self._chunks:
            raise anyio.EndOfStream
        return self._chunks.pop(0)


class _SinkStream:
    """Fake ByteSendStream collecting sent lines."""

    def __init__(self) -> None:
        self.sent: list[bytes] = []

    async def send(self, item: bytes) -> None:
        self.sent.append(item)


def _lines(chunks: list[bytes]) -> list[bytes]:
    async def collect() -> list[bytes]:
        return [line async for line in buffered_lines(_ChunkStream(chunks))]  # type: ignore[arg-type]

    return anyio.run(collect)


def test_reassembles_lines_split_across_chunks() -> None:
    assert _lines([b'{"a":1}\n{"b"', b":2}\n"]) == [b'{"a":1}\n', b'{"b":2}\n']


def test_final_unterminated_fragment_yielded_at_eof() -> None:
    assert _lines([b"first\n", b"no-newline"]) == [b"first\n", b"no-newline"]


def test_empty_chunk_treated_as_eof() -> None:
    assert _lines([b"first\n", b"", b"never seen\n"]) == [b"first\n"]


def test_pump_lines_forwards_and_taps() -> None:
    tapped: list[bytes] = []
    sink = _SinkStream()

    async def run() -> None:
        await pump_lines(
            _ChunkStream([b"one\ntwo\n"]),  # type: ignore[arg-type]
            sink,  # type: ignore[arg-type]
            tap=tapped.append,
        )

    anyio.run(run)
    assert sink.sent == [b"one\n", b"two\n"]
    assert tapped == sink.sent

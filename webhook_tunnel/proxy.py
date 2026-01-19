"""Local TCP/HTTP proxy used by the CLI.

This module intentionally avoids external binaries (e.g. socat) to keep the
project installable via pip on multiple OSes.

It performs a best-effort TCP forward from a public port to a local port and
records basic connection events and HTTP request lines (when detected).

Limitations:
- HTTP logging is best-effort and focuses on the request line/host.
- It does not aim to be a full-featured reverse proxy (chunking nuances,
  websockets, HTTP/2, etc.). For webhook/callback testing over HTTP/1.1 this
  is typically sufficient.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


HTTP_METHODS = {
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
}


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Logger:
    def __init__(self, log_file: Path, name: str):
        self.log_file = log_file
        self.name = name
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def write(self, message: str) -> None:
        line = f"[{_ts()}] [{self.name}] {message}\n"
        self.log_file.open("a", encoding="utf-8").write(line)


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while not reader.at_eof():
            data = await reader.read(64 * 1024)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def _try_parse_http_request(head: bytes) -> Optional[Tuple[str, str, str]]:
    """Return (method, path, host) if head looks like an HTTP request."""
    try:
        text = head.decode("iso-8859-1", errors="replace")
    except Exception:
        return None

    # Only consider the header portion.
    header_end = text.find("\r\n\r\n")
    if header_end == -1:
        return None

    header_text = text[:header_end]
    lines = header_text.split("\r\n")
    if not lines:
        return None

    parts = lines[0].split(" ")
    if len(parts) < 3:
        return None

    method, path, proto = parts[0].upper(), parts[1], parts[2]
    if method not in HTTP_METHODS:
        return None
    if not proto.startswith("HTTP/"):
        return None

    host = ""
    for ln in lines[1:]:
        if ln.lower().startswith("host:"):
            host = ln.split(":", 1)[1].strip()
            break

    return method, path, host


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    *,
    target_host: str,
    target_port: int,
    logger: Logger,
    http_peek_timeout: float,
) -> None:
    peer = client_writer.get_extra_info("peername")
    peer_str = f"{peer[0]}:{peer[1]}" if isinstance(peer, tuple) else str(peer)
    logger.write(f"conn accepted from {peer_str}")

    initial = b""
    try:
        initial = await asyncio.wait_for(client_reader.readuntil(b"\r\n\r\n"), timeout=http_peek_timeout)
    except asyncio.IncompleteReadError as e:
        initial = e.partial
    except asyncio.LimitOverrunError:
        initial = b""
    except asyncio.TimeoutError:
        initial = b""

    req = _try_parse_http_request(initial) if initial else None
    if req:
        method, path, host = req
        logger.write(f"http {method} {path} host={host or '-'} from {peer_str}")

    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(target_host, target_port)
    except Exception as e:
        logger.write(f"upstream connect failed to {target_host}:{target_port} error={e}")
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except Exception:
            pass
        return

    # Send the peeked bytes (if any) upstream.
    if initial:
        upstream_writer.write(initial)
        await upstream_writer.drain()

    # Bidirectional piping.
    t1 = asyncio.create_task(_pipe(client_reader, upstream_writer))
    t2 = asyncio.create_task(_pipe(upstream_reader, client_writer))
    done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    logger.write(f"conn closed from {peer_str}")


async def run_server(
    *,
    name: str,
    public_port: int,
    local_port: int,
    log_file: Path,
    bind_host: str = "127.0.0.1",
    target_host: str = "127.0.0.1",
    http_peek_timeout: float = 0.5,
) -> None:
    logger = Logger(log_file, name)
    logger.write(f"starting proxy bind={bind_host}:{public_port} -> {target_host}:{local_port}")

    server = await asyncio.start_server(
        lambda r, w: handle_client(
            r,
            w,
            target_host=target_host,
            target_port=local_port,
            logger=logger,
            http_peek_timeout=http_peek_timeout,
        ),
        host=bind_host,
        port=public_port,
        reuse_address=True,
    )

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _request_stop(*_args):
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows: signal handlers in asyncio are limited
            signal.signal(sig, lambda *_: _request_stop())

    async with server:
        logger.write("proxy ready")
        await stop.wait()

    logger.write("proxy stopped")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Webhook Tunnel embedded proxy")
    parser.add_argument("--name", required=True)
    parser.add_argument("--public-port", type=int, required=True)
    parser.add_argument("--local-port", type=int, required=True)
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--bind-host", default="127.0.0.1")
    parser.add_argument("--target-host", default="127.0.0.1")
    parser.add_argument("--http-peek-timeout", type=float, default=0.5)
    args = parser.parse_args(argv)

    log_path = Path(args.log_file).expanduser()
    try:
        asyncio.run(
            run_server(
                name=args.name,
                public_port=args.public_port,
                local_port=args.local_port,
                log_file=log_path,
                bind_host=args.bind_host,
                target_host=args.target_host,
                http_peek_timeout=args.http_peek_timeout,
            )
        )
        return 0
    except Exception as e:
        # Last-resort: write to the log file if possible.
        try:
            Logger(log_path, args.name).write(f"fatal error: {e}")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

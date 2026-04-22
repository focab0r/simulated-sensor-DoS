"""
tcp_hold.py — TCP connection holder / stress tester
-----------------------------------------------------
Opens as many TCP connections as possible to the target host:port and keeps
them alive by sending a slow, partial HTTP request (Slowloris style).
Useful for testing --limit-concurrency and --backlog settings in uvicorn.

Usage:
    python tcp_hold.py                          # defaults: 172.20.0.20:8000
    python tcp_hold.py --host 127.0.0.1 --port 8000
    python tcp_hold.py --connections 200 --interval 5
"""

import argparse
import socket
import time
import threading
import sys
from datetime import datetime


# ── Config defaults ────────────────────────────────────────────────────────────
DEFAULT_HOST        = "172.20.0.20"
DEFAULT_PORT        = 8000
DEFAULT_CONNECTIONS = 100       # how many sockets to try to open
DEFAULT_INTERVAL    = 10        # seconds between keep-alive trickles
CONNECT_TIMEOUT     = 5         # seconds to wait for TCP handshake
SOCKET_TIMEOUT      = 30        # seconds before a socket is considered dead


# ── Shared state ───────────────────────────────────────────────────────────────
lock            = threading.Lock()
alive_sockets   = []        # sockets currently held open
dead_count      = 0         # sockets that died
refused_count   = 0         # connection refused (port closed / backlog full)


def ts():
    return datetime.now().strftime("%H:%M:%S")


def log(msg, color=""):
    RESET  = "\033[0m"
    colors = {"red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
               "cyan": "\033[96m", "dim": "\033[2m"}
    prefix = colors.get(color, "")
    print(f"{prefix}[{ts()}] {msg}{RESET}", flush=True)


# ── Socket worker ──────────────────────────────────────────────────────────────
def hold_connection(host: str, port: int, idx: int, interval: int):
    """
    Open one TCP socket and keep it alive by sending an incomplete HTTP
    request header every `interval` seconds. The server keeps the connection
    open waiting for the rest of the headers that never arrive.
    """
    global dead_count, refused_count

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(CONNECT_TIMEOUT)
        sock.connect((host, port))
        sock.settimeout(SOCKET_TIMEOUT)

        # Send a partial HTTP/1.1 request — no blank line, so the server
        # keeps waiting for the rest of the headers indefinitely.
        partial_request = (
            f"GET /sensor HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"User-Agent: tcp-hold/{idx}\r\n"
            f"Accept: */*\r\n"
            # intentionally NOT sending the final \r\n that completes headers
        )
        sock.sendall(partial_request.encode())

        with lock:
            alive_sockets.append(sock)
            log(f"[#{idx:04d}] connected  — alive: {len(alive_sockets)}", "green")

        # Keep the connection open by trickling one extra header line
        # every `interval` seconds — this resets the server-side read timeout.
        while True:
            time.sleep(interval)
            try:
                # Send a dummy header continuation to keep the socket warm
                sock.sendall(f"X-Keep-Alive: {int(time.time())}\r\n".encode())
            except (OSError, BrokenPipeError):
                break

    except ConnectionRefusedError:
        with lock:
            refused_count += 1
            log(f"[#{idx:04d}] REFUSED    — server not accepting (backlog full?)", "red")
        return

    except (socket.timeout, TimeoutError):
        with lock:
            refused_count += 1
            log(f"[#{idx:04d}] TIMEOUT    — could not connect in {CONNECT_TIMEOUT}s", "yellow")
        return

    except OSError as e:
        with lock:
            refused_count += 1
            log(f"[#{idx:04d}] OS ERROR   — {e}", "yellow")
        return

    finally:
        try:
            sock.close()
        except Exception:
            pass
        with lock:
            if sock in alive_sockets:
                alive_sockets.remove(sock)
            dead_count += 1
        log(f"[#{idx:04d}] closed     — alive: {len(alive_sockets)}", "dim")


# ── Stats printer ──────────────────────────────────────────────────────────────
def print_stats(total: int, interval: int):
    """Print a summary line every `interval` seconds."""
    while True:
        time.sleep(interval)
        with lock:
            alive   = len(alive_sockets)
            dead    = dead_count
            refused = refused_count
        log(
            f"── STATS  alive={alive}  dead={dead}  refused={refused}  "
            f"target={total} ──",
            "cyan"
        )


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="TCP connection holder / stress tester")
    parser.add_argument("--host",        default=DEFAULT_HOST,        help="Target host")
    parser.add_argument("--port",        default=DEFAULT_PORT,        type=int, help="Target port")
    parser.add_argument("--connections", default=DEFAULT_CONNECTIONS, type=int, help="Number of connections to open")
    parser.add_argument("--interval",    default=DEFAULT_INTERVAL,    type=int, help="Seconds between keep-alive trickles")
    parser.add_argument("--delay",       default=0.05,                type=float, help="Seconds between spawning each connection thread")
    args = parser.parse_args()

    log(f"Target        : {args.host}:{args.port}", "cyan")
    log(f"Connections   : {args.connections}", "cyan")
    log(f"Keep-alive    : every {args.interval}s", "cyan")
    log(f"Spawn delay   : {args.delay}s between threads", "cyan")
    log("Press Ctrl+C to release all connections and exit.\n", "yellow")

    # Stats printer thread
    stats_thread = threading.Thread(
        target=print_stats, args=(args.connections, args.interval * 2), daemon=True
    )
    stats_thread.start()

    # Spawn one thread per connection
    threads = []
    for i in range(1, args.connections + 1):
        t = threading.Thread(
            target=hold_connection,
            args=(args.host, args.port, i, args.interval),
            daemon=True,
        )
        t.start()
        threads.append(t)
        try:
            time.sleep(args.delay)   # slight ramp-up to avoid instant SYN flood
        except KeyboardInterrupt:
            break

    log("All connection threads spawned. Holding... (Ctrl+C to stop)\n", "cyan")

    # Block here indefinitely — only Ctrl+C breaks out.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    log("\nCtrl+C received — closing all sockets...", "yellow")
    with lock:
        for s in list(alive_sockets):
            try:
                s.close()
            except Exception:
                pass
        alive_sockets.clear()

    log(f"Done. Held {dead_count} connections total.", "cyan")
    sys.exit(0)


if __name__ == "__main__":
    main()
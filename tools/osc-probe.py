#!/usr/bin/env python3
"""Dump and drive the VRChat OSC wire. Standard library only, no venv or install.

Diagnostic strings here stay ASCII: a Windows console decoding as cp1252 mangles
anything else, and this tool exists to be readable when something has gone wrong.

Talks to whatever holds the ports: the Av3Emulator in play mode (`docs/verify.md`
§OSC) or a running VRChat client. It is a wire instrument and holds no mapping
logic; the moment it needs any, it has become vrc-bridge and belongs there.

  python tools/osc-probe.py --listen 5
  python tools/osc-probe.py /avatar/parameters/MyFloat=0.42 /input/Jump=1

Protocol reference is docs/osc.md: address families, wire types, and where the
emulator's implementation differs from the client's.
"""
import argparse
import collections
import socket
import struct
import sys
import time

DEFAULT_SEND_PORT = 9000   # VRChat and the emulator both listen here
DEFAULT_LISTEN_PORT = 9001  # ...and both send here


def _pad(raw):
    return raw + b"\0" * ((4 - len(raw) % 4) % 4)


def encode(address, *args):
    out = _pad(address.encode() + b"\0")
    tags = ","
    body = b""
    for arg in args:
        if isinstance(arg, bool):
            tags += "T" if arg else "F"   # OSC 1.0 booleans are type tags, no payload
        elif isinstance(arg, int):
            tags += "i"
            body += struct.pack(">i", arg)
        elif isinstance(arg, float):
            tags += "f"
            body += struct.pack(">f", arg)
        else:
            tags += "s"
            body += _pad(str(arg).encode() + b"\0")
    return out + _pad(tags.encode() + b"\0") + body


def _read_string(buf, i):
    end = buf.index(b"\0", i)
    return buf[i:end].decode("utf-8", "replace"), (end + 4) - (end % 4)


def decode(buf, out):
    """Append (address, typetag, args) for a packet, recursing into bundles."""
    if buf.startswith(b"#bundle\0"):
        i = 16
        while i < len(buf):
            size = struct.unpack_from(">i", buf, i)[0]
            decode(buf[i + 4:i + 4 + size], out)
            i += 4 + size
        return out
    address, i = _read_string(buf, 0)
    tags, i = _read_string(buf, i)
    args = []
    for tag in tags[1:]:
        if tag == "f":
            args.append(struct.unpack_from(">f", buf, i)[0]); i += 4
        elif tag == "i":
            args.append(struct.unpack_from(">i", buf, i)[0]); i += 4
        elif tag == "s":
            text, i = _read_string(buf, i); args.append(text)
        elif tag == "T":
            args.append(True)
        elif tag == "F":
            args.append(False)
        else:
            args.append("<unhandled %s>" % tag)
    out.append((address, tags, args))
    return out


def parse_send(spec):
    """'/addr=value' -> (address, typed value). Refuses a shell-mangled address."""
    address, sep, raw = spec.partition("=")
    if not sep:
        sys.exit("Not an assignment: %r. Expected /some/address=value." % spec)
    if not address.startswith("/"):
        # Git Bash rewrites a leading-slash argument into a Windows path, so
        # /avatar/parameters/X is sent as C:/Program Files/Git/avatar/... to a
        # socket that accepts it and silently ignores it. Refusing beats a run
        # that looks like the receiver rejected the value.
        sys.exit(
            "Address %r does not start with '/'; the shell rewrote it.\n"
            "Fix: prefix the command with MSYS_NO_PATHCONV=1, or run it from PowerShell."
            % address
        )
    low = raw.lower()
    if low in ("true", "false"):
        return address, low == "true"
    try:
        return address, float(raw) if ("." in raw or "e" in low) else int(raw)
    except ValueError:
        return address, raw


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sends", nargs="*", metavar="ADDR=VALUE",
                    help="send before listening; bare int/float/true/false are typed as written")
    ap.add_argument("--listen", type=float, default=5.0, metavar="SECS",
                    help="seconds to listen after sending (default 5)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=DEFAULT_SEND_PORT,
                    help="port to send to (default %d)" % DEFAULT_SEND_PORT)
    ap.add_argument("--listen-port", type=int, default=DEFAULT_LISTEN_PORT,
                    help="port to bind (default %d)" % DEFAULT_LISTEN_PORT)
    ap.add_argument("--raw", action="store_true",
                    help="print every datagram as it arrives instead of a summary")
    args = ap.parse_args()

    sends = [parse_send(s) for s in args.sends]

    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        rx.bind((args.host, args.listen_port))
    except OSError as exc:
        sys.exit("Cannot bind %s:%d: %s\nAnother OSC consumer (VRChat, vrc-bridge) already holds it."
                 % (args.host, args.listen_port, exc))
    rx.settimeout(0.2)
    print("listening %s:%d for %.1fs" % (args.host, args.listen_port, args.listen), flush=True)

    if sends:
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for address, value in sends:
            tx.sendto(encode(address, value), (args.host, args.port))
            print("sent %s = %r (%s)" % (address, value, type(value).__name__), flush=True)

    counts = collections.Counter()
    endpoints = collections.Counter()
    first = {}
    datagrams = 0
    started = time.time()
    while time.time() - started < args.listen:
        try:
            data, source = rx.recvfrom(65535)
        except socket.timeout:
            continue
        datagrams += 1
        endpoints[source] += 1
        elapsed = time.time() - started
        for address, tags, values in decode(data, []):
            counts[address] += 1
            first.setdefault(address, (tags, values, elapsed))
            if args.raw:
                print("  %8.3fs %-46s %-4s %r" % (elapsed, address, tags, values), flush=True)

    if not datagrams:
        print("--- nothing received ---", flush=True)
        return
    print("--- %d datagrams from %s ---"
          % (datagrams, ", ".join("%s:%d" % e for e in endpoints)), flush=True)
    if args.raw:
        return
    for address, count in sorted(counts.items()):
        tags, values, elapsed = first[address]
        print("  %-46s x%-4d first@%.3fs %-4s %r" % (address, count, elapsed, tags, values),
              flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Dump and drive the VRChat OSC wire. Standard library only, no venv or install.

Talks to whatever holds the ports: the Av3Emulator in play mode (`docs/verify.md`
Sec OSC) or a running VRChat client. A wire instrument holding no mapping logic; the
moment it needs any it has become vrc-bridge and belongs there.

  python tools/osc-probe.py --listen 5
  python tools/osc-probe.py /avatar/parameters/MyFloat=0.42 /input/Jump=1

Argument types are exact and are not coerced at the far end: `1` is an int and
`1.0` a float, and sending the wrong one is a silent no-op. docs/osc.md has the
rule and the rest of the protocol.

Diagnostics stay ASCII: a Windows console decoding as cp1252 mangles anything
else, and this tool exists to be readable when something has gone wrong.
"""
import argparse
import collections
import socket
import struct
import sys
import time

DEFAULT_SEND_PORT = 9000    # VRChat and the emulator both listen here
DEFAULT_BIND_PORT = 9001    # ...and both send here


class Malformed(Exception):
    """A datagram this decoder will not guess at."""


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
    end = buf.find(b"\0", i)
    if end < 0:
        raise Malformed("unterminated string")
    return buf[i:end].decode("utf-8", "replace"), (end + 4) - (end % 4)


def _unpack(fmt, buf, i, size):
    if i + size > len(buf):
        raise Malformed("truncated argument")
    return struct.unpack_from(fmt, buf, i)[0], i + size


def decode(buf, out):
    """Append (address, typetag, args) per message, recursing into bundles.

    Stops at the first unknown type tag rather than continuing: argument sizes are
    tag-derived, so guessing one desynchronises the cursor and every later value
    decodes as garbage from the wrong offset.
    """
    if buf.startswith(b"#bundle\0"):
        i = 16
        while i < len(buf):
            size, i = _unpack(">i", buf, i, 4)
            decode(buf[i:i + size], out)
            i += size
        return out
    address, i = _read_string(buf, 0)
    tags, i = _read_string(buf, i)
    args = []
    for tag in tags[1:]:
        if tag == "f":
            value, i = _unpack(">f", buf, i, 4)
            args.append(value)
        elif tag == "i":
            value, i = _unpack(">i", buf, i, 4)
            args.append(value)
        elif tag == "s":
            value, i = _read_string(buf, i)
            args.append(value)
        elif tag in "TF":
            args.append(tag == "T")
        else:
            raise Malformed("unsupported type tag %r in %r at %s" % (tag, tags, address))
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
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Types are exact: 1 sends an int, 1.0 a float, true a bool. See docs/osc.md.")
    ap.add_argument("sends", nargs="*", metavar="ADDR=VALUE")
    ap.add_argument("--listen", type=float, default=5.0, metavar="SECS",
                    help="seconds to listen after sending (default 5)")
    ap.add_argument("--host", default="127.0.0.1", help="send target (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=DEFAULT_SEND_PORT,
                    help="port to send to (default %d)" % DEFAULT_SEND_PORT)
    ap.add_argument("--bind", default="127.0.0.1",
                    help="address to listen on; loopback by default, so a remote --host "
                         "also needs --bind 0.0.0.0")
    ap.add_argument("--bind-port", type=int, default=DEFAULT_BIND_PORT,
                    help="port to bind (default %d)" % DEFAULT_BIND_PORT)
    ap.add_argument("--raw", action="store_true",
                    help="print each datagram as it arrives instead of a summary")
    args = ap.parse_args()

    sends = [parse_send(s) for s in args.sends]

    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # No SO_REUSEADDR: on Windows it lets a second copy bind the same port, after
    # which delivery goes to one of them arbitrarily and the other reports an empty
    # capture. A stale background run should fail loud here instead.
    try:
        rx.bind((args.bind, args.bind_port))
    except OSError as exc:
        sys.exit("Cannot bind %s:%d: %s\nAnother OSC consumer (VRChat, vrc-bridge, or a "
                 "still-running copy of this probe) already holds it."
                 % (args.bind, args.bind_port, exc))
    rx.settimeout(0.2)
    print("listening %s:%d for %.1fs" % (args.bind, args.bind_port, args.listen), flush=True)

    if sends:
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for address, value in sends:
            tx.sendto(encode(address, value), (args.host, args.port))
            print("sent %s = %r (%s)" % (address, value, type(value).__name__), flush=True)

    counts = collections.Counter()
    endpoints = collections.Counter()
    first = {}
    datagrams = malformed = 0
    started = time.time()
    while time.time() - started < args.listen:
        try:
            data, source = rx.recvfrom(65535)
        except socket.timeout:
            continue
        datagrams += 1
        endpoints[source] += 1
        elapsed = time.time() - started
        try:
            messages = decode(data, [])
        except (Malformed, struct.error, ValueError) as exc:
            malformed += 1
            print("  %8.3fs undecodable datagram from %s:%d: %s" % (elapsed, source[0], source[1], exc),
                  flush=True)
            continue
        for address, tags, values in messages:
            counts[address] += 1
            first.setdefault(address, (tags, values, elapsed))
            if args.raw:
                print("  %8.3fs %-46s %-4s %r" % (elapsed, address, tags, values), flush=True)

    if not datagrams:
        print("--- nothing received ---", flush=True)
        return
    print("--- %d datagrams from %s%s ---"
          % (datagrams, ", ".join("%s:%d" % e for e in endpoints),
             ", %d undecodable" % malformed if malformed else ""), flush=True)
    if args.raw:
        return
    for address, count in sorted(counts.items()):
        tags, values, elapsed = first[address]
        print("  %-46s x%-4d first@%.3fs %-4s %r" % (address, count, elapsed, tags, values),
              flush=True)


if __name__ == "__main__":
    main()

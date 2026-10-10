"""Read a RecordPlay take: what changed when, distances, and waiting on a take in flight.

Usage (Python 3.13, standard library only):
  report_play.py changes  FILE [--who L] [--from F] [--to F] [--cols a,b] [--eps 0.0001] [--max N]
  report_play.py distance FILE COL (--point x,y,z | --col COL2 [--who2 C1] | --step) [--who L] [--from F] [--to F] [--max N]
  report_play.py wait     FILE FRAME|+N [--who L] [--timeout S]

FILE is the path RecordPlay.Run returns. RecordPlay's class docstring in vrc-unity-tools declares the
file's layout; docs/unity-tools.md is the door's contract.
"""
import argparse
import math
import re
import sys
import time

FIXED = ("frame", "t", "dt", "who")
EVENT = re.compile(r"^# f=(\d+) (.*)$")


class Take:
    def __init__(self, path):
        self.path = path
        self.comments, self.events, self.header, self.rows = [], [], None, []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.endswith("\n"):
                    break  # the writer is mid-line; a cut last cell would otherwise pass the count below
                line = line.rstrip("\n")
                if not line:
                    continue
                if line.startswith("#"):
                    m = EVENT.match(line)
                    if m:
                        self.events.append((int(m.group(1)), m.group(2)))
                    else:
                        self.comments.append(line)
                elif self.header is None:
                    self.header = line.split(",")
                else:
                    cells = line.split(",")
                    if len(cells) != len(self.header):
                        continue  # a row cut mid-write by a reader racing the writer
                    row = dict(zip(self.header, cells))
                    row["frame"] = int(row["frame"])
                    self.rows.append(row)
        if self.header is None:
            sys.exit(f"{path}: no CSV header yet (is this a RecordPlay take?)")

    def stop(self):
        return next((e for e in self.events if e[1].startswith("stopped: ")), None)

    def summary(self):
        by = {}
        for r in self.rows:
            by.setdefault(r["who"], []).append(r["frame"])
        parts = []
        for who, frames in by.items():
            dup = len(frames) - len(set(frames))
            s = sorted(set(frames))
            holes = sum(1 for a, b in zip(s, s[1:]) if b != a + 1)
            parts.append(f"{who}={len(frames)} f{s[0]}..{s[-1]}"
                         + ("" if not dup else f" DUPLICATES={dup}")
                         + ("" if not holes else f" HOLES={holes}"))
        clean = all("DUPLICATES" not in p and "HOLES" not in p for p in parts)
        stop = self.stop()
        return (f"{self.path}: rows {' '.join(parts) or 'none'} | "
                + ("frames contiguous, no duplicate (frame, who)" if clean else "NOT CLEAN")
                + f" | stop: {stop[1][len('stopped: '):] + ' at f' + str(stop[0]) if stop else 'none (take open)'}")


def num(v):
    try:
        return float(v)
    except ValueError:
        return None


def window(lines, cap, frame_of):
    if len(lines) <= cap:
        return lines
    cut = lines[cap]
    return lines[:cap] + [f"... {len(lines) - cap} more lines; continue with --from {frame_of(cut)}"]


def in_range(f, a):
    return (a.from_ is None or f >= a.from_) and (a.to is None or f <= a.to)


def xyz(row, col):
    vals = [num(row.get(f"{col}.{k}", "")) for k in "xyz"]
    return None if None in vals else vals


def cmd_changes(take, a):
    cols = [h for h in take.header if h not in FIXED]
    if a.cols:
        want = a.cols.split(",")
        cols = [h for h in cols if h in want or h.split(".")[0] in want]
        if not cols:
            sys.exit(f"no column matches {a.cols}; columns are: {', '.join(take.header[4:])}")
    out = []  # (frame, text)
    whos = [a.who] if a.who else list(dict.fromkeys(r["who"] for r in take.rows))
    for who in whos:
        rows = [r for r in take.rows if r["who"] == who]
        changes, prev = [], None
        for r in rows:
            if prev is not None and in_range(r["frame"], a):
                d = {}
                for c in cols:
                    x, y = num(prev[c]), num(r[c])
                    moved = (prev[c] != r[c]) if x is None or y is None else abs(y - x) > a.eps
                    if moved:
                        d[c] = (prev[c], r[c])
                if d:
                    changes.append((r["frame"], d, prev, r))
            prev = r
        i = 0
        while i < len(changes):
            j = i
            while (j + 1 < len(changes) and changes[j + 1][0] == changes[j][0] + 1
                   and changes[j + 1][1].keys() == changes[i][1].keys()):
                j += 1
            f0, d0, _, _ = changes[i]
            if j - i >= 2:  # three or more frames of the same columns moving: one run line
                f1, d1, _, _ = changes[j]
                moved = ", ".join(f"{c} {d0[c][0]}->{d1[c][1]}" for c in d0)
                steps = []
                for tf in dict.fromkeys(c.rsplit(".", 1)[0] for c in d0 if c.endswith((".x", ".y", ".z"))):
                    s = [math.dist(xyz(p, tf), xyz(r, tf)) for _, _, p, r in changes[i:j + 1] if xyz(p, tf) and xyz(r, tf)]
                    if s:
                        steps.append(f"{tf} step {min(s):.4f}..{max(s):.4f}")
                out.append((f0, f"f{f0}..{f1} {who} run of {j - i + 1} frames: {moved}" + (f" | {'; '.join(steps)}" if steps else "")))
            else:
                for f, d, _, _ in changes[i:j + 1]:
                    out.append((f, f"f{f} {who} " + "  ".join(f"{c} {v[0]}->{v[1]}" for c, v in d.items())))
            i = j + 1
    for f, text in take.events:
        if in_range(f, a):
            out.append((f, f"f{f} # {text}"))
    out.sort(key=lambda x: (x[0], not x[1].split(" ", 1)[1].startswith("#")))
    print(take.summary())
    for line in window([t for _, t in out], a.max, lambda t: re.match(r"f(\d+)", t).group(1)):
        print(line)


def cmd_distance(take, a):
    modes = sum(x is not None and x is not False for x in (a.point, a.col, a.step or None))
    if modes != 1:
        sys.exit("give exactly one of --point x,y,z, --col COL2 or --step")
    if f"{a.COL}.x" not in take.header:
        sys.exit(f"{a.COL} is not a tf column; tf columns: {', '.join(h[:-2] for h in take.header if h.endswith('.x'))}")
    who = a.who or "L"
    rows = [r for r in take.rows if r["who"] == who]
    other = {}
    if a.col:
        if f"{a.col}.x" not in take.header:
            sys.exit(f"{a.col} is not a tf column")
        other = {r["frame"]: r for r in take.rows if r["who"] == (a.who2 or who)}
    point = [float(v) for v in a.point.split(",")] if a.point else None
    lines, vals, prev = [], [], None
    for r in rows:
        f, p = r["frame"], xyz(r, a.COL)
        if p is None:
            prev = None
            continue
        extra = ""
        if point:
            d = math.dist(p, point)
        elif a.step:
            if prev is None or prev[0] != f - 1:
                prev = (f, p)
                continue
            d, prev = math.dist(p, prev[1]), (f, p)
        else:
            o = other.get(f)
            q = xyz(o, a.col) if o else None
            if q is None:
                continue
            d = math.dist(p, q)
            ya, yb = num(r[f"{a.COL}.yaw"]), num(o[f"{a.col}.yaw"])
            if a.who2 and ya is not None and yb is not None:
                extra = f" dyaw={(yb - ya + 180) % 360 - 180:.3f}"
        if in_range(f, a):
            vals.append((d, f))
            lines.append(f"f{f} {who} {d:.4f}{extra}")
    print(take.summary())
    if vals:
        print(f"{a.COL} over {len(vals)} frames: min {min(vals)[0]:.4f} at f{min(vals)[1]}, max {max(vals)[0]:.4f} at f{max(vals)[1]}")
    for line in window(lines, a.max, lambda t: re.match(r"f(\d+)", t).group(1)):
        print(line)


def cmd_wait(a):
    who, deadline, target = a.who or "L", time.monotonic() + a.timeout, None
    while True:
        try:
            take = Take(a.FILE)
        except FileNotFoundError:
            take = None
        if take:
            frames = [r for r in take.rows if r["who"] == who]
            if target is None and (not a.FRAME.startswith("+") or frames):
                target = int(a.FRAME) if not a.FRAME.startswith("+") else frames[-1]["frame"] + int(a.FRAME[1:])
            hit = next((r for r in frames if target is not None and r["frame"] >= target), None)
            if hit:
                print(", ".join(f"{k}={v}" for k, v in hit.items()))
                return 0
            stop = take.stop()
            if stop:
                print(f"{who} never reached f{target}: {stop[1]} at f{stop[0]}", file=sys.stderr)
                return 2
        if time.monotonic() > deadline:
            last = frames[-1]["frame"] if take and frames else "none"
            print(f"timed out after {a.timeout}s waiting for {who} at f{target}; last {who} frame {last}", file=sys.stderr)
            return 3
        time.sleep(0.5)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("changes", "distance"):
        s = sub.add_parser(name)
        s.add_argument("FILE")
        if name == "distance":
            s.add_argument("COL")
            s.add_argument("--point")
            s.add_argument("--col")
            s.add_argument("--who2")
            s.add_argument("--step", action="store_true")
        else:
            s.add_argument("--cols")
            s.add_argument("--eps", type=float, default=0.0001)
        s.add_argument("--who")
        s.add_argument("--from", dest="from_", type=int)
        s.add_argument("--to", type=int)
        s.add_argument("--max", type=int, default=200)
    w = sub.add_parser("wait")
    w.add_argument("FILE")
    w.add_argument("FRAME")
    w.add_argument("--who")
    w.add_argument("--timeout", type=float, default=120)
    a = ap.parse_args()
    if a.cmd == "wait":
        return cmd_wait(a)
    take = Take(a.FILE)
    (cmd_changes if a.cmd == "changes" else cmd_distance)(take, a)
    return 0


if __name__ == "__main__":
    sys.exit(main())

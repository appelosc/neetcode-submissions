#!/usr/bin/env python3
"""Build an SVG stats card from a NeetCode GitHub-sync repository.

Layout NeetCode uses:  <category>/<problem-slug>/submission-N.<ext>
Dates come from git history (first commit that added each file), so run it
in a full clone (actions/checkout with fetch-depth: 0).

Difficulty comes from difficulty.json next to this script (built from
NeetCode's public problem data, with NeetCode's renamed slugs mapped).
Slugs not in it are looked up on LeetCode once and cached back into the file.
You can also add entries by hand: "some-slug": {"d": "Medium"}.
"""
import collections
import datetime as dt
import html
import json
import math
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "assets/neetcode-card.svg")
USER = os.environ.get("NEETCODE_USER", "")
DIFF_FILE = Path(__file__).with_name("difficulty.json")
WEEKS = 20

LANGS = {
    ".py": ("Python", "#3572A5"), ".js": ("JavaScript", "#f1e05a"),
    ".ts": ("TypeScript", "#3178c6"), ".java": ("Java", "#b07219"),
    ".cpp": ("C++", "#f34b7d"), ".cs": ("C#", "#178600"),
    ".go": ("Go", "#00ADD8"), ".rs": ("Rust", "#dea584"),
    ".kt": ("Kotlin", "#A97BFF"), ".swift": ("Swift", "#F05138"),
    ".sql": ("SQL", "#e38c00"),
}

BG, BORDER, TEXT, MUTED, ACCENT = "#0d1117", "#30363d", "#e6edf3", "#8b949e", "#2ea043"
TRACK = "#21262d"
GRID = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
DIFF = {"Easy": "#00b8a3", "Medium": "#ffc01e", "Hard": "#ff375f"}
UNKNOWN = "#6e7681"


# ---------- data ----------

def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                          text=True, check=True).stdout


def added_dates():
    dates, current = {}, None
    log = git("log", "--reverse", "--diff-filter=A", "--name-only",
              "--format=@@%cI", "--no-renames")
    for line in log.splitlines():
        if line.startswith("@@"):
            current = dt.datetime.fromisoformat(line[2:]).date()
        elif line.strip() and current:
            dates.setdefault(line.strip(), current)
    return dates


def collect():
    dates = added_dates()
    problems, submissions = {}, []
    for f in ROOT.glob("*/*/submission-*.*"):
        rel = f.relative_to(ROOT).as_posix()
        if rel.startswith("."):
            continue
        d = dates.get(rel, dt.date.today())
        submissions.append((d, f.suffix))
        key = f.parts[-2]  # problem slug
        problems[key] = min(problems.get(key, d), d)
    return problems, submissions


def leetcode_difficulty(slug):
    body = json.dumps({"query": "query($s:String!){question(titleSlug:$s){difficulty}}",
                       "variables": {"s": slug}}).encode()
    req = urllib.request.Request("https://leetcode.com/graphql", data=body, headers={
        "Content-Type": "application/json", "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0 neetcode-card"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            q = json.load(r).get("data", {}).get("question")
            return q["difficulty"] if q else None
    except Exception as e:  # network hiccup: just try again next run
        print(f"  lookup failed for {slug}: {e}")
        return None


def difficulties(slugs):
    table = json.loads(DIFF_FILE.read_text()) if DIFF_FILE.exists() else {}
    changed = False
    for slug in slugs:
        if slug in table:
            continue
        d = leetcode_difficulty(slug)
        print(f"  {slug}: {d or 'unknown'}")
        if d:
            table[slug] = {"d": d}
            changed = True
    if changed:
        DIFF_FILE.write_text(json.dumps(dict(sorted(table.items())), separators=(",", ":"), indent=0))
    return table


# ---------- drawing ----------

def esc(s):
    return html.escape(s, quote=True)


def title(slug):
    return " ".join(w.capitalize() for w in slug.split("-"))


def streak(days):
    today = dt.date.today()
    d = today if today in days else today - dt.timedelta(days=1)
    n = 0
    while d in days:
        n += 1
        d -= dt.timedelta(days=1)
    return n


def arc(cx, cy, r, a0, a1):
    """SVG path for a circle arc from angle a0 to a1 (radians, 0 = top, clockwise)."""
    x0, y0 = cx + r * math.sin(a0), cy - r * math.cos(a0)
    x1, y1 = cx + r * math.sin(a1), cy - r * math.cos(a1)
    large = 1 if a1 - a0 > math.pi else 0
    return f"M{x0:.2f},{y0:.2f} A{r},{r} 0 {large} 1 {x1:.2f},{y1:.2f}"


def build_svg(problems, submissions, table):
    W, H = 760, 330
    today = dt.date.today()
    per_day = collections.Counter(d for d, _ in submissions)
    langs = collections.Counter(e for _, e in submissions)
    diff_of = {s: table.get(s, {}).get("d") for s in problems}
    counts = collections.Counter(diff_of.values())
    nc150 = sum(1 for s in problems if table.get(s, {}).get("nc150"))
    recent = sorted(problems.items(), key=lambda kv: kv[1], reverse=True)[:5]
    total = len(problems)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="Segoe UI,Ubuntu,Helvetica,Arial,sans-serif">',
         f'<style>.t{{fill:{TEXT}}}.m{{fill:{MUTED}}}</style>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{BG}" stroke="{BORDER}"/>']
    head = "NeetCode Progress" + (f" · @{USER}" if USER else "")
    s.append(f'<text x="24" y="38" class="t" font-size="19" font-weight="600">{esc(head)}</text>')
    s.append(f'<text x="{W-24}" y="38" class="m" font-size="11" text-anchor="end">updated {today:%Y-%m-%d}</text>')

    # --- Ring: solved, split by difficulty ---
    cx, cy, r = 92, 136, 54
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TRACK}" stroke-width="8"/>')
    segs = [(DIFF[k], counts[k]) for k in ("Easy", "Medium", "Hard")] + [(UNKNOWN, counts[None])]
    segs = [(c, n) for c, n in segs if n]
    gap = 0.06 if len(segs) > 1 else 0
    a = 0.0
    for color, n in segs:
        span = 2 * math.pi * n / total
        if span >= 2 * math.pi - 1e-6:
            s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="8"/>')
        else:
            s.append(f'<path d="{arc(cx, cy, r, a + gap/2, a + span - gap/2)}" fill="none" '
                     f'stroke="{color}" stroke-width="8" stroke-linecap="round"/>')
        a += span
    s.append(f'<text x="{cx}" y="{cy+6}" class="t" font-size="30" font-weight="700" text-anchor="middle">{total}</text>')
    s.append(f'<text x="{cx}" y="{cy+24}" class="m" font-size="11" text-anchor="middle">solved</text>')

    # --- Easy / Medium / Hard rows ---
    rx, bar_w = 172, 150
    rows = [("Easy", counts["Easy"]), ("Medium", counts["Medium"]), ("Hard", counts["Hard"])]
    if counts[None]:
        rows.append(("Other", counts[None]))
    top = cy - 14 * len(rows) + 6
    for i, (name, n) in enumerate(rows):
        y = top + i * 28
        color = DIFF.get(name, UNKNOWN)
        s.append(f'<text x="{rx}" y="{y}" fill="{color}" font-size="13" font-weight="600">{name}</text>')
        s.append(f'<text x="{rx+bar_w}" y="{y}" class="t" font-size="13" font-weight="600" text-anchor="end">{n}</text>')
        s.append(f'<rect x="{rx}" y="{y+6}" width="{bar_w}" height="5" rx="2.5" fill="{TRACK}"/>')
        if n:
            s.append(f'<rect x="{rx}" y="{y+6}" width="{max(5, bar_w*n/total):.1f}" height="5" rx="2.5" fill="{color}"/>')

    # --- Small stats line ---
    stats = [f"{len(submissions)} submissions", f"{streak(set(per_day))} day streak", f"NeetCode 150: {nc150}/150"]
    s.append(f'<text x="24" y="226" class="m" font-size="12">{esc("  ·  ".join(stats))}</text>')

    # --- Languages ---
    ly, lw = 262, 298
    s.append(f'<text x="24" y="{ly-10}" class="m" font-size="12">Languages</text>')
    s.append(f'<clipPath id="lb"><rect x="24" y="{ly}" width="{lw}" height="8" rx="4"/></clipPath><g clip-path="url(#lb)">')
    x, legend, tot = 24.0, [], sum(langs.values()) or 1
    for ext, n in langs.most_common():
        name, color = LANGS.get(ext, (ext.lstrip(".").upper(), MUTED))
        w = lw * n / tot
        s.append(f'<rect x="{x:.1f}" y="{ly}" width="{w:.1f}" height="8" fill="{color}"/>')
        x += w
        legend.append((name, color, 100 * n / tot))
    s.append('</g>')
    lx = 24
    for name, color, pct in legend[:4]:
        label = f"{name} {pct:.0f}%"
        s.append(f'<circle cx="{lx+4}" cy="{ly+24}" r="4" fill="{color}"/>')
        s.append(f'<text x="{lx+12}" y="{ly+28}" class="t" font-size="11">{esc(label)}</text>')
        lx += 22 + 7 * len(label)

    # --- Right column ---
    px = 372
    s.append(f'<line x1="{px-24}" y1="64" x2="{px-24}" y2="{H-24}" stroke="{BORDER}"/>')

    # Activity grid
    cell, g, gy = 11, 3, 82
    s.append(f'<text x="{px}" y="{gy-10}" class="m" font-size="12">Activity · last {WEEKS} weeks</text>')
    start = today - dt.timedelta(days=today.weekday() + 7 * (WEEKS - 1))
    peak = max(per_day.values(), default=1)
    for w in range(WEEKS):
        for d in range(7):
            day = start + dt.timedelta(days=w * 7 + d)
            if day > today:
                continue
            n = per_day.get(day, 0)
            lvl = 0 if n == 0 else min(4, 1 + int(3 * (n - 1) / max(peak - 1, 1)))
            s.append(f'<rect x="{px + w*(cell+g)}" y="{gy + d*(cell+g)}" width="{cell}" height="{cell}" '
                     f'rx="2" fill="{GRID[lvl]}"><title>{day}: {n}</title></rect>')

    # Recent solves
    ry = 210
    s.append(f'<text x="{px}" y="{ry-10}" class="m" font-size="12">Recently solved</text>')
    if not recent:
        s.append(f'<text x="{px}" y="{ry+12}" class="m" font-size="13">Nothing yet</text>')
    for i, (slug, d) in enumerate(recent):
        y = ry + 10 + i * 21
        name = title(slug)
        name = name if len(name) <= 36 else name[:35] + "…"
        color = DIFF.get(diff_of.get(slug), UNKNOWN)
        s.append(f'<circle cx="{px+4}" cy="{y-4}" r="3.5" fill="{color}"/>')
        s.append(f'<text x="{px+14}" y="{y}" class="t" font-size="13">{esc(name)}</text>')
        s.append(f'<text x="{W-24}" y="{y}" class="m" font-size="11" text-anchor="end">{d:%b %d}</text>')

    s.append('</svg>')
    return "\n".join(s)


if __name__ == "__main__":
    problems, submissions = collect()
    table = difficulties(problems)
    out = ROOT / OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_svg(problems, submissions, table), encoding="utf-8")
    print(f"{len(problems)} problems, {len(submissions)} submissions -> {out}")

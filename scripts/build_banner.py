#!/usr/bin/env python3
"""Regenerates assets/banner.svg, including the live GitHub contribution graph.

Usage (locally):   GH_USER=<github-username> GH_TOKEN=<token> python scripts/build_banner.py
Usage (Actions):   see .github/workflows/update-banner.yml (token and user are provided automatically)

Without GH_USER / GH_TOKEN the banner is rendered with an empty graph.
Only the Python standard library is used.
"""
import base64
import json
import os
import sys
import urllib.request
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------ content ---
HANDLE = "Jaack_o"
TOP_LEFT = "PEOPLE & TECH, END TO END"
TOP_RIGHT = "11 YEARS OF EXPERIENCE"
ROLE = "MINECRAFT SERVER ADMIN"
TAGLINE = ["Running Minecraft servers:", "the people and the tech."]
STAT_NUMBER, STAT_LABEL = "200,000+", "REGISTERED PLAYERS"
COLUMNS = [
    ("01", "TEAM MANAGEMENT", "from guides to admins"),
    ("02", "SERVER TECH", "plugins, economy, store"),
    ("03", "MODERATION", "disputes & sensitive cases"),
    ("04", "DISCORD DEV", "development & integration"),
]
FOOTER = ("JAACK_O", "FRENCH MINECRAFT COMMUNITY", "HEAD ADMIN")

# ------------------------------------------------------------------- design ---
W, H = 1000, 666
BG, PANEL, BORDER, RULE = "#0a0f1e", "#0d1428", "#1b2547", "#18203f"
INK, MUTED, GOLD, NODE = "#eef1ff", "#7f89b3", "#f2c14e", "#3a4574"
LEVELS = ["#131a30", "#4b3d17", "#86691f", "#c99a2c", "#f2c14e"]
SANS = "'Avenir Next','Segoe UI','Helvetica Neue',system-ui,-apple-system,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
LEVEL_OF = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

PH = (838, 196, 88)  # photo: centre x, centre y, radius
NET = {"A": (668, 98), "B": (728, 134), "C": (778, 86), "D": (884, 76), "E": (944, 122),
       "F": (942, 248), "G": (918, 304), "H": (766, 304), "I": (690, 254), "J": (656, 178)}
NET_EDGES = ["AB", "BC", "CD", "DE", "EF", "FG", "GH", "HI", "IJ", "JA", "BJ", "BI"]
NET_GOLD = {"C", "F"}

PANEL_Y, PANEL_H = 336, 168



# -------------------------------------------------------------- hero: voxel ---
HERO = "voxel"  # "voxel" = isometric Minecraft-style blocks, "photo" = profile picture (assets/pfp.jpg)

BLOCKS = {"navy": ("#34479a", "#202d6b", "#151f4a"), "gold": ("#f6d36e", "#c99a2c", "#86691f")}
HEIGHTS = [  # number of blocks stacked on each cell of the 5x5 terrain
    [1, 1, 1, 0, 0],
    [1, 2, 2, 1, 0],
    [1, 2, 4, 2, 1],
    [0, 1, 2, 3, 1],
    [0, 0, 1, 1, 1],
]
GOLD_BLOCKS = {(2, 2, 3), (3, 3, 2), (1, 2, 1)}  # (row, col, level)
FLOATING = [(704, 152, 9, "navy", -1.0), (914, 120, 11, "gold", -3.0), (768, 94, 7, "gold", -2.0)]


def _shade(color, f):
    h = color.lstrip("#")
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(int(h[i:i + 2], 16) * f))) for i in (0, 2, 4))


def _cube(cx, cy, a, kind, seed):
    """One isometric cube. (cx, cy) is the centre of its top face, `a` its half-width."""
    top, left, right = BLOCKS[kind]
    n, out = 4, []
    for i in range(n):
        for j in range(n):
            f = (0.9, 0.97, 1.0, 1.06, 1.12)[(seed * 7 + i * 13 + j * 5 + i * j * 3) % 5]
            pts = " ".join(
                f"{cx - a + (u + v) * a / n:.1f},{cy + (v - u) * a / (2 * n):.1f}"
                for u, v in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)))
            out.append(f'<polygon points="{pts}" fill="{_shade(top, f)}"/>')
    out.append(f'<polygon points="{cx-a},{cy} {cx},{cy+a/2} {cx},{cy+a/2+a} {cx-a},{cy+a}" fill="{left}"/>')
    out.append(f'<polygon points="{cx},{cy+a/2} {cx+a},{cy} {cx+a},{cy+a} {cx},{cy+a/2+a}" fill="{right}"/>')
    out.append(f'<polygon points="{cx-a},{cy} {cx},{cy-a/2} {cx+a},{cy} {cx},{cy+a/2}" fill="none" stroke="{BG}" stroke-opacity="0.35" stroke-width="0.8"/>')
    out.append(f'<path d="M{cx-a},{cy} V{cy+a} L{cx},{cy+a/2+a} L{cx+a},{cy+a} V{cy} M{cx},{cy+a/2} V{cy+a/2+a}" fill="none" stroke="{BG}" stroke-opacity="0.55" stroke-width="0.9"/>')
    return "".join(out)


def voxel_hero():
    a, ox, oy, n = 28, 805, 138, len(HEIGHTS)
    scr = lambda I, J: (ox + (I - J) * a, oy + a / 2 + (I + J) * a / 2)  # ground-plane lattice point
    parts = [f'<circle cx="{ox}" cy="128" r="120" fill="url(#gold-glow)"/>',
             f'<ellipse cx="{ox}" cy="{scr(n/2, n/2)[1]:.0f}" rx="{n*a+20}" ry="46" fill="#000" fill-opacity="0.35"/>']
    for t in range(n + 1):  # faint ground grid
        for p, q in ((scr(t, 0), scr(t, n)), (scr(0, t), scr(n, t))):
            parts.append(f'<line x1="{p[0]}" y1="{p[1]:.1f}" x2="{q[0]}" y2="{q[1]:.1f}" stroke="{NODE}" stroke-opacity="0.45"/>')
    for s in range(2 * n - 1):  # painter's order: back to front, bottom to top
        for i in range(n):
            j = s - i
            if 0 <= j < n:
                for k in range(HEIGHTS[i][j]):
                    kind = "gold" if (i, j, k) in GOLD_BLOCKS else "navy"
                    parts.append(_cube(ox + (i - j) * a, oy + (i + j) * a / 2 - k * a, a, kind, i * 5 + j * 3 + k))
    for x, y, r, kind, delay in FLOATING:
        parts.append(f'<g class="bob" style="animation-delay:{delay}s">{_cube(x, y, r, kind, int(x) % 7)}</g>')
    return "\n    ".join(parts)

# --------------------------------------------------------------------- data ---
def fetch_calendar(login, token):
    query = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
      totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-banner", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        raise RuntimeError(f"GitHub API error: {payload.get('errors') or 'user not found'}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def parse_calendar(cal):
    """GraphQL calendar -> weeks of (date, count, level) plus total, current streak, record."""
    weeks = [[(date.fromisoformat(d["date"]), d["contributionCount"], LEVEL_OF[d["contributionLevel"]])
              for d in w["contributionDays"]] for w in cal["weeks"]]
    days = [d for w in weeks for d in w]
    counts = [c for _, c, _ in days]
    record = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        record = max(record, run)
    tail = counts[:-1] if counts and counts[-1] == 0 else counts  # today may not be over yet
    streak = 0
    for c in reversed(tail):
        if c == 0:
            break
        streak += 1
    return {"total": cal["totalContributions"], "streak": streak, "record": record, "weeks": weeks}


# ------------------------------------------------------------------- render ---
def network():
    out = []
    for a, b in NET_EDGES:
        (x1, y1), (x2, y2) = NET[a], NET[b]
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{NODE}" stroke-opacity="0.55"/>')
    for k, (x, y) in NET.items():
        if k in NET_GOLD:
            out.append(f'<circle cx="{x}" cy="{y}" r="13" fill="{GOLD}" fill-opacity="0.13"/>'
                       f'<circle cx="{x}" cy="{y}" r="4.5" fill="{GOLD}"/>')
        else:
            out.append(f'<rect x="{x-2.5}" y="{y-2.5}" width="5" height="5" fill="{NODE}"/>')
    return "\n    ".join(out)


def heatmap(data):
    """Header numbers, month labels and the week grid. `data` is None for the empty state."""
    x0, width = 376, 540
    weeks = data["weeks"] if data else [[(None, 0, 0)] * 7 for _ in range(53)]
    pitch = width / len(weeks)
    cell = pitch - 1.8
    top = PANEL_Y + 68

    def stat(value, label, first=False):
        gap = "" if first else ' dx="28"'
        return (f'<tspan{gap} font-family="{SANS}" font-size="22" font-weight="800" fill="{GOLD}">{value}</tspan>'
                f'<tspan dx="8" font-family="{MONO}" font-size="10" letter-spacing="1.8" fill="{MUTED}">{label}</tspan>')

    fmt = (lambda n: f"{n:,}") if data else (lambda n: "—")
    header = ('<text x="%d" y="%d">' % (x0, PANEL_Y + 38)
              + stat(fmt(data["total"] if data else 0), "CONTRIBUTIONS", True)
              + stat(fmt(data["streak"] if data else 0), "DAY STREAK")
              + stat(fmt(data["record"] if data else 0), "DAY RECORD") + "</text>")

    cells, labels, prev_month, last_label = [], [], None, -9
    for i, week in enumerate(weeks):
        first = week[0][0]
        if first and first.month != prev_month:
            if i - last_label >= 3:
                labels.append(f'<text x="{x0 + i * pitch:.1f}" y="{PANEL_Y + 60}">{MONTHS[first.month - 1]}</text>')
                last_label = i
            prev_month = first.month
        for r, (d, count, level) in enumerate(week):
            row = ((d.weekday() + 1) % 7) if d else r
            cells.append(f'<rect x="{x0 + i * pitch:.1f}" y="{top + row * pitch:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
                         f'rx="1.6" fill="{LEVELS[level]}"/>')
    months = f'<g font-family="{MONO}" font-size="9" letter-spacing="1.4" fill="{MUTED}" fill-opacity="0.9">{"".join(labels)}</g>'
    return header + months + "".join(cells)


def render(data):
    cols, colw = [], (W - 112) / 4
    cy = PANEL_Y + PANEL_H + 18  # top of the four columns
    for i, (num, title, sub) in enumerate(COLUMNS):
        x = 56 + i * colw + (24 if i else 0)
        cols.append(f'<text x="{x:.1f}" y="{cy+20}" font-size="11" font-weight="700" fill="{GOLD}" letter-spacing="1.5">{escape(num)}</text>'
                    f'<text x="{x:.1f}" y="{cy+43}" font-size="12.5" font-weight="700" fill="{INK}" letter-spacing="2">{escape(title)}</text>'
                    f'<text x="{x:.1f}" y="{cy+65}" font-size="11.5" fill="{MUTED}">{escape(sub)}</text>')
        if i:
            cols.append(f'<line x1="{56 + i * colw:.1f}" y1="{cy}" x2="{56 + i * colw:.1f}" y2="{cy+72}" stroke="{RULE}"/>')
    foot_y = H - 26
    grid = "".join(f'<line x1="{x}" y1="72" x2="{x}" y2="318" stroke="{RULE}" stroke-opacity="0.7"/>' for x in (330, 450, 570))
    if HERO == "photo":
        pfp = base64.b64encode((ROOT / "assets" / "pfp.jpg").read_bytes()).decode()
        hero = (f'<g>{network()}</g>'
                f'<circle class="pulse" cx="{PH[0]}" cy="{PH[1]}" r="{PH[2]+8}" fill="none" stroke="{GOLD}" stroke-width="2" opacity="0"/>'
                f'<circle cx="{PH[0]}" cy="{PH[1]}" r="{PH[2]+8}" fill="{BG}" stroke="{GOLD}" stroke-width="2.5"/>'
                f'<image x="{PH[0]-PH[2]}" y="{PH[1]-PH[2]}" width="{PH[2]*2}" height="{PH[2]*2}" clip-path="url(#pfp)" '
                f'preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{pfp}"/>')
    else:
        hero = f'<g>{voxel_hero()}</g>'
    total = f" {data['total']:,} contributions on GitHub over the last year." if data else ""

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">{escape(HANDLE)}, Minecraft server admin</title>
  <desc id="d">Human and technical management of Minecraft servers, {escape(STAT_NUMBER)} {escape(STAT_LABEL.lower())}, 11 years of experience.{total}</desc>
  <defs>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#1c2a5c" stop-opacity="0.55"/><stop offset="1" stop-color="#1c2a5c" stop-opacity="0"/></radialGradient>
    <linearGradient id="name" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#c3cbf3"/></linearGradient>
    <radialGradient id="gold-glow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{GOLD}" stop-opacity="0.20"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
    <clipPath id="pfp"><circle cx="{PH[0]}" cy="{PH[1]}" r="{PH[2]}"/></clipPath>
    <style>
      .pulse {{ transform-box: fill-box; transform-origin: center; animation: pulse 6s ease-out infinite; }}
      @keyframes pulse {{ 0% {{ transform: scale(1); opacity: 0.55; }} 65%, 100% {{ transform: scale(1.34); opacity: 0; }} }}
      .bob {{ animation: bob 6s ease-in-out infinite; }}
      @keyframes bob {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-6px); }} }}
      @media (prefers-reduced-motion: reduce) {{ .pulse, .bob {{ animation: none; }} }}
    </style>
  </defs>

  <rect width="{W}" height="{H}" rx="22" fill="{BG}"/>
  <ellipse cx="300" cy="200" rx="420" ry="260" fill="url(#glow)"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="21.5" fill="none" stroke="{BORDER}"/>

  <g font-family="{MONO}" font-size="11.5" letter-spacing="3.2" fill="{MUTED}">
    <text x="56" y="52">{escape(TOP_LEFT)}</text>
    <text x="{W-56}" y="52" text-anchor="end" fill-opacity="0.85">{escape(TOP_RIGHT)}</text>
  </g>
  <line x1="56" y1="70" x2="{W-56}" y2="70" stroke="{RULE}"/>
  {grid}

  {hero}

  <text x="56" y="126" font-family="{MONO}" font-size="12" font-weight="700" letter-spacing="3.4" fill="{GOLD}">{escape(ROLE)}</text>
  <text x="58" y="222" font-family="{SANS}" font-size="96" font-weight="800" letter-spacing="1" fill="url(#name)">{escape(HANDLE)}</text>
  <text x="56" y="272" font-family="{MONO}" font-size="19" font-weight="700" fill="{INK}">{escape(TAGLINE[0])}</text>
  <text x="56" y="298" font-family="{MONO}" font-size="19" font-weight="700" fill="{INK}">{escape(TAGLINE[1])}</text>
  <rect x="56" y="316" width="60" height="2.5" rx="1" fill="{GOLD}"/>

  <rect x="56" y="{PANEL_Y}" width="{W-112}" height="{PANEL_H}" rx="18" fill="{PANEL}" stroke="{BORDER}"/>
  <text x="84" y="{PANEL_Y+88}" font-family="{SANS}" font-size="38" font-weight="800" fill="{GOLD}">{escape(STAT_NUMBER)}</text>
  <text x="84" y="{PANEL_Y+114}" font-family="{MONO}" font-size="10.5" letter-spacing="1.8" fill="{MUTED}">{escape(STAT_LABEL)}</text>
  <line x1="344" y1="{PANEL_Y+22}" x2="344" y2="{PANEL_Y+PANEL_H-22}" stroke="{BORDER}"/>
  {heatmap(data)}

  <g font-family="{MONO}">{"".join(cols)}</g>

  <line x1="56" y1="{foot_y-30}" x2="{W-56}" y2="{foot_y-30}" stroke="{RULE}"/>
  <g font-family="{MONO}" font-size="11.5" letter-spacing="2.4">
    <text x="56" y="{foot_y}" font-weight="700" fill="{GOLD}">{escape(FOOTER[0])}</text>
    <text x="{W/2}" y="{foot_y}" text-anchor="middle" fill="{MUTED}">{escape(FOOTER[1])}</text>
    <text x="{W-56}" y="{foot_y}" text-anchor="end" fill="{MUTED}">{escape(FOOTER[2])}</text>
  </g>
</svg>
'''


def main():
    user, token = os.environ.get("GH_USER"), os.environ.get("GH_TOKEN")
    data = None
    if user and token:
        data = parse_calendar(fetch_calendar(user, token))  # fails loudly: no empty banner gets committed
        print(f"{user}: {data['total']} contributions, streak {data['streak']}, record {data['record']}")
    else:
        print("GH_USER / GH_TOKEN not set: rendering the empty state", file=sys.stderr)
    out = ROOT / "assets" / "banner.svg"
    out.write_text(render(data), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

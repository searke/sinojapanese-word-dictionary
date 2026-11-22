"""Skeleton maps of the kanji web, drawn as static SVG at build time.

1. Neighbourhood skeleton: one node per neighbourhood. Links are the number of
   words crossing between two neighbourhoods, thinned to a "skeleton": the
   maximum spanning tree plus each neighbourhood's two strongest links.
2. Hub map: the three best-connected kanji of every neighbourhood, placed around
   their neighbourhood's spot on map 1, with every word among them drawn as a line.
"""
import html
import math
from collections import Counter

import networkx as nx

W, H = 1000, 1000
PAD = 90


def esc(s):
    return html.escape(str(s))


def hood_graph(G, words):
    hood = {c: v["hood"] for c, v in G["kanji"].items()}
    cross = Counter()
    for w in words:
        a, b = w["w"]
        if a in hood and b in hood and hood[a] != hood[b]:
            cross[tuple(sorted((hood[a], hood[b])))] += 1
    HG = nx.Graph()
    for h in G["neighbourhoods"]:
        HG.add_node(h["id"])
    for (a, b), n in cross.items():
        HG.add_edge(a, b, weight=n)
    return HG


def skeleton(HG, per_node=2):
    S = nx.maximum_spanning_tree(HG, weight="weight")
    for n in HG:
        best = sorted(HG[n].items(), key=lambda t: -t[1]["weight"])[:per_node]
        for m, d in best:
            S.add_edge(n, m, weight=d["weight"])
    return S


def fit(pos, pad=PAD):
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    sx = (W - 2 * pad) / ((max(xs) - min(xs)) or 1)
    sy = (H - 2 * pad) / ((max(ys) - min(ys)) or 1)
    return {n: (pad + (p[0] - min(xs)) * sx, pad + (p[1] - min(ys)) * sy) for n, p in pos.items()}


def spread(pos, radius, rounds=200):
    """Push apart nodes that overlap (simple pairwise repulsion)."""
    pos = {n: list(p) for n, p in pos.items()}
    nodes = list(pos)
    for _ in range(rounds):
        moved = False
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                need = radius[a] + radius[b] + 14
                dx, dy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]
                d = math.hypot(dx, dy) or 0.01
                if d < need:
                    push = (need - d) / 2
                    ux, uy = dx / d, dy / d
                    pos[a][0] -= ux * push; pos[a][1] -= uy * push
                    pos[b][0] += ux * push; pos[b][1] += uy * push
                    moved = True
        for n in nodes:
            pos[n][0] = min(max(pos[n][0], radius[n] + 10), W - radius[n] - 10)
            pos[n][1] = min(max(pos[n][1], radius[n] + 10), H - radius[n] - 30)
        if not moved:
            break
    return {n: tuple(p) for n, p in pos.items()}


def spread_boxes(pos, boxes, rounds=400):
    """Push apart labelled nodes. boxes[n] = (half_width, top, bottom) around the node centre."""
    pos = {n: list(p) for n, p in pos.items()}
    nodes = list(pos)
    for _ in range(rounds):
        moved = False
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                (wa, ta, ba), (wb, tb, bb) = boxes[a], boxes[b]
                ax0, ax1 = pos[a][0] - wa, pos[a][0] + wa
                bx0, bx1 = pos[b][0] - wb, pos[b][0] + wb
                ay0, ay1 = pos[a][1] - ta, pos[a][1] + ba
                by0, by1 = pos[b][1] - tb, pos[b][1] + bb
                ox = min(ax1, bx1) - max(ax0, bx0) + 8
                oy = min(ay1, by1) - max(ay0, by0) + 8
                if ox > 0 and oy > 0:
                    moved = True
                    if ox < oy:
                        d = ox / 2 * (1 if pos[b][0] >= pos[a][0] else -1)
                        pos[a][0] -= d; pos[b][0] += d
                    else:
                        d = oy / 2 * (1 if pos[b][1] >= pos[a][1] else -1)
                        pos[a][1] -= d; pos[b][1] += d
        for n in nodes:
            w, t, b = boxes[n]
            pos[n][0] = min(max(pos[n][0], w + 6), W - w - 6)
            pos[n][1] = min(max(pos[n][1], t + 6), H - b - 6)
        if not moved:
            break
    return {n: tuple(p) for n, p in pos.items()}


def hood_map(G, words):
    """Return (svg, skeleton edges as (a, b, n), positions)."""
    HG = hood_graph(G, words)
    S = skeleton(HG)
    hoods = {h["id"]: h for h in G["neighbourhoods"]}
    pos = fit(nx.kamada_kawai_layout(S, weight=None))
    size = {n: len(hoods[n]["kanji"]) for n in hoods}
    rad = {n: 22 + 26 * math.sqrt(size[n] / max(size.values())) for n in hoods}
    boxes = {n: (max(rad[n], len(hoods[n]["name"]) * 5.6), rad[n], rad[n] + 30) for n in hoods}
    pos = spread_boxes(pos, boxes)
    maxw = max(d["weight"] for _, _, d in S.edges(data=True))

    out = [f'<svg class="map" viewBox="0 0 {W} {H}" role="img" '
           'aria-label="Skeleton of the kanji neighbourhoods">']
    for a, b, d in sorted(S.edges(data=True), key=lambda e: e[2]["weight"]):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        sw = 1.5 + 9 * d["weight"] / maxw
        out.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                   f'class="edge" stroke-width="{sw:.1f}"><title>{esc(hoods[a]["name"])} ↔ '
                   f'{esc(hoods[b]["name"])}: {d["weight"]} words</title></line>')
    for n, (x, y) in pos.items():
        h = hoods[n]
        r = rad[n]
        out.append(f'<a href="n/{n}.html"><g class="hnode"><title>{esc(h["name"])} · '
                   f'{size[n]} kanji</title>'
                   f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}"/>'
                   f'<text x="{x:.0f}" y="{y + r * 0.36:.0f}" class="hk" font-size="{r * 1.05:.0f}">'
                   f'{esc(h["hub"])}</text>'
                   f'<text x="{x:.0f}" y="{y + r + 22:.0f}" class="hl">{esc(h["name"])}</text></g></a>')
    out.append("</svg>")
    edges = sorted(((hoods[a]["name"], hoods[b]["name"], d["weight"]) for a, b, d in S.edges(data=True)),
                   key=lambda t: -t[2])
    return "".join(out), edges, pos


def hub_map(G, words, kinfo, hood_pos, per_hood=3):
    hoods = G["neighbourhoods"]
    hubs, pos = [], {}
    for h in hoods:
        cx, cy = hood_pos[h["id"]]
        top = h["kanji"][:per_hood]
        for i, c in enumerate(top):
            ang = -math.pi / 2 + 2 * math.pi * i / len(top)
            pos[c] = (cx + 30 * math.cos(ang), cy + 30 * math.sin(ang))
            hubs.append(c)
    rad = {c: 17 for c in hubs}
    pos = spread(pos, rad)
    hs = set(hubs)
    links = {}
    for w in words:
        a, b = w["w"]
        if a != b and a in hs and b in hs:
            links.setdefault(frozenset((a, b)), []).append(w["w"])
    hood_of = {c: G["kanji"][c]["hood"] for c in hubs}

    out = [f'<svg class="map" viewBox="0 0 {W} {H}" role="img" '
           'aria-label="The three main kanji of each neighbourhood and the words linking them">']
    for pair, ws in links.items():
        a, b = tuple(pair)
        (x1, y1), (x2, y2) = pos[a], pos[b]
        cls = "edge in" if hood_of[a] == hood_of[b] else "edge out"
        out.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" class="{cls}">'
                   f'<title>{esc("、".join(ws))}</title></line>')
    for c in hubs:
        x, y = pos[c]
        lv = kinfo[c]["lvl"]
        h = hoods[hood_of[c] - 1]
        out.append(f'<a href="k/{ord(c):x}.html"><g class="knode lv{lv}"><title>{esc(c)} · '
                   f'{esc(", ".join(kinfo[c]["meanings"][:3]))} · {esc(h["name"])}</title>'
                   f'<circle cx="{x:.0f}" cy="{y:.0f}" r="17"/>'
                   f'<text x="{x:.0f}" y="{y + 7:.0f}" class="hk" font-size="20">{esc(c)}</text></g></a>')
    out.append("</svg>")
    return "".join(out), len(links)


MAP_CSS = """
.mapwrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
.map{width:100%;min-width:640px;height:auto;display:block;background:var(--card);border:1px solid var(--line);
border-radius:12px;margin:12px 0}
.map .edge{stroke:var(--muted);stroke-opacity:.45;stroke-linecap:round}
.map .edge.in{stroke:var(--accent);stroke-opacity:.6;stroke-width:2}
.map .edge.out{stroke-width:1;stroke-opacity:.25}
.map .edge:hover{stroke:var(--accent);stroke-opacity:1}
.map .hnode circle{fill:var(--bg);stroke:var(--accent);stroke-width:2.5}
.map .knode circle{fill:var(--bg);stroke:var(--lc);stroke-width:3}
.map a:hover circle{fill:var(--hl)}
.map .hk{text-anchor:middle;fill:var(--fg);font-family:"Hiragino Mincho ProN","Noto Serif JP",serif}
.map .hl{text-anchor:middle;fill:var(--muted);font-size:19px;font-weight:600;
paint-order:stroke;stroke:var(--card);stroke-width:5px;stroke-linejoin:round}
table.links{border-collapse:collapse;font-size:14px;width:100%}
table.links td{border-top:1px solid var(--line);padding:4px 6px}
table.links td:last-child{text-align:right;font-variant-numeric:tabular-nums}
"""


def map_body(G, words, kinfo, legend_html):
    svg1, edges, hpos = hood_map(G, words)
    svg2, nlinks = hub_map(G, words, kinfo, hpos)
    rows = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{n}</td></tr>" for a, b, n in edges)
    return f"""<h1>Map of the web</h1>
<p class="muted">Two skeleton views of how the kanji fit together. Tap any circle to open it. On a phone, swipe sideways to see the whole map.</p>
<h2>Neighbourhood skeleton</h2>
<p class="muted">Each circle is a neighbourhood, sized by how many kanji it holds, labelled with its
hub kanji. Lines are the words that cross between two neighbourhoods; thicker means more words.
Only the strongest links are drawn: enough to keep every neighbourhood connected, plus each one's
two busiest links.</p>
<div class="mapwrap">{svg1}</div>
<details class="how"><summary>The links as a table</summary>
<table class="links"><tr><td><b>From</b></td><td><b>To</b></td><td><b>Words</b></td></tr>{rows}</table>
</details>
<h2 style="margin-top:36px">Hub map</h2>
<p class="muted">The three best-connected kanji of each neighbourhood, placed where their neighbourhood
sits above. Every line is a real word ({nlinks} in all). Red lines stay inside a neighbourhood; grey
lines cross between them. The ring colour is the kanji's difficulty level.</p>
{legend_html}
<div class="mapwrap">{svg2}</div>"""

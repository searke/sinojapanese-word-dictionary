#!/usr/bin/env python3
"""Build the Sino-Japanese word explorer as a static site in docs/.

Data: JMdict (common words) + KANJIDIC2, via jmdict-simplified.
Run scripts/fetch_data.sh first.

A word is kept when it is written with exactly two kanji and its reading
can be split into an on'yomi of the first kanji + an on'yomi of the
second (allowing the usual sound changes: っ gemination, rendaku, p-sounds).
That split is what lets each kanji page group words by on'yomi.
"""
import html
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs"

# ---------------------------------------------------------------- kana utils

def kata2hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)

VOICE = dict(zip("かきくけこさしすせそたちつてとはひふへほ",
                 "がぎぐげござじずぜぞだぢづでどばびぶべぼ"))
SEMI = dict(zip("はひふへほ", "ぱぴぷぺぽ"))


def first_variants(on: str) -> set[str]:
    """Forms an on'yomi can take as the FIRST element of a compound."""
    out = {on}
    if len(on) >= 2 and on[-1] in "つちくき":
        out.add(on[:-1] + "っ")          # 学校 がっこう, 一緒 いっしょ
    return out


def second_variants(on: str) -> set[str]:
    """Forms an on'yomi can take as the SECOND element of a compound."""
    out = {on}
    h = on[0]
    if h in VOICE:
        out.add(VOICE[h] + on[1:])        # 本棚-type rendaku, 三階 さんがい
    if h in SEMI:
        out.add(SEMI[h] + on[1:])         # 発表 はっぴょう, 散歩 さんぽ
    if on[-1] in "つちくき" and len(on) >= 2:
        out.add(on[:-1] + "っ")           # rare, harmless
    return out


ROWS = [("あ", "あいうえお"), ("か", "かきくけこがぎぐげご"),
        ("さ", "さしすせそざじずぜぞ"), ("た", "たちつてとだぢづでど"),
        ("な", "なにぬねの"), ("は", "はひふへほばびぶべぼぱぴぷぺぽ"),
        ("ま", "まみむめも"), ("や", "やゆよ"), ("ら", "らりるれろ"), ("わ", "わを")]


def row_of(kana: str) -> str:
    for head, members in ROWS:
        if kana[0] in members:
            return head
    return "ん"


def kana_key(s: str):
    """Gojūon sort key: base sound first, voicing as tie-breaker."""
    base = {v: k for k, v in VOICE.items()} | {v: k for k, v in SEMI.items()}
    return ("".join(base.get(c, c) for c in s), s)


def is_kanji(c: str) -> bool:
    return "一" <= c <= "鿿" or "㐀" <= c <= "䶿"

# ---------------------------------------------------------------- load data

def load_kanji():
    kd = json.loads((DATA / "kanjidic.json").read_text("utf-8"))
    info = {}
    for ch in kd["characters"]:
        rm = ch.get("readingMeaning") or {}
        on, kun, meanings = [], [], []
        for g in rm.get("groups", []):
            for r in g["readings"]:
                if r["type"] == "ja_on":
                    v = kata2hira(r["value"])
                    if v not in on:
                        on.append(v)
                elif r["type"] == "ja_kun":
                    kun.append(r["value"])
            meanings += [m["value"] for m in g["meanings"] if m["lang"] == "en"]
        if on:
            info[ch["literal"]] = {
                "on": on, "kun": kun, "meanings": meanings,
                "grade": ch["misc"].get("grade"),
                "freq": ch["misc"].get("frequency"),
                "strokes": (ch["misc"].get("strokeCounts") or [None])[0],
                "jlpt": ch["misc"].get("jlptLevel"),
            }
    return info


def split_reading(word, reading, kinfo):
    """Return (on1, on2, surface1, surface2) if reading = on(word[0]) + on(word[1])."""
    a, b = word
    for on1 in kinfo[a]["on"]:
        for s1 in first_variants(on1):
            if not reading.startswith(s1):
                continue
            rest = reading[len(s1):]
            for on2 in kinfo[b]["on"]:
                if rest in second_variants(on2):
                    return on1, on2, s1, rest
    return None


def load_words(kinfo):
    jm = json.loads((DATA / "jmdict.json").read_text("utf-8"))
    words, seen = [], set()
    for entry in jm["words"]:
        for i, k in enumerate(entry["kanji"]):
            w = k["text"]
            # keep the main spelling and common variants; skip rare/old ones
            if i > 0 and not k["common"]:
                continue
            if len(w) != 2 or not all(is_kanji(c) and c in kinfo for c in w):
                continue
            if w in seen or set(k["tags"]) & {"iK", "oK", "rK", "sK", "ateji"}:
                continue
            readings = [r for r in entry["kana"]
                        if "*" in r["appliesToKanji"] or w in r["appliesToKanji"]]
            for r in readings:
                rd = kata2hira(r["text"])
                sp = split_reading(w, rd, kinfo)
                if sp:
                    break
            else:
                continue
            senses = [s for s in entry["sense"]
                      if "*" in s["appliesToKanji"] or w in s["appliesToKanji"]]
            glosses = []
            for s in senses:
                for g in s["gloss"]:
                    if g["text"] not in glosses:
                        glosses.append(g["text"])
            seen.add(w)
            words.append({
                "w": w, "r": rd, "on": sp[:2], "parts": sp[2:],
                "common": k["common"], "gloss": glosses[:4],
            })
    return words

# ---------------------------------------------------------------- html

CSS = """
:root{--bg:#fbf8f3;--fg:#24211d;--muted:#7a7268;--line:#e6dfd4;--accent:#b23a2b;
--card:#fff;--hl:#f6e3c8}
@media (prefers-color-scheme:dark){:root{--bg:#1b1916;--fg:#ece6dc;--muted:#a39a8d;
--line:#36312a;--accent:#ff8a6e;--card:#24211d;--hl:#4a3a24}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.6 system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}
a{color:inherit;text-decoration:none}
main{max-width:900px;margin:0 auto;padding:24px 16px 64px}
header.site{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:24px}
header.site a{font-weight:600}
.muted{color:var(--muted)}
h1,h2,h3{line-height:1.25}
.hero{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.big{font-size:120px;line-height:1;font-family:"Hiragino Mincho ProN","Noto Serif JP",serif}
.meta dt{color:var(--muted);font-size:13px}
.meta dd{margin:0 0 6px}
.on-tag{display:inline-block;padding:1px 10px;border-radius:99px;background:var(--hl);
margin:2px 4px 2px 0;font-weight:600}
section.on{margin-top:32px}
section.on h2{font-size:22px;border-bottom:2px solid var(--accent);display:inline-block;
padding-bottom:2px;margin-bottom:4px}
h3{font-size:14px;color:var(--muted);font-weight:500;margin:16px 0 6px}
ul.words{list-style:none;padding:0;margin:0;display:grid;
grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
ul.words li{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.w{font-size:26px;font-family:"Hiragino Mincho ProN","Noto Serif JP",serif;letter-spacing:2px}
.w a{border-bottom:2px solid transparent}
.w a:hover{border-color:var(--accent);color:var(--accent)}
.w .self{color:var(--accent)}
.r{font-size:14px}.r b{color:var(--accent);font-weight:600}
.g{font-size:13px;color:var(--muted)}
.row{margin-top:28px}
.row h2{font-size:28px;margin:0 0 8px;color:var(--accent)}
.reading{display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-top:1px solid var(--line)}
.reading .rk{width:72px;flex:none;font-weight:600;padding-top:6px}
.kl{display:flex;flex-wrap:wrap;gap:4px}
.kl a{display:inline-flex;flex-direction:column;align-items:center;min-width:46px;
padding:4px 6px;border-radius:8px;background:var(--card);border:1px solid var(--line)}
.kl a:hover{border-color:var(--accent)}
.kl a span{font-size:24px;font-family:"Hiragino Mincho ProN","Noto Serif JP",serif;line-height:1.2}
.kl a small{font-size:10px;color:var(--muted)}
nav.rows{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}
nav.rows a{padding:2px 10px;border:1px solid var(--line);border-radius:99px}
input#q{width:100%;font-size:18px;padding:10px 12px;border-radius:10px;border:1px solid var(--line);
background:var(--card);color:var(--fg)}
.hidden{display:none!important}
"""


def esc(s):
    return html.escape(str(s))


def kpath(c):
    return f"{ord(c):x}.html"


def page(title, body, depth):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><link rel="stylesheet" href="{up}style.css"></head>
<body><main>
<header class="site"><a href="{up}index.html">漢語 · Sino-Japanese explorer</a>
<span class="muted">音読み index</span></header>
{body}
<footer class="muted" style="margin-top:48px;font-size:12px">
Data: <a href="https://www.edrdg.org/jmdict/j_jmdict.html">JMdict</a> &amp;
<a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project">KANJIDIC2</a>
(EDRDG, CC BY-SA 4.0) via jmdict-simplified.</footer>
</main></body></html>"""


def word_li(word, key, pages, depth_prefix=""):
    chars = []
    for c in word["w"]:
        if c == key:
            chars.append(f'<span class="self">{esc(c)}</span>')
        elif c in pages:
            chars.append(f'<a href="{depth_prefix}{kpath(c)}">{esc(c)}</a>')
        else:
            chars.append(esc(c))
    p1, p2 = word["parts"]
    if word["w"][0] == key:
        rd = f"<b>{esc(p1)}</b>{esc(p2)}"
    else:
        rd = f"{esc(p1)}<b>{esc(p2)}</b>"
    if word["w"][0] == key and word["w"][1] == key:
        rd = f"<b>{esc(p1)}{esc(p2)}</b>"
    gloss = "; ".join(word["gloss"])
    return (f'<li><div class="w">{"".join(chars)}</div>'
            f'<div class="r">{rd}</div><div class="g">{esc(gloss)}</div></li>')


def build():
    kinfo = load_kanji()
    words = load_words(kinfo)

    # index words by kanji and by which on'yomi that kanji uses in the word
    by_kanji = defaultdict(lambda: defaultdict(lambda: {"first": [], "second": []}))
    for w in words:
        a, b = w["w"]
        by_kanji[a][w["on"][0]]["first"].append(w)
        by_kanji[b][w["on"][1]]["second"].append(w)
    pages = set(by_kanji)

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "k").mkdir(parents=True)
    (OUT / "style.css").write_text(CSS, "utf-8")
    (OUT / ".nojekyll").write_text("", "utf-8")

    for c, groups in by_kanji.items():
        info = kinfo[c]
        order = [o for o in info["on"] if o in groups]  # KANJIDIC order
        total = sum(len(g["first"]) + len(g["second"]) for g in groups.values())
        on_tags = "".join(
            f'<a class="on-tag" href="#on-{esc(o)}">{esc(o)}</a>' for o in order)
        unused = [o for o in info["on"] if o not in groups]
        meta = [f"<dt>On'yomi used here</dt><dd>{on_tags}</dd>"]
        if unused:
            meta.append(f"<dt>Other on'yomi</dt><dd>{esc('、'.join(unused))}</dd>")
        if info["kun"]:
            meta.append(f"<dt>Kun'yomi</dt><dd>{esc('、'.join(info['kun'][:8]))}</dd>")
        bits = []
        if info["grade"]:
            bits.append(f"grade {info['grade']}")
        if info["jlpt"]:
            bits.append(f"old JLPT {info['jlpt']}")
        if info["strokes"]:
            bits.append(f"{info['strokes']} strokes")
        bits.append(f"{total} words")
        body = [f'<div class="hero"><div class="big">{esc(c)}</div><div>'
                f'<h1 style="margin:0">{esc(", ".join(info["meanings"][:5]))}</h1>'
                f'<p class="muted" style="margin:4px 0 8px">{esc(" · ".join(bits))}</p>'
                f'<dl class="meta">{"".join(meta)}</dl></div></div>']
        for o in order:
            g = groups[o]
            body.append(f'<section class="on" id="on-{esc(o)}"><h2>{esc(c)} 〔{esc(o)}〕</h2>')
            for pos, label in (("first", f"{c}〇 — {c} first"), ("second", f"〇{c} — {c} second")):
                lst = sorted(g[pos], key=lambda w: (not w["common"], kana_key(w["r"])))
                if not lst:
                    continue
                body.append(f"<h3>{esc(label)} ({len(lst)})</h3><ul class='words'>")
                body += [word_li(w, c, pages) for w in lst]
                body.append("</ul>")
            body.append("</section>")
        (OUT / "k" / kpath(c)).write_text(
            page(f"{c} — Sino-Japanese words", "\n".join(body), 1), "utf-8")

    # ---- index: every on'yomi (gojūon order), with the kanji that use it
    by_on = defaultdict(list)
    for c, groups in by_kanji.items():
        for o, g in groups.items():
            by_on[o].append((c, len(g["first"]) + len(g["second"])))
    rows = defaultdict(list)
    for o in sorted(by_on, key=kana_key):
        rows[row_of(o)].append(o)
    nav = "".join(f'<a href="#row-{h}">{h}</a>' for h, _ in ROWS if h in rows)
    body = [
        "<h1>漢語の森 — explore Sino-Japanese words</h1>",
        f"<p class='muted'>{len(pages)} kanji · {len(words)} two-kanji words read with on'yomi. "
        "Pick a kanji to see every compound it forms, grouped by the on'yomi it uses there. "
        "Every kanji inside a word is a link, so you can keep wandering.</p>",
        '<input id="q" placeholder="Filter: type a reading (かん / カン) or a kanji…" autocomplete="off">',
        f'<nav class="rows">{nav}</nav>',
    ]
    for h, _ in ROWS:
        if h not in rows:
            continue
        body.append(f'<div class="row" id="row-{h}"><h2>{h}</h2>')
        for o in rows[h]:
            ks = sorted(by_on[o], key=lambda t: (-t[1], t[0]))
            links = "".join(
                f'<a href="k/{kpath(c)}" data-k="{esc(c)}" title="{esc(", ".join(kinfo[c]["meanings"][:3]))}">'
                f'<span>{esc(c)}</span><small>{n}</small></a>' for c, n in ks)
            body.append(f'<div class="reading" data-on="{esc(o)}"><div class="rk">{esc(o)}</div>'
                        f'<div class="kl">{links}</div></div>')
        body.append("</div>")
    body.append("""<script>
const q=document.getElementById('q');
const k2h=s=>s.replace(/[\\u30a1-\\u30f6]/g,c=>String.fromCharCode(c.charCodeAt(0)-0x60));
q.addEventListener('input',()=>{const v=k2h(q.value.trim());
document.querySelectorAll('.reading').forEach(r=>{
 const hitOn=!v||r.dataset.on.startsWith(v);
 let any=false;r.querySelectorAll('a').forEach(a=>{
  const show=hitOn||a.dataset.k===v;a.classList.toggle('hidden',!show);any=any||show});
 r.classList.toggle('hidden',!any)});
document.querySelectorAll('.row').forEach(row=>row.classList.toggle('hidden',
 !row.querySelector('.reading:not(.hidden)')));});
</script>""")
    (OUT / "index.html").write_text(page("漢語の森 — Sino-Japanese explorer", "\n".join(body), 0), "utf-8")
    print(f"built {len(pages)} kanji pages, {len(words)} words → {OUT}")


if __name__ == "__main__":
    build()

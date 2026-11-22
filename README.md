# 漢語の森 — Sino-Japanese word explorer

A static website for exploring Sino-Japanese (漢語) vocabulary, one kanji at a time.

- **Index** (`docs/index.html`): every on'yomi in gojūon order (あ・か・さ…), each listing the kanji
  that use that reading. A filter box narrows by reading (かん / カン) or kanji.
- **Kanji pages** (`docs/k/<codepoint>.html`): all two-kanji words containing that kanji,
  grouped by the on'yomi the kanji takes in each word, then split into "kanji first" / "kanji second".
  Every other kanji in a word links to its own page, so you can wander from word to word.

- **Neighbourhoods** (`docs/neighbourhoods.html`, `docs/n/<id>.html`): treat kanji as nodes and words
  as links, and the web splits into 27 groups that make lots of words with each other (Louvain
  community detection, names hand-picked in `scripts/graph.py`). Also lists the 37 "island" pairs
  like 挨拶 and 珊瑚 that only make words with each other.
- **Core 257** (`docs/core.html`): the densest part of the web (maximum k-core), where each kanji
  links to at least 10 others in the group.
- **Graph data** (`docs/graph.json`): every kanji's neighbourhood and centrality scores (degree,
  betweenness, eigenvector, closeness). `python3 scripts/graph.py` prints a summary.

Only words whose reading splits cleanly into *on'yomi + on'yomi* are included (allowing っ gemination,
rendaku and p-sounds, e.g. 学校 がっ+こう, 発表 はっ+ぴょう). Kun'yomi words like 手紙 are left out.

## Build

```sh
scripts/fetch_data.sh      # downloads JMdict (common words) + KANJIDIC2 into data/
python3 scripts/build.py   # writes the site into docs/
```

Needs Python 3 and `networkx` (`pip install -r requirements.txt`). To publish it, turn on GitHub Pages for the `docs/` folder.

## Data & license

Dictionary data comes from [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) and
[KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project) by the Electronic Dictionary
Research and Development Group, used under CC BY-SA 4.0, through the JSON builds from
[jmdict-simplified](https://github.com/scriptin/jmdict-simplified).

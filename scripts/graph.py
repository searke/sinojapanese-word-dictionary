"""The kanji graph: kanji are nodes, each two-kanji word is a link between them.

Used by build.py for the neighbourhood and core pages. Run it directly
(python3 scripts/graph.py) to print summary statistics.
"""
from collections import Counter

import networkx as nx

# Louvain community detection. The resolution sets how fine-grained the
# neighbourhoods are: 1.5 gives roughly 27 groups of 30-150 kanji.
RESOLUTION = 1.5
SEED = 42

# Hand-picked names, keyed by each neighbourhood's hub (its best-connected
# kanji). A neighbourhood whose hub isn't listed is just named after the hub.
THEMES = {
    "一": "Time & numbers",
    "水": "Force & energy",
    "文": "Writing & form",
    "発": "Action & conflict",
    "国": "Nation & society",
    "定": "Judgement & decisions",
    "作": "Making things",
    "人": "People & roles",
    "会": "Meetings & public life",
    "下": "Places & directions",
    "石": "Earth & matter",
    "大": "Mountains, metals & creatures",
    "外": "Duties & relations",
    "金": "Money & help",
    "行": "Conduct & ceremony",
    "心": "Body & hardship",
    "養": "Living & growing",
    "意": "Feelings & will",
    "子": "Family & rank",
    "連": "Fortune & wishes",
    "賞": "Giving & receiving",
    "成": "Structure & order",
    "問": "Questions & investigation",
    "室": "Rooms & company",
    "天": "Sky, weather & purity",
    "左": "Sides & vehicles",
    "長": "Length & endurance",
}


def build_graph(words):
    G = nx.Graph()
    for w in words:
        a, b = w["w"]
        if a != b:
            G.add_edge(a, b)
    return G


def analyse(words):
    """Return per-kanji stats, neighbourhoods, islands and summary numbers."""
    G = build_graph(words)
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    H = G.subgraph(comps[0]).copy()

    comms = nx.community.louvain_communities(H, resolution=RESOLUTION, seed=SEED)
    comms = sorted(comms, key=len, reverse=True)

    betw = nx.betweenness_centrality(H)
    eig = nx.eigenvector_centrality(H, max_iter=1000)
    close = nx.closeness_centrality(H)
    core = nx.core_number(H)
    kmax = max(core.values())

    hoods = []
    node = {}
    for i, members in enumerate(comms):
        sub = H.subgraph(members)
        ranked = sorted(members, key=lambda c: (-sub.degree(c), -H.degree(c), c))
        hub = ranked[0]
        hoods.append({"id": i + 1, "hub": hub, "name": THEMES.get(hub, f"{hub} neighbourhood"),
                      "kanji": ranked})
        for c in members:
            node[c] = {"hood": i + 1, "degree": H.degree(c), "inner_degree": sub.degree(c),
                       "betweenness": round(betw[c], 5), "eigenvector": round(eig[c], 5),
                       "closeness": round(close[c], 5), "core": core[c] == kmax}

    # links between neighbourhoods (how many words cross each border)
    cross = Counter()
    for a, b in H.edges():
        ha, hb = node[a]["hood"], node[b]["hood"]
        if ha != hb:
            cross[(ha, hb)] += 1
            cross[(hb, ha)] += 1
    for h in hoods:
        nbrs = [(o, n) for (s, o), n in cross.items() if s == h["id"]]
        h["neighbours"] = [o for o, _ in sorted(nbrs, key=lambda t: -t[1])[:5]]

    islands = [sorted(c) for c in comps[1:]]
    summary = {
        "kanji": G.number_of_nodes(), "links": G.number_of_edges(),
        "giant": H.number_of_nodes(), "islands": len(islands),
        "avg_path": round(nx.average_shortest_path_length(H), 2),
        "diameter": nx.diameter(H),
        "clustering": round(nx.average_clustering(H), 3),
        "core_k": kmax, "core_size": sum(v == kmax for v in core.values()),
        "neighbourhoods": len(hoods),
    }
    return {"summary": summary, "kanji": node, "neighbourhoods": hoods, "islands": islands}


if __name__ == "__main__":
    import build
    k = build.load_kanji()
    g = analyse(build.load_words(k))
    for key, v in g["summary"].items():
        print(f"{key:>15}: {v}")
    top = lambda m: "".join(sorted(g["kanji"], key=lambda c: -g["kanji"][c][m])[:15])
    for m in ("degree", "betweenness", "eigenvector", "closeness"):
        print(f"{m:>15}: {top(m)}")
    for h in g["neighbourhoods"]:
        print(f'{h["id"]:>3} {h["name"]:<30} {len(h["kanji"]):>4} {"".join(h["kanji"][:20])}')
    print("islands:", " ".join("".join(i) for i in g["islands"]))

"""
career_graph.py — Generate a nodal relationship graph of careers from final_data.json.

Produces a dark-background network visualization where:
  - Each node is a career
  - Edges connect related careers (same O*NET group, related fields)
  - Node colors represent major career families
  - Hub nodes (major groups) are larger
  - Layout mimics a radial / force-directed style

Usage:
    python career_graph.py                        # Default: 400 nodes, PNG output
    python career_graph.py --nodes 600            # More nodes
    python career_graph.py --output graph.pdf     # PDF output
    python career_graph.py --interactive          # Opens matplotlib window
"""

import argparse
import json
import math
import random
from collections import defaultdict
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")  # headless by default
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# ── Configuration ──────────────────────────────────────────────
INPUT_FILE = "../Data Management/final_data.json"
DEFAULT_MAX_NODES = 400
DEFAULT_OUTPUT = "career_graph.png"
DPI = 200
FIG_SIZE = (20, 20)
SEED = 42

# O*NET 2-digit major group labels and colors
MAJOR_GROUPS: Dict[str, Tuple[str, str]] = {
    "11": ("Management",               "#6C8EBF"),   # blue
    "13": ("Business & Finance",        "#82B366"),   # green
    "15": ("Computer & Math",           "#D6A4E0"),   # lavender
    "17": ("Architecture & Engineering","#F0C040"),   # yellow
    "19": ("Life & Physical Science",   "#D4E157"),   # lime
    "21": ("Community & Social Service","#FF8A80"),   # coral
    "23": ("Legal",                     "#FFD54F"),   # gold
    "25": ("Education & Training",      "#4FC3F7"),   # sky blue
    "27": ("Arts, Design & Media",      "#F48FB1"),   # pink
    "29": ("Healthcare Practitioners",  "#EF5350"),   # red
    "31": ("Healthcare Support",        "#CE93D8"),   # purple
    "33": ("Protective Service",        "#A1887F"),   # brown
    "35": ("Food Preparation",          "#FFB74D"),   # orange
    "37": ("Building & Grounds",        "#AED581"),   # light green
    "39": ("Personal Care & Service",   "#F06292"),   # hot pink
    "41": ("Sales",                     "#4DB6AC"),   # teal
    "43": ("Office & Admin Support",    "#9E9E9E"),   # gray
    "45": ("Farming, Fishing, Forestry","#8BC34A"),   # green
    "47": ("Construction & Extraction", "#FF7043"),   # deep orange
    "49": ("Installation & Maintenance","#78909C"),   # blue gray
    "51": ("Production",                "#B0BEC5"),   # silver
    "53": ("Transportation",            "#7986CB"),   # indigo
    "55": ("Military",                  "#546E7A"),   # dark teal
}

# Which major groups are closely related (inter-group edges)
RELATED_GROUPS = [
    # Business cluster
    ("11", "13"), ("11", "23"), ("11", "41"), ("13", "41"), ("13", "43"),
    # Tech cluster
    ("15", "17"), ("15", "19"), ("15", "27"),
    # Science-Healthcare cluster
    ("19", "29"), ("19", "17"), ("29", "31"), ("31", "39"),
    # Education-Social cluster
    ("25", "21"), ("21", "39"), ("25", "27"),
    # Trades cluster
    ("17", "47"), ("47", "49"), ("49", "51"), ("37", "47"),
    # Service cluster
    ("35", "39"), ("33", "55"), ("39", "41"),
    # Transport-Production cluster
    ("51", "53"), ("53", "49"), ("45", "19"), ("45", "37"),
    # Cross-cluster bridges
    ("11", "15"), ("11", "29"), ("13", "15"), ("13", "23"),
    ("17", "51"), ("25", "29"), ("27", "41"), ("33", "21"),
    ("43", "41"), ("43", "11"),
]


def load_careers(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_major_group(career_id: str) -> str:
    """Extract the 2-digit O*NET major group from an id like career-29-1141-00."""
    parts = career_id.split("-")
    if len(parts) >= 2 and parts[1].isdigit():
        return parts[1]
    return ""


def parse_minor_group(career_id: str) -> str:
    """Extract the 4-digit minor group, e.g. '1141' from career-29-1141-00."""
    parts = career_id.split("-")
    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
        return parts[1] + parts[2]
    return ""


def select_careers(all_careers: List[dict], max_nodes: int) -> List[dict]:
    """
    Select a balanced sample across major groups.
    Prioritize real O*NET careers, then BLS, then a few alternates.
    """
    onet = [c for c in all_careers if not c["id"].startswith("career-alt") and not c["id"].startswith("career-bls")]
    bls  = [c for c in all_careers if c["id"].startswith("career-bls")]
    alt  = [c for c in all_careers if c["id"].startswith("career-alt")]

    # Take all O*NET first (usually ~1016), then BLS, then fill with alts
    selected = onet + bls
    if len(selected) < max_nodes:
        random.seed(SEED)
        random.shuffle(alt)
        selected += alt[: max_nodes - len(selected)]
    else:
        # Sample evenly across major groups
        by_group = defaultdict(list)
        for c in selected:
            mg = parse_major_group(c["id"])
            by_group[mg].append(c)

        per_group = max(1, max_nodes // max(len(by_group), 1))
        sampled = []
        for mg in sorted(by_group):
            group_careers = by_group[mg]
            random.seed(SEED + hash(mg))
            random.shuffle(group_careers)
            sampled.extend(group_careers[:per_group])

        # Top up if under budget
        remaining = [c for c in selected if c not in sampled]
        random.seed(SEED)
        random.shuffle(remaining)
        sampled += remaining[: max_nodes - len(sampled)]
        selected = sampled[:max_nodes]

    return selected


def build_graph(careers: List[dict]) -> nx.Graph:
    """Build a networkx graph with intra-group and inter-group edges."""
    G = nx.Graph()

    # Index by groups
    by_major = defaultdict(list)
    by_minor = defaultdict(list)

    for c in careers:
        cid = c["id"]
        mg = parse_major_group(cid)
        mn = parse_minor_group(cid)
        label = c["title"][:30]
        color = MAJOR_GROUPS.get(mg, ("Other", "#888888"))[1]

        G.add_node(cid, label=label, major=mg, minor=mn, color=color)
        if mg:
            by_major[mg].append(cid)
        if mn:
            by_minor[mn].append(cid)

    # ── Layer 1: Intra-minor-group edges (same detailed specialty) ──
    # These are the tightest connections — all nodes in the same minor group
    for mn, members in by_minor.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):   # full mesh within minor group
                G.add_edge(members[i], members[j], weight=3.0, etype="minor")

    # ── Layer 2: Intra-major-group edges (same broad family) ──
    # Each node connects to 4-6 random peers in the same major group
    random.seed(SEED)
    for mg, members in by_major.items():
        n = len(members)
        for node in members:
            k = min(6, n - 1)
            if k > 0:
                targets = random.sample([m for m in members if m != node], k)
                for t in targets:
                    G.add_edge(node, t, weight=1.5, etype="major")

    # ── Layer 3: Inter-group bridges (related career families) ──
    # Many more bridges between related fields
    random.seed(SEED + 1)
    for g1, g2 in RELATED_GROUPS:
        if g1 in by_major and g2 in by_major:
            m1 = by_major[g1]
            m2 = by_major[g2]
            # Connect ~30% of the smaller group to the other
            count = max(3, min(len(m1), len(m2)) // 3)
            pairs = list(zip(
                random.sample(m1, min(count, len(m1))),
                random.sample(m2, min(count, len(m2))),
            ))
            for n1, n2 in pairs:
                G.add_edge(n1, n2, weight=0.8, etype="bridge")

    # ── Layer 4: Central hub — radiating spokes to EVERY node ──
    # This creates the dense starburst seen in the reference image
    G.add_node("__hub__", label="Careers", major="hub", minor="", color="#cccccc")
    for node in list(G.nodes()):
        if node != "__hub__":
            G.add_edge("__hub__", node, weight=0.2, etype="hub")

    return G


def compute_layout(G: nx.Graph) -> dict:
    """
    Compute a radial force-directed layout:
    major groups are arranged in a circle, then spring layout refines positions.
    """
    # Initial positions: place major group centroids on a circle
    groups = sorted(g for g in set(nx.get_node_attributes(G, "major").values()) if g != "hub")
    group_angles = {
        g: 2 * math.pi * i / max(len(groups), 1)
        for i, g in enumerate(groups)
    }
    radius = 8.0

    init_pos = {}
    random.seed(SEED)
    for node, attrs in G.nodes(data=True):
        mg = attrs.get("major", "")
        if mg == "hub":
            init_pos[node] = (0.0, 0.0)
            continue
        angle = group_angles.get(mg, 0)
        # Scatter within sector — tighter spread for more overlap
        r = radius * 0.6 + random.gauss(0, 2.5)
        a = angle + random.gauss(0, 0.55)
        init_pos[node] = (r * math.cos(a), r * math.sin(a))

    # Refine with spring layout — smaller k = denser graph
    pos = nx.spring_layout(
        G,
        pos=init_pos,
        fixed=["__hub__"],   # pin the hub at the center
        k=0.22,
        iterations=250,
        seed=SEED,
        weight="weight",
    )
    return pos


def draw_graph(G: nx.Graph, pos: dict, output: str, interactive: bool = False):
    """Render the graph with a dark background and colorful nodes."""
    if interactive:
        matplotlib.use("TkAgg")

    fig, ax = plt.subplots(1, 1, figsize=FIG_SIZE, facecolor="#0D0D0D")
    ax.set_facecolor("#0D0D0D")
    ax.set_aspect("equal")
    ax.axis("off")

    # ── Draw edges (layered: hub spokes first, then bridges, then cluster) ──
    # Sort edges so hub spokes draw underneath everything
    hub_edges = []
    bridge_edges = []
    cluster_edges = []

    for u, v, d in G.edges(data=True):
        etype = d.get("etype", "major")
        if etype == "hub":
            hub_edges.append((u, v, d))
        elif etype == "bridge":
            bridge_edges.append((u, v, d))
        else:
            cluster_edges.append((u, v, d))

    # Hub spokes — thin, dim radiating lines from center
    for u, v, d in hub_edges:
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        ax.plot(
            [x0, x1], [y0, y1],
            color="#555555",
            linewidth=0.3,
            alpha=0.18,
            zorder=1,
        )

    # Inter-group bridges — medium, slightly brighter
    for u, v, d in bridge_edges:
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        ax.plot(
            [x0, x1], [y0, y1],
            color="#777777",
            linewidth=0.5,
            alpha=0.30,
            zorder=2,
        )

    # Intra-cluster edges — brightest, show the cluster structure
    for u, v, d in cluster_edges:
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        w = d.get("weight", 1.0)
        lw = 0.6 if w < 2.0 else 1.0
        ax.plot(
            [x0, x1], [y0, y1],
            color="#888888",
            linewidth=lw,
            alpha=0.35,
            zorder=3,
        )

    # ── Draw nodes ──
    colors = [G.nodes[n].get("color", "#888888") for n in G.nodes()]
    degrees = dict(G.degree())
    max_deg = max(degrees.values()) if degrees else 1

    sizes = []
    for n in G.nodes():
        if n == "__hub__":
            s = 500  # Central hub is large and prominent
        else:
            d = degrees[n]
            s = 15 + 120 * (d / max_deg) ** 0.7
        sizes.append(s)

    xs = [pos[n][0] for n in G.nodes()]
    ys = [pos[n][1] for n in G.nodes()]

    ax.scatter(
        xs, ys,
        c=colors,
        s=sizes,
        alpha=0.92,
        edgecolors="none",
        zorder=5,
    )

    # ── Add a subtle glow for the top hub nodes ──
    top_n = sorted(degrees, key=degrees.get, reverse=True)[:12]
    for n in top_n:
        x, y = pos[n]
        c = G.nodes[n].get("color", "#888888")
        ax.scatter(
            [x], [y],
            c=c,
            s=sizes[list(G.nodes()).index(n)] * 4,
            alpha=0.12,
            edgecolors="none",
            zorder=4,
        )

    # ── Legend ──
    legend_handles = []
    seen = set()
    for mg, (label, color) in sorted(MAJOR_GROUPS.items()):
        if mg in seen:
            continue
        seen.add(mg)
        # Only show groups that have nodes in the graph
        if any(G.nodes[n].get("major") == mg for n in G.nodes()):
            h = ax.scatter([], [], c=color, s=60, label=label)
            legend_handles.append(h)

    leg = ax.legend(
        handles=legend_handles,
        loc="lower left",
        fontsize=7,
        frameon=True,
        facecolor="#1a1a1a",
        edgecolor="#333333",
        labelcolor="#cccccc",
        ncol=2,
        columnspacing=1.0,
        handletextpad=0.3,
    )
    leg.get_frame().set_alpha(0.85)

    # ── Title ──
    ax.text(
        0.5, 0.97,
        "MascotGO Career Relationship Network",
        transform=ax.transAxes,
        fontsize=16,
        fontweight="bold",
        color="#e0e0e0",
        ha="center",
        va="top",
        fontfamily="sans-serif",
    )
    ax.text(
        0.5, 0.945,
        f"{G.number_of_nodes()} careers · {G.number_of_edges()} connections",
        transform=ax.transAxes,
        fontsize=9,
        color="#777777",
        ha="center",
        va="top",
    )

    plt.tight_layout(pad=1.0)

    if interactive:
        plt.show()
    else:
        fig.savefig(output, dpi=DPI, facecolor=fig.get_facecolor(), bbox_inches="tight")
        print(f"✅ Graph saved to {output}")
        plt.close(fig)


# ── Main ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate career relationship graph")
    parser.add_argument("--input",  default=INPUT_FILE,       help="Path to final_data.json")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,    help="Output image path")
    parser.add_argument("--nodes",  type=int, default=DEFAULT_MAX_NODES, help="Max nodes to display")
    parser.add_argument("--interactive", action="store_true",  help="Show in matplotlib window")
    args = parser.parse_args()

    print(f"📂 Loading careers from {args.input} …")
    all_careers = load_careers(args.input)
    print(f"   {len(all_careers)} total careers")

    print(f"🎯 Selecting up to {args.nodes} careers for the graph …")
    selected = select_careers(all_careers, args.nodes)
    print(f"   Selected {len(selected)}")

    print("🔗 Building relationship graph …")
    G = build_graph(selected)
    print(f"   {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print("📐 Computing layout …")
    pos = compute_layout(G)

    print("🎨 Rendering …")
    draw_graph(G, pos, args.output, interactive=args.interactive)


if __name__ == "__main__":
    main()
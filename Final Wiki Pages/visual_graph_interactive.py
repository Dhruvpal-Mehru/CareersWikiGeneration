"""
career_graph_interactive.py — Generate an interactive HTML career network graph.

Obsidian-style: positions are pre-computed and static. No bouncing physics.
Just smooth zoom, pan, hover tooltips, click-to-highlight, search, and legend filtering.

Usage:
    python career_graph_interactive.py
    python career_graph_interactive.py --nodes 600
    python career_graph_interactive.py --output my_graph.html
"""

import argparse
import json
import math
import random
from collections import defaultdict

import networkx as nx

INPUT_FILE = "../Data Management/final_data.json"
DEFAULT_MAX_NODES = 500
DEFAULT_OUTPUT = "career_graph.html"
SEED = 42

MAJOR_GROUPS = {
    "11": ("Management",               "#6C8EBF"),
    "13": ("Business & Finance",        "#82B366"),
    "15": ("Computer & Math",           "#D6A4E0"),
    "17": ("Architecture & Engineering","#F0C040"),
    "19": ("Life & Physical Science",   "#D4E157"),
    "21": ("Community & Social Service","#FF8A80"),
    "23": ("Legal",                     "#FFD54F"),
    "25": ("Education & Training",      "#4FC3F7"),
    "27": ("Arts, Design & Media",      "#F48FB1"),
    "29": ("Healthcare Practitioners",  "#EF5350"),
    "31": ("Healthcare Support",        "#CE93D8"),
    "33": ("Protective Service",        "#A1887F"),
    "35": ("Food Preparation",          "#FFB74D"),
    "37": ("Building & Grounds",        "#AED581"),
    "39": ("Personal Care & Service",   "#F06292"),
    "41": ("Sales",                     "#4DB6AC"),
    "43": ("Office & Admin Support",    "#9E9E9E"),
    "45": ("Farming, Fishing, Forestry","#8BC34A"),
    "47": ("Construction & Extraction", "#FF7043"),
    "49": ("Installation & Maintenance","#78909C"),
    "51": ("Production",                "#B0BEC5"),
    "53": ("Transportation",            "#7986CB"),
    "55": ("Military",                  "#546E7A"),
}

RELATED_GROUPS = [
    ("11", "13"), ("11", "23"), ("11", "41"), ("13", "41"), ("13", "43"),
    ("15", "17"), ("15", "19"), ("15", "27"),
    ("19", "29"), ("19", "17"), ("29", "31"), ("31", "39"),
    ("25", "21"), ("21", "39"), ("25", "27"),
    ("17", "47"), ("47", "49"), ("49", "51"), ("37", "47"),
    ("35", "39"), ("33", "55"), ("39", "41"),
    ("51", "53"), ("53", "49"), ("45", "19"), ("45", "37"),
    ("11", "15"), ("11", "29"), ("13", "15"), ("13", "23"),
    ("17", "51"), ("25", "29"), ("27", "41"), ("33", "21"),
    ("43", "41"), ("43", "11"),
]


def parse_major_group(career_id):
    parts = career_id.split("-")
    if len(parts) >= 2 and parts[1].isdigit():
        return parts[1]
    return ""

def parse_minor_group(career_id):
    parts = career_id.split("-")
    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
        return parts[1] + parts[2]
    return ""

def select_careers(all_careers, max_nodes):
    onet = [c for c in all_careers if not c["id"].startswith("career-alt") and not c["id"].startswith("career-bls")]
    bls  = [c for c in all_careers if c["id"].startswith("career-bls")]
    alt  = [c for c in all_careers if c["id"].startswith("career-alt")]
    selected = onet + bls
    if len(selected) < max_nodes:
        random.seed(SEED)
        random.shuffle(alt)
        selected += alt[:max_nodes - len(selected)]
    else:
        by_group = defaultdict(list)
        for c in selected:
            by_group[parse_major_group(c["id"])].append(c)
        per_group = max(1, max_nodes // max(len(by_group), 1))
        sampled = []
        for mg in sorted(by_group):
            random.seed(SEED + hash(mg))
            random.shuffle(by_group[mg])
            sampled.extend(by_group[mg][:per_group])
        remaining = [c for c in selected if c not in sampled]
        random.seed(SEED)
        random.shuffle(remaining)
        sampled += remaining[:max_nodes - len(sampled)]
        selected = sampled[:max_nodes]
    return selected


def build_graph_and_layout(careers):
    G = nx.Graph()
    by_major = defaultdict(list)
    by_minor = defaultdict(list)

    for c in careers:
        cid = c["id"]
        mg = parse_major_group(cid)
        mn = parse_minor_group(cid)
        gn, color = MAJOR_GROUPS.get(mg, ("Other", "#888888"))
        G.add_node(cid, title=c["title"], group=mg, groupName=gn, minor=mn, color=color, isHub=False)
        if mg: by_major[mg].append(cid)
        if mn: by_minor[mn].append(cid)

    G.add_node("__hub__", title="MascotGO Careers", group="hub", groupName="Central Hub", minor="", color="#cccccc", isHub=True)

    # Minor group mesh
    for mn, members in by_minor.items():
        for i in range(len(members)):
            for j in range(i+1, len(members)):
                G.add_edge(members[i], members[j], weight=3.0, etype="minor")

    # Major group peers
    random.seed(SEED)
    for mg, members in by_major.items():
        for node in members:
            k = min(6, len(members)-1)
            if k > 0:
                for t in random.sample([m for m in members if m != node], k):
                    G.add_edge(node, t, weight=1.5, etype="major")

    # Inter-group bridges
    random.seed(SEED+1)
    for g1, g2 in RELATED_GROUPS:
        if g1 in by_major and g2 in by_major:
            m1, m2 = by_major[g1], by_major[g2]
            count = max(3, min(len(m1), len(m2))//3)
            for n1, n2 in zip(random.sample(m1, min(count,len(m1))), random.sample(m2, min(count,len(m2)))):
                G.add_edge(n1, n2, weight=0.8, etype="bridge")

    # Hub spokes
    for node in list(G.nodes()):
        if node != "__hub__":
            G.add_edge("__hub__", node, weight=0.2, etype="hub")

    # Layout
    print("   Computing layout …")
    groups = sorted(g for g in set(nx.get_node_attributes(G, "group").values()) if g != "hub")
    group_angles = {g: 2*math.pi*i/max(len(groups),1) for i, g in enumerate(groups)}

    init_pos = {}
    random.seed(SEED)
    for node in G.nodes():
        mg = G.nodes[node].get("group", "")
        if mg == "hub":
            init_pos[node] = (0.0, 0.0)
            continue
        angle = group_angles.get(mg, 0)
        r = 4.8 + random.gauss(0, 2.5)
        a = angle + random.gauss(0, 0.55)
        init_pos[node] = (r*math.cos(a), r*math.sin(a))

    pos = nx.spring_layout(G, pos=init_pos, fixed=["__hub__"], k=0.22, iterations=300, seed=SEED, weight="weight")

    # Normalize to pixel space
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    span = max(max(xs)-min(xs), max(ys)-min(ys)) or 1
    scale = 1000 / span

    node_list = []
    node_index = {}
    for i, (nid, attrs) in enumerate(G.nodes(data=True)):
        px, py = pos[nid]
        node_list.append({
            "id": nid, "title": attrs["title"], "group": attrs["group"],
            "groupName": attrs["groupName"], "color": attrs["color"], "isHub": attrs["isHub"],
            "x": round((px-cx)*scale, 2), "y": round((py-cy)*scale, 2),
        })
        node_index[nid] = i

    link_list = []
    seen = set()
    for u, v, d in G.edges(data=True):
        key = (min(node_index[u], node_index[v]), max(node_index[u], node_index[v]))
        if key not in seen:
            seen.add(key)
            link_list.append({"source": node_index[u], "target": node_index[v], "type": d.get("etype","major")})

    return node_list, link_list


def generate_html(nodes, links, output):
    graph_json = json.dumps({"nodes": nodes, "links": links})
    legend_groups = []
    seen = set()
    for n in nodes:
        if n["group"] not in seen and n["group"] != "hub":
            seen.add(n["group"])
            legend_groups.append({"group": n["group"], "name": n["groupName"], "color": n["color"]})
    legend_groups.sort(key=lambda x: x["group"])
    legend_json = json.dumps(legend_groups)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MascotGO — Career Relationship Network</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
canvas {{ display: block; cursor: grab; }}
canvas.grabbing {{ cursor: grabbing; }}

.title-bar {{
    position: absolute; top: 0; left: 0; right: 0; padding: 20px 30px;
    background: linear-gradient(180deg, rgba(10,10,10,0.95) 0%, rgba(10,10,10,0.5) 70%, transparent 100%);
    pointer-events: none; z-index: 10;
}}
.title-bar h1 {{ font-size: 22px; font-weight: 700; color: #e0e0e0; }}
.title-bar .sub {{ font-size: 12px; color: #555; margin-top: 4px; }}

.legend {{
    position: absolute; bottom: 20px; left: 20px;
    background: rgba(18,18,18,0.94); border: 1px solid #2a2a2a; border-radius: 10px;
    padding: 14px 18px; z-index: 10; max-height: 55vh; overflow-y: auto;
}}
.legend h3 {{ font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: #555; margin-bottom: 10px; }}
.leg-item {{
    display: flex; align-items: center; gap: 8px; padding: 4px 6px;
    cursor: pointer; border-radius: 4px; transition: background 0.15s;
}}
.leg-item:hover {{ background: rgba(255,255,255,0.04); }}
.leg-item.on {{ background: rgba(255,255,255,0.07); }}
.leg-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
.leg-name {{ font-size: 11px; color: #aaa; }}
.leg-n {{ font-size: 10px; color: #444; margin-left: auto; padding-left: 10px; }}

.tt {{
    position: absolute; pointer-events: none; z-index: 20;
    background: rgba(12,12,12,0.96); border: 1px solid #333; border-radius: 8px;
    padding: 12px 16px; display: none; max-width: 300px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.7);
}}
.tt-t {{ font-size: 14px; font-weight: 700; color: #eee; margin-bottom: 3px; }}
.tt-g {{ font-size: 11px; margin-bottom: 6px; }}
.tt-c {{ font-size: 10px; color: #555; }}

.ctrls {{
    position: absolute; top: 20px; right: 20px; z-index: 10;
    display: flex; flex-direction: column; gap: 6px;
}}
.cb {{
    width: 36px; height: 36px; border-radius: 8px;
    background: rgba(25,25,25,0.92); border: 1px solid #333;
    color: #888; font-size: 18px; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.15s;
}}
.cb:hover {{ background: rgba(50,50,50,0.92); color: #ddd; }}

.sbar {{
    position: absolute; top: 80px; left: 50%; transform: translateX(-50%);
    z-index: 15; transition: all 0.25s ease;
}}
.sbar.hide {{ opacity: 0; pointer-events: none; transform: translateX(-50%) translateY(-8px); }}
.sbar input {{
    width: 320px; padding: 10px 16px; border-radius: 24px;
    background: rgba(18,18,18,0.96); border: 1px solid #333;
    color: #ddd; font-size: 13px; outline: none;
}}
.sbar input:focus {{ border-color: #555; }}
.sbar input::placeholder {{ color: #444; }}

.ipanel {{
    position: absolute; top: 80px; right: 20px; width: 260px;
    background: rgba(15,15,15,0.95); border: 1px solid #2a2a2a; border-radius: 10px;
    padding: 18px; z-index: 10; display: none; box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}}
.ipanel.on {{ display: block; }}
.ipanel h2 {{ font-size: 15px; color: #eee; margin-bottom: 6px; }}
.ipanel .ig {{ font-size: 12px; margin-bottom: 12px; }}
.ipanel .is {{ font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #555; margin: 12px 0 6px; }}
.ipanel .in {{ font-size: 11px; color: #aaa; padding: 3px 0; cursor: pointer; }}
.ipanel .in:hover {{ color: #fff; }}
.ipanel .ix {{ position: absolute; top: 12px; right: 14px; color: #555; cursor: pointer; font-size: 16px; }}
.ipanel .ix:hover {{ color: #aaa; }}
</style>
</head>
<body>

<canvas id="c"></canvas>

<div class="title-bar">
    <h1>MascotGO Career Relationship Network</h1>
    <div class="sub" id="stats"></div>
</div>

<div class="ctrls">
    <button class="cb" id="zi" title="Zoom in">+</button>
    <button class="cb" id="zo" title="Zoom out">−</button>
    <button class="cb" id="zr" title="Reset">⟲</button>
    <button class="cb" id="ts" title="Search">🔍</button>
</div>

<div class="sbar hide" id="sb">
    <input type="text" id="si" placeholder="Search careers…" autocomplete="off">
</div>

<div class="legend" id="lg"><h3>Career Families</h3></div>

<div class="tt" id="tt">
    <div class="tt-t"></div>
    <div class="tt-g"></div>
    <div class="tt-c"></div>
</div>

<div class="ipanel" id="ip">
    <span class="ix" id="ic">✕</span>
    <h2 id="ipt"></h2>
    <div class="ig" id="ipg"></div>
    <div class="is">Connected Careers</div>
    <div id="ipn"></div>
</div>

<script>
const G = {graph_json};
const LG = {legend_json};

const cv = document.getElementById('c');
const cx = cv.getContext('2d');
let W, H, dpr;
let hov = null, sel = null, hlg = null, stm = '', dirty = true;

function resize() {{
    dpr = devicePixelRatio || 1;
    W = innerWidth; H = innerHeight;
    cv.width = W * dpr; cv.height = H * dpr;
    cv.style.width = W + 'px'; cv.style.height = H + 'px';
    cx.setTransform(dpr, 0, 0, dpr, 0, 0);
    dirty = true;
}}
resize();
addEventListener('resize', resize);

// Static nodes
const N = G.nodes.map((n, i) => ({{ ...n, i, r: n.isHub ? 10 : 3.5 }}));
const L = G.links.map(l => ({{ s: N[l.source], t: N[l.target], type: l.type }}));

// Adjacency
const adj = new Map();
N.forEach(n => adj.set(n.i, new Set()));
L.forEach(l => {{ adj.get(l.s.i).add(l.t.i); adj.get(l.t.i).add(l.s.i); }});
N.forEach(n => {{
    n.cc = [...adj.get(n.i)].filter(i => !N[i].isHub).length;
    if (!n.isHub) n.r = 2.5 + Math.min(n.cc / 12, 5);
}});

const nh = L.filter(l => l.type !== 'hub').length;
document.getElementById('stats').textContent = N.length + ' careers · ' + nh + ' connections — scroll to zoom, drag to pan';

// Camera with smooth lerp
let cam = {{ x: 0, y: 0, z: 1 }};
let tgt = {{ x: 0, y: 0, z: 1 }};

function s2w(sx, sy) {{
    return {{ x: (sx - W/2) / cam.z - cam.x, y: (sy - H/2) / cam.z - cam.y }};
}}

function hex2rgba(h, a) {{
    return `rgba(${{parseInt(h.slice(1,3),16)}},${{parseInt(h.slice(3,5),16)}},${{parseInt(h.slice(5,7),16)}},${{a}})`;
}}

function draw() {{
    // Lerp camera
    let moving = false;
    for (const k of ['x','y','z']) {{
        const d = tgt[k] - cam[k];
        if (Math.abs(d) > (k === 'z' ? 0.0001 : 0.01)) {{
            cam[k] += d * 0.12;
            moving = true;
        }} else cam[k] = tgt[k];
    }}
    if (!dirty && !moving) return;
    dirty = false;

    cx.save();
    cx.clearRect(0, 0, W, H);
    cx.fillStyle = '#0a0a0a';
    cx.fillRect(0, 0, W, H);
    cx.translate(W/2, H/2);
    cx.scale(cam.z, cam.z);
    cx.translate(cam.x, cam.y);

    const an = hov || sel;
    const as = an ? adj.get(an.i) : null;
    cx.lineCap = 'round';

    // Links
    for (const l of L) {{
        let a, w;
        if (l.type === 'hub') {{ a = 0.04; w = 0.25; }}
        else if (l.type === 'bridge') {{ a = 0.10; w = 0.4; }}
        else if (l.type === 'minor') {{ a = 0.22; w = 0.7; }}
        else {{ a = 0.13; w = 0.45; }}

        let ec = '#888';
        if (an) {{
            const con = l.s.i === an.i || l.t.i === an.i;
            if (con) {{ a = l.type === 'hub' ? 0.2 : 0.65; w = l.type === 'hub' ? 0.5 : 1.6; ec = an.color; }}
            else a = 0.015;
        }}
        if (hlg) {{
            if (l.s.group !== hlg && l.t.group !== hlg) a = 0.008;
            else if (!an) a = Math.min(a * 2, 0.4);
        }}
        cx.beginPath(); cx.moveTo(l.s.x, l.s.y); cx.lineTo(l.t.x, l.t.y);
        cx.strokeStyle = hex2rgba(ec, a); cx.lineWidth = w / cam.z; cx.stroke();
    }}

    // Nodes
    for (const n of N) {{
        let r = n.r, na = 0.9, glow = 0;
        const ms = stm && n.title.toLowerCase().includes(stm);

        if (an) {{
            if (n.i === an.i) {{ glow = r*4; na = 1; r *= 1.5; }}
            else if (as.has(n.i)) {{ na = 0.95; r *= 1.15; }}
            else na = 0.07;
        }}
        if (hlg && n.group !== hlg && n.group !== 'hub') na = 0.06;
        if (ms) {{ glow = r*5; na = 1; r *= 1.3; }}

        if (glow > 0) {{
            const gr = cx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glow);
            gr.addColorStop(0, hex2rgba(n.color, 0.25));
            gr.addColorStop(1, hex2rgba(n.color, 0));
            cx.beginPath(); cx.arc(n.x, n.y, glow, 0, Math.PI*2); cx.fillStyle = gr; cx.fill();
        }}
        cx.beginPath(); cx.arc(n.x, n.y, r, 0, Math.PI*2);
        cx.fillStyle = hex2rgba(n.color, na); cx.fill();
    }}

    // Labels — ONLY shown on hover or click. No auto-labels.
    if (an && !an.isHub) {{
        const pad = 3 / cam.z;

        // Hovered/selected node label
        const fs = Math.max(5, 10 / cam.z);
        cx.font = `700 ${{fs}}px -apple-system, sans-serif`;
        cx.textBaseline = 'middle';
        const right = an.x >= 0;
        cx.textAlign = right ? 'left' : 'right';
        const lx = right ? an.x + an.r*1.5 + pad + 2 : an.x - an.r*1.5 - pad - 2;

        cx.strokeStyle = hex2rgba('#0a0a0a', 0.95);
        cx.lineWidth = 3.5 / cam.z;
        cx.lineJoin = 'round';
        cx.strokeText(an.title, lx, an.y);
        cx.fillStyle = '#fff';
        cx.fillText(an.title, lx, an.y);

        // Neighbor labels — only when CLICKED (selected), not just hovered
        if (sel && sel.i === an.i) {{
            const nfs = Math.max(3.5, 7 / cam.z);
            cx.font = `500 ${{nfs}}px -apple-system, sans-serif`;

            const neighbors = [...as].filter(i => !N[i].isHub).map(i => N[i]).sort((a,b) => b.cc - a.cc);
            const nplaced = [];

            for (const nb of neighbors) {{
                const r2 = nb.x >= 0;
                cx.textAlign = r2 ? 'left' : 'right';
                const nlx = r2 ? nb.x + nb.r + pad + 2 : nb.x - nb.r - pad - 2;
                const ntw = cx.measureText(nb.title).width;
                const nbox = r2
                    ? {{ x1: nlx, y1: nb.y - nfs*0.6, x2: nlx + ntw, y2: nb.y + nfs*0.6 }}
                    : {{ x1: nlx - ntw, y1: nb.y - nfs*0.6, x2: nlx, y2: nb.y + nfs*0.6 }};

                let skip = false;
                for (const p of nplaced) {{
                    if (nbox.x1 < p.x2 && nbox.x2 > p.x1 && nbox.y1 < p.y2 && nbox.y2 > p.y1) {{ skip = true; break; }}
                }}
                if (skip) continue;
                nplaced.push(nbox);

                cx.strokeStyle = hex2rgba('#0a0a0a', 0.85);
                cx.lineWidth = 2.5 / cam.z;
                cx.lineJoin = 'round';
                cx.strokeText(nb.title, nlx, nb.y);
                cx.fillStyle = hex2rgba('#bbb', 0.7);
                cx.fillText(nb.title, nlx, nb.y);
            }}
        }}
    }}
    cx.restore();
}}

// Interaction
let pan = null;

function mp(e) {{ return {{ x: e.clientX, y: e.clientY }}; }}

function findN(mx, my) {{
    const w = s2w(mx, my);
    const hr = Math.max(8, 14 / cam.z);
    let best = null, bd = Infinity;
    for (const n of N) {{
        const d = Math.hypot(n.x - w.x, n.y - w.y);
        if (d < hr && d < bd) {{ best = n; bd = d; }}
    }}
    return best;
}}

cv.addEventListener('mousedown', e => {{
    pan = {{ ...mp(e), cx: tgt.x, cy: tgt.y }};
    cv.classList.add('grabbing');
}});

cv.addEventListener('mousemove', e => {{
    const p = mp(e);
    if (pan) {{
        tgt.x = pan.cx + (p.x - pan.x) / cam.z;
        tgt.y = pan.cy + (p.y - pan.y) / cam.z;
        dirty = true;
    }} else {{
        const n = findN(p.x, p.y);
        if (n !== hov) {{ hov = n; cv.style.cursor = n ? 'pointer' : 'grab'; dirty = true; }}
        const tt = document.getElementById('tt');
        if (n && !n.isHub) {{
            tt.style.display = 'block'; tt.style.left = (p.x+16)+'px'; tt.style.top = (p.y-10)+'px';
            tt.querySelector('.tt-t').textContent = n.title;
            const tg = tt.querySelector('.tt-g'); tg.textContent = n.groupName; tg.style.color = n.color;
            tt.querySelector('.tt-c').textContent = n.cc + ' related careers';
        }} else tt.style.display = 'none';
    }}
}});

cv.addEventListener('mouseup', e => {{
    cv.classList.remove('grabbing');
    if (pan) {{
        const p = mp(e);
        if (Math.hypot(p.x - pan.x, p.y - pan.y) < 4) {{
            const n = findN(p.x, p.y);
            selNode(n && !n.isHub ? (n === sel ? null : n) : null);
        }}
        pan = null;
    }}
}});

cv.addEventListener('mouseleave', () => {{ hov = null; document.getElementById('tt').style.display = 'none'; dirty = true; }});

cv.addEventListener('wheel', e => {{
    e.preventDefault();
    tgt.z = Math.max(0.15, Math.min(20, tgt.z * (e.deltaY > 0 ? 0.88 : 1.14)));
    dirty = true;
}}, {{ passive: false }});

// Touch
let ltd = null;
cv.addEventListener('touchstart', e => {{
    e.preventDefault();
    if (e.touches.length === 1) {{ const t = e.touches[0]; pan = {{ x: t.clientX, y: t.clientY, cx: tgt.x, cy: tgt.y }}; }}
    else if (e.touches.length === 2) ltd = Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY);
}}, {{ passive: false }});
cv.addEventListener('touchmove', e => {{
    e.preventDefault();
    if (e.touches.length === 1 && pan) {{
        const t = e.touches[0];
        tgt.x = pan.cx + (t.clientX - pan.x) / cam.z;
        tgt.y = pan.cy + (t.clientY - pan.y) / cam.z;
        dirty = true;
    }} else if (e.touches.length === 2 && ltd) {{
        const d = Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY);
        tgt.z = Math.max(0.15, Math.min(20, tgt.z * d/ltd));
        ltd = d; dirty = true;
    }}
}}, {{ passive: false }});
cv.addEventListener('touchend', () => {{ pan = null; ltd = null; }});

// Selection panel
function selNode(node) {{
    sel = node;
    const ip = document.getElementById('ip');
    if (!node) {{ ip.classList.remove('on'); dirty = true; return; }}
    document.getElementById('ipt').textContent = node.title;
    const g = document.getElementById('ipg'); g.textContent = node.groupName; g.style.color = node.color;
    const nb = document.getElementById('ipn'); nb.innerHTML = '';
    const nbs = [...adj.get(node.i)].filter(i => !N[i].isHub).sort((a,b) => N[a].group.localeCompare(N[b].group));
    nbs.slice(0, 25).forEach(ni => {{
        const n = N[ni], d = document.createElement('div');
        d.className = 'in';
        d.innerHTML = '<span style="color:'+n.color+';margin-right:6px">●</span>' + n.title;
        d.onclick = () => {{ selNode(n); tgt.x = -n.x; tgt.y = -n.y; dirty = true; }};
        nb.appendChild(d);
    }});
    if (nbs.length > 25) {{
        const m = document.createElement('div'); m.className = 'in'; m.style.color = '#444';
        m.textContent = '+ ' + (nbs.length-25) + ' more…'; nb.appendChild(m);
    }}
    ip.classList.add('on');
    tgt.x = -node.x; tgt.y = -node.y;
    dirty = true;
}}
document.getElementById('ic').onclick = () => selNode(null);

// Controls
document.getElementById('zi').onclick = () => {{ tgt.z = Math.min(20, tgt.z*1.4); dirty = true; }};
document.getElementById('zo').onclick = () => {{ tgt.z = Math.max(0.15, tgt.z/1.4); dirty = true; }};
document.getElementById('zr').onclick = () => {{
    tgt = {{x:0,y:0,z:1}}; selNode(null); hlg = null; stm = '';
    document.getElementById('si').value = '';
    document.querySelectorAll('.leg-item').forEach(e => e.classList.remove('on'));
    dirty = true;
}};

// Search
const sb = document.getElementById('sb'), si = document.getElementById('si');
document.getElementById('ts').onclick = () => {{
    sb.classList.toggle('hide');
    if (!sb.classList.contains('hide')) si.focus();
    else {{ si.value = ''; stm = ''; dirty = true; }}
}};
si.oninput = e => {{ stm = e.target.value.toLowerCase(); dirty = true; }};
si.onkeydown = e => {{
    if (e.key === 'Enter' && stm) {{
        const m = N.find(n => !n.isHub && n.title.toLowerCase().includes(stm));
        if (m) selNode(m);
    }}
}};

// Legend
const lgEl = document.getElementById('lg');
const gc = {{}}; N.forEach(n => {{ if (n.group !== 'hub') gc[n.group] = (gc[n.group]||0)+1; }});
LG.forEach(g => {{
    const el = document.createElement('div'); el.className = 'leg-item';
    el.innerHTML = `<span class="leg-dot" style="background:${{g.color}}"></span><span class="leg-name">${{g.name}}</span><span class="leg-n">${{gc[g.group]||0}}</span>`;
    el.onclick = () => {{
        if (hlg === g.group) {{ hlg = null; el.classList.remove('on'); }}
        else {{ hlg = g.group; document.querySelectorAll('.leg-item').forEach(e=>e.classList.remove('on')); el.classList.add('on'); }}
        selNode(null); dirty = true;
    }};
    lgEl.appendChild(el);
}});

// Loop — only redraws when dirty or camera lerping
(function loop() {{ draw(); requestAnimationFrame(loop); }})();
</script>
</body>
</html>"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Saved to {output}")
    print(f"   Open in Chrome/Firefox/Safari")


def main():
    parser = argparse.ArgumentParser(description="Generate interactive HTML career graph")
    parser.add_argument("--input",  default=INPUT_FILE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--nodes",  type=int, default=DEFAULT_MAX_NODES)
    args = parser.parse_args()

    print(f"📂 Loading from {args.input} …")
    with open(args.input, "r") as f:
        all_careers = json.load(f)
    print(f"   {len(all_careers)} careers")

    print(f"🎯 Selecting up to {args.nodes} …")
    selected = select_careers(all_careers, args.nodes)
    print(f"   {len(selected)} selected")

    print("🔗 Building graph …")
    nodes, links = build_graph_and_layout(selected)
    print(f"   {len(nodes)} nodes, {len(links)} links")

    print("📄 Generating HTML …")
    generate_html(nodes, links, args.output)


if __name__ == "__main__":
    main()
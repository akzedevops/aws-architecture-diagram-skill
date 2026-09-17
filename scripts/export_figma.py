#!/usr/bin/env python3
"""Export a diagram data file to Figma through the Figma MCP's `use_figma` tool.

    python export_figma.py DATA.py                 # writes figma_step1.js and icon_order.txt
    python export_figma.py DATA.py --root 17:3     # writes figma_step2.js for that root frame

Figma has no file import for this, so the export is two Plugin API scripts run through
`use_figma` (load the `figma-use` skill first). Step 1 creates a page and a frame with the
zones, icon placeholders and captions and returns the frame's node id plus the placeholder
ids. Step 2, generated with that id, draws the connectors, arrowheads and label plates on
the same frame. Then upload the PNGs from ICON_DIR onto the placeholders with
`upload_assets` in the order listed in icon_order.txt. Each step is one tool call; the
Starter plan's call limit can stop a large diagram between them, which is why they are
separate and resumable.
"""
import argparse, io, json, os, runpy

STEP1 = r"""
const D = %(data)s;
const hex = h => ({r:parseInt(h.slice(1,3),16)/255,g:parseInt(h.slice(3,5),16)/255,b:parseInt(h.slice(5,7),16)/255});
const solid = h => [{type:"SOLID", color:hex(h)}];
await figma.loadFontAsync({family:"Inter",style:"Regular"});
await figma.loadFontAsync({family:"Inter",style:"Semi Bold"});
await figma.loadFontAsync({family:"Inter",style:"Bold"});
const page = figma.createPage();
page.name = %(page)s;
await figma.setCurrentPageAsync(page);

const root = figma.createFrame();
root.name = %(frame)s;
root.x = 0; root.y = 0; root.resize(%(W)d, %(H)d);
root.fills = solid("#ffffff"); root.clipsContent = false;

function text(s,x,y,size,style,color,w,align){
  const t = figma.createText();
  t.fontName = {family:"Inter", style:style};
  t.fontSize = size;
  t.characters = s;
  if (w){ t.textAutoResize = "HEIGHT"; t.resize(w, t.height); }
  else { t.textAutoResize = "WIDTH_AND_HEIGHT"; }
  t.textAlignHorizontal = align || "LEFT";
  t.fills = solid(color);
  t.x = x; t.y = y;
  root.appendChild(t);
  return t;
}
if (D.title) text(D.title, 42, 28, 19, "Bold", "#151d2b").name = "title";
if (D.subtitle) text(D.subtitle, 42, 58, 12.5, "Regular", "#4b5563", D.W - 80).name = "subtitle";

// zones: AWS group palette, all transparent; security-group labels straddle the top border
for (const g of D.groups){
  const f = figma.createFrame();
  f.name = "zone/" + g.l;
  f.x = g.x; f.y = g.y; f.resize(g.w, g.h);
  f.fills = []; f.strokes = solid(g.bc); f.strokeWeight = 2; f.cornerRadius = 4;
  f.clipsContent = false;
  if (g.d) f.dashPattern = [6,5];
  root.appendChild(f);
  const ly = D.straddle.includes(g.n) ? g.y - 9 : g.y + 7;
  let lx = g.x + 10;
  const plate = figma.createRectangle();
  plate.name = "zonelabel-bg"; plate.fills = solid("#ffffff"); plate.cornerRadius = 2;
  root.appendChild(plate);
  if (g.i){
    const c = figma.createRectangle();
    c.name = "chip"; c.resize(13,13); c.x = lx; c.y = ly + 2;
    c.cornerRadius = 2; c.fills = solid(g.bc); c.opacity = 0.85;
    root.appendChild(c); lx += 20;
  }
  const t = text(g.l, lx, ly, 12, "Semi Bold", g.fc);
  t.letterSpacing = {unit:"PERCENT", value:3};
  t.name = "zonelabel";
  plate.resize(t.x + t.width - (g.x + 10) + 10, 18);
  plate.x = g.x + 5; plate.y = ly - 1;
}

// resources: 42px icon placeholder centred in a 180px block, caption and sub-caption beneath
const iconNodes = [];
for (const r of D.res){
  if (r.ic){
    const ic = figma.createRectangle();
    ic.name = "icon/" + r.ic;
    ic.resize(42,42); ic.x = r.x + 69; ic.y = r.y;
    ic.fills = solid("#e8ecf2"); ic.cornerRadius = 4;
    root.appendChild(ic);
    iconNodes.push({id: ic.id, icon: r.ic});
  } else {
    const b = figma.createRectangle();
    b.name = "box/" + r.l;
    b.resize(42,42); b.x = r.x + 69; b.y = r.y;
    b.fills = []; b.strokes = solid("#5A6C86"); b.strokeWeight = 1.6; b.cornerRadius = 5;
    root.appendChild(b);
  }
  text(r.l, r.x, r.y + 48, 12.5, "Bold", "#232f3e", 180, "CENTER").name = "label";
  if (r.s) text(r.s, r.x, r.y + 65, 11, "Regular", "#4a5568", 180, "CENTER").name = "sublabel";
}
return { rootId: root.id, iconNodes, count: root.children.length };
"""

STEP2 = r"""const C = %(conn)s;
const hex = h => ({r:parseInt(h.slice(1,3),16)/255,g:parseInt(h.slice(3,5),16)/255,b:parseInt(h.slice(5,7),16)/255});
const solid = h => [{type:"SOLID", color:hex(h)}];
await figma.loadFontAsync({family:"Inter",style:"Semi Bold"});
await figma.loadFontAsync({family:"Inter",style:"Bold"});
const root = await figma.getNodeByIdAsync(%(root)s);
const STROKE = "#434e5e";

// vectorPaths re-origin geometry to their own bbox, so emit each path relative to its bbox
// and place the node at the bbox origin, or everything piles up at 0,0.
function place(node, pts, data, winding){
  const mx = Math.min(...pts.map(q => q[0])), my = Math.min(...pts.map(q => q[1]));
  node.vectorPaths = [{windingRule: winding, data: data(mx, my)}];
  root.appendChild(node);
  node.x = mx; node.y = my;
}
for (const c of C){
  const v = figma.createVector();
  v.name = "conn";
  v.strokes = solid(STROKE); v.strokeWeight = 1.7;
  v.strokeJoin = "ROUND"; v.strokeCap = "NONE"; v.fills = [];
  if (c.d) v.dashPattern = [5,4];
  place(v, c.p, (mx,my) => "M " + c.p.map(q => (q[0]-mx) + " " + (q[1]-my)).join(" L "), "NONE");
  if (c.a === 0) continue;
  const p = c.p[c.p.length-2], q = c.p[c.p.length-1];
  const dx = q[0]-p[0], dy = q[1]-p[1], L = Math.hypot(dx,dy) || 1;
  const ux = dx/L, uy = dy/L, nx = -uy, ny = ux, s = 6, w = 3.4;
  const tri = [q, [q[0]-ux*s+nx*w, q[1]-uy*s+ny*w], [q[0]-ux*s-nx*w, q[1]-uy*s-ny*w]];
  const a = figma.createVector();
  a.name = "arrow"; a.fills = solid(STROKE); a.strokes = [];
  place(a, tri, (mx,my) =>
    `M ${tri[0][0]-mx} ${tri[0][1]-my} L ${tri[1][0]-mx} ${tri[1][1]-my} L ${tri[2][0]-mx} ${tri[2][1]-my} Z`,
    "NONZERO");
}
// resources back on top: zones < connectors < resources < edge labels
for (const n of root.children.filter(n =>
      n.name.startsWith("icon/") || n.name.startsWith("box/") ||
      n.name === "label" || n.name === "sublabel" ||
      n.name === "zonelabel-bg" || n.name === "chip" || n.name === "zonelabel")) root.appendChild(n);
// edge labels on a white plate
for (const c of C){
  if (!c.l || !c.lp) continue;
  const t = figma.createText();
  t.fontName = {family:"Inter", style:"Bold"};
  t.fontSize = 11.5; t.characters = c.l;
  t.textAutoResize = "WIDTH_AND_HEIGHT";
  t.fills = solid("#232f3e"); t.name = "edgelabel";
  root.appendChild(t);
  t.x = c.lp[0] - t.width/2; t.y = c.lp[1] - t.height/2;
  const bg = figma.createRectangle();
  bg.name = "edgelabel-bg";
  bg.resize(t.width + 18, t.height + 4);
  bg.x = t.x - 9; bg.y = t.y - 2;
  bg.cornerRadius = 3; bg.fills = solid("#ffffff");
  root.insertChild(root.children.indexOf(t), bg);
}
return { children: root.children.length,
         conns: root.children.filter(n => n.name === "conn").length,
         arrows: root.children.filter(n => n.name === "arrow").length,
         edgelabels: root.children.filter(n => n.name === "edgelabel").length,
         strayAtOrigin: root.children.filter(n => n.x === 0 && n.y === 0).map(n => n.name) };
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--root", help="frame node id returned by step 1; writes figma_step2.js")
    ap.add_argument("--out-dir", default="_figma", help="where the .js files go (relative to the data file)")
    ap.add_argument("--page", help="page name (default: the diagram title)")
    a = ap.parse_args()
    path = os.path.abspath(a.data)
    d = runpy.run_path(path)
    out = os.path.join(os.path.dirname(path), a.out_dir)
    os.makedirs(out, exist_ok=True)
    title, sub = d.get("TITLE", ""), d.get("SUBTITLE", "").replace("<br>", "\n")
    oy = 95 if (title or sub) else 0    # diagram sits below the title block
    W, H = d.get("W", 1900), d.get("H", 1200)
    groups = [dict(n=g[0], x=g[1], y=g[2] + oy, w=g[3], h=g[4], l=g[5], bc=g[6], fc=g[7], d=g[8], i=g[9])
              for g in d["GROUPS"]]
    res = [dict(ic=r[0] or "", x=r[1] - 90, y=r[2] + oy, l=r[3], s=r[4]) for r in d["RES"]]
    conn = []
    for c in d["CONN"]:
        pts, dashed, lab, lp = c[:4]
        conn.append(dict(p=[[x, y + oy] for x, y in pts], d=dashed, a=(c[4] if len(c) > 4 else 1),
                         l=lab, lp=([lp[0], lp[1] + oy] if lp else None)))
    if a.root:
        js = STEP2 % {"conn": json.dumps(conn, ensure_ascii=False), "root": json.dumps(a.root)}
        p = os.path.join(out, "figma_step2.js")
        io.open(p, "w", encoding="utf-8").write(js)
        print("wrote %s  (%d connectors, root %s)" % (p, len(conn), a.root))
        return
    data = dict(title=title, subtitle=sub, W=W, H=H + oy + 40, groups=groups, res=res,
                straddle=sorted(d.get("STRADDLE", ())))
    js = STEP1 % {"data": json.dumps(data, ensure_ascii=False), "page": json.dumps(a.page or title or "architecture"),
                  "frame": json.dumps(title or "architecture"), "W": W, "H": H + oy + 40}
    p = os.path.join(out, "figma_step1.js")
    io.open(p, "w", encoding="utf-8").write(js)
    icons = [r["ic"] for r in res if r["ic"]]
    io.open(os.path.join(out, "icon_order.txt"), "w").write("\n".join(icons))
    print("wrote %s  (%d groups, %d resources, %d icon placeholders)" % (p, len(groups), len(res), len(icons)))
    print("next: run it through use_figma, then rerun with --root <rootId> for step 2")


if __name__ == "__main__":
    main()

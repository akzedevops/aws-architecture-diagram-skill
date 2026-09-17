#!/usr/bin/env python3
"""Export a diagram data file to a Mermaid `architecture-beta` block for READMEs and wikis.

    python export_mermaid.py DATA.py [--out file.mmd]

Mermaid's architecture diagrams have five stock icons (cloud, database, disk, internet,
server), no edge labels and their own layout, so this is a structural sketch for places
that render Mermaid (GitHub, GitLab, Notion, docs sites), not a substitute for the PNG.
Groups nest as they contain each other; edges take their sides from the direction of the
first and last segment of the connector.
"""
import argparse, io, os, re, runpy

ICON = {"rds": "database", "rds-mysql": "database", "rds-postgres": "database", "aurora": "database",
        "dynamodb": "database", "elasticache": "database", "redshift": "database", "documentdb": "database",
        "s3": "disk", "efs": "disk", "ebs": "disk", "backup": "disk", "glacier": "disk", "ecr": "disk",
        "route53": "internet", "cloudfront": "internet", "internet": "internet", "users": "internet",
        "user": "internet", "client": "internet", "waf": "internet", "api-gateway": "internet"}


def ident(s, used):
    base = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "n"
    name, k = base, 2
    while name in used:
        name, k = "%s_%d" % (base, k), k + 1
    used.add(name)
    return name


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--out")
    a = ap.parse_args()
    path = os.path.abspath(a.data)
    d = runpy.run_path(path)
    GROUPS, RES, CONN = d["GROUPS"], d["RES"], d["CONN"]
    out = a.out or os.path.splitext(d.get("OUT", "architecture.png"))[0] + ".mmd"
    out = os.path.join(os.path.dirname(path), out) if not os.path.isabs(out) else out

    gbox = {g[0]: (g[1], g[2], g[1] + g[3], g[2] + g[4]) for g in GROUPS}
    used = set()
    gid = {g[0]: ident(g[0], used) for g in GROUPS}

    def innermost(px, py):
        best, key = None, None
        for k, (x0, y0, x1, y1) in gbox.items():
            if x0 <= px <= x1 and y0 <= py <= y1:
                area = (x1 - x0) * (y1 - y0)
                if best is None or area < best:
                    best, key = area, k
        return key

    gparent = {}
    for k, (x0, y0, x1, y1) in gbox.items():
        best, parent = None, None
        for k2, (a0, b0, a1, b1) in gbox.items():
            if k2 != k and a0 <= x0 and b0 <= y0 and a1 >= x1 and b1 >= y1:
                area = (a1 - a0) * (b1 - b0)
                if best is None or area < best:
                    best, parent = area, k2
        gparent[k] = parent

    lines = ["architecture-beta"]
    for key, x, y, w, h, label, *_ in GROUPS:
        p = gparent[key]
        lines.append("    group %s(cloud)[%s]%s" % (gid[key], label.replace("[", "(").replace("]", ")"),
                                                    " in " + gid[p] if p else ""))
    rid, boxes = [], []
    for icon, cx, y, label, sub in RES:
        i = ident(label, used)
        rid.append(i)
        boxes.append((cx - 90, y - 4, cx + 90, y + 82))
        g = innermost(cx, y + 21)
        lines.append("    service %s(%s)[%s]%s" % (i, ICON.get(icon, "server"), label.replace("[", "(").replace("]", ")"),
                                                   " in " + gid[g] if g else ""))

    def near(pt):
        best, idx = None, None
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            if x0 - 14 <= pt[0] <= x1 + 14 and y0 - 14 <= pt[1] <= y1 + 14:
                dist = abs(pt[0] - (x0 + x1) / 2) + abs(pt[1] - (y0 + y1) / 2)
                if best is None or dist < best:
                    best, idx = dist, i
        return idx

    def side(p, q, at_start):
        dx, dy = q[0] - p[0], q[1] - p[1]
        if abs(dx) >= abs(dy):
            return ("R" if dx > 0 else "L") if at_start else ("L" if dx > 0 else "R")
        return ("B" if dy > 0 else "T") if at_start else ("T" if dy > 0 else "B")

    conns = [dict(pts=c[0], src=near(c[0][0]), dst=near(c[0][-1])) for c in CONN]
    for c in conns:                      # trunks: chain to the connector that starts where this ends
        if c["dst"] is None:
            for o in conns:
                if o is not c and abs(o["pts"][0][0] - c["pts"][-1][0]) <= 2 and abs(o["pts"][0][1] - c["pts"][-1][1]) <= 2:
                    c["dst"] = o["dst"]
                    break
    n = 0
    for c in conns:
        if c["src"] is None or c["dst"] is None or c["src"] == c["dst"]:
            continue
        pts = c["pts"]
        lines.append("    %s:%s --> %s:%s" % (rid[c["src"]], side(pts[0], pts[1], True),
                                              side(pts[-2], pts[-1], False), rid[c["dst"]]))
        n += 1
    io.open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("wrote %s  (%d groups, %d services, %d edges)" % (out, len(GROUPS), len(RES), n))


if __name__ == "__main__":
    main()

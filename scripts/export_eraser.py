#!/usr/bin/env python3
"""Export a diagram data file to Eraser's cloud-architecture diagram-as-code.

    python export_eraser.py DATA.py [--out file.eraser]

Eraser lays diagrams out itself, so only the structure survives: groups nested as they
contain each other on the canvas, one node per resource with the matching `aws-...` icon,
and one connection per flow. Paste the output into a cloud architecture diagram at
app.eraser.io, or, with the Eraser MCP connected, create a file and call
`manually_create_diagram` with diagramType "cloud-architecture-diagram" and this text as
`code`. Icon names below were checked against docs.eraser.io/docs/icons; anything not in
the table is emitted without an icon, which Eraser draws as a plain node.
"""
import argparse, io, os, re, runpy

ICONS = {
    "eks": "aws-elastic-kubernetes-service", "ecs": "aws-elastic-container-service", "fargate": "aws-fargate",
    "ec2": "aws-ec2", "lambda": "aws-lambda", "ecr": "aws-elastic-container-registry",
    "rds": "aws-rds", "rds-mysql": "aws-rds", "rds-postgres": "aws-rds", "aurora": "aws-aurora",
    "dynamodb": "aws-dynamodb", "elasticache": "aws-elasticache",
    "s3": "aws-simple-storage-service", "efs": "aws-efs", "backup": "aws-backup",
    "glacier": "aws-simple-storage-service-glacier",
    "cloudfront": "aws-cloudfront", "route53": "aws-route-53", "alb": "aws-elb-application-load-balancer",
    "elb": "aws-elb-application-load-balancer", "nlb": "aws-elb-network-load-balancer",
    "nat": "aws-nat-gateway", "vpc": "aws-vpc", "api-gateway": "aws-api-gateway",
    "waf": "aws-waf", "shield": "aws-shield", "secrets": "aws-secrets-manager",
    "kms": "aws-key-management-service", "iam": "aws-identity-and-access-management", "cognito": "aws-cognito",
    "cloudwatch": "aws-cloudwatch", "cloudtrail": "aws-cloudtrail", "guardduty": "aws-guardduty",
    "config": "aws-config", "sns": "aws-simple-notification-service", "sqs": "aws-simple-queue-service",
    "eventbridge": "aws-eventbridge", "step-functions": "aws-step-functions",
    "users": "users", "user": "user", "gitlab": "gitlab", "github": "github", "argo": "argocd",
    "k8s-pod": "kubernetes",
}
GROUP_ICONS = {"#232F3E": "aws-cloud", "#8C4FFF": "aws-vpc"}


def clean(s):
    s = s.replace("·", "-").replace("+", "and").replace("/", "-")
    s = re.sub(r"[^\w \-.()~]", "", s).strip()
    return re.sub(r"\s+", " ", s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--out")
    a = ap.parse_args()
    path = os.path.abspath(a.data)
    d = runpy.run_path(path)
    GROUPS, RES, CONN = d["GROUPS"], d["RES"], d["CONN"]
    out = a.out or os.path.splitext(d.get("OUT", "architecture.png"))[0] + ".eraser"
    out = os.path.join(os.path.dirname(path), out) if not os.path.isabs(out) else out

    gbox = {g[0]: (g[1], g[2], g[1] + g[3], g[2] + g[4]) for g in GROUPS}
    glabel = {g[0]: g[5] for g in GROUPS}
    gcolour = {g[0]: g[6].upper() for g in GROUPS}

    def innermost(px, py, exclude=None):
        best, key = None, None
        for k, (x0, y0, x1, y1) in gbox.items():
            if k == exclude:
                continue
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

    # unique node names: the caption, and when captions repeat, the zone (or the nearest
    # ancestor group that tells the copies apart) in brackets
    def ancestors(g):
        chain = []
        while g:
            chain.append(g)
            g = gparent.get(g)
        return chain

    names, res_group, counts = [], [], {}
    for icon, cx, y, label, sub in RES:
        counts[label] = counts.get(label, 0) + 1
    for icon, cx, y, label, sub in RES:
        res_group.append(innermost(cx, y + 21))
    # Eraser merges nodes that share a label, and brackets in a node name do not survive
    # its parser, so repeated captions get the zone as a plain suffix in both name and label
    used, tags = {}, []
    for i, (icon, cx, y, label, sub) in enumerate(RES):
        name, tag = clean(label), None
        if counts[label] > 1:
            for g in ancestors(res_group[i]):
                if re.search(r"zone|region|account", glabel[g], re.I):
                    tag = clean(glabel[g]).split()[-1]
                    break
            if tag is None and res_group[i]:
                tag = clean(glabel[res_group[i]]).split()[-1]
            name = "%s %s" % (name, tag) if tag else name
        if name in used:
            used[name] += 1
            name = "%s %d" % (name, used[name])
            tag = (tag + " " if tag else "") + str(used[name])
        else:
            used[name] = 1
        names.append(name)
        tags.append(tag)

    # resolve connector endpoints to resources (icon box widened to the caption block)
    boxes = [(cx - 90, y - 4, cx + 90, y + 82) for icon, cx, y, label, sub in RES]

    def near(pt):
        best, idx = None, None
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            if x0 - 14 <= pt[0] <= x1 + 14 and y0 - 14 <= pt[1] <= y1 + 14:
                dist = abs(pt[0] - (x0 + x1) / 2) + abs(pt[1] - (y0 + y1) / 2)
                if best is None or dist < best:
                    best, idx = dist, i
        return idx

    def on_path(pt, o):
        for (ax, ay), (bx, by) in zip(o["pts"], o["pts"][1:]):
            if (ax == bx == pt[0] and min(ay, by) - 2 <= pt[1] <= max(ay, by) + 2) or \
               (ay == by == pt[1] and min(ax, bx) - 2 <= pt[0] <= max(ax, bx) + 2):
                return True
        return False

    def same(p, q):
        return abs(p[0] - q[0]) <= 2 and abs(p[1] - q[1]) <= 2

    # a run with no arrowhead that ends exactly where another connector starts, or on its
    # path, is a shared trunk: its real target is that connector's target
    conns = []
    for c in CONN:
        pts, dashed, lab, lp = c[:4]
        arrow = c[4] if len(c) > 4 else 1
        conns.append(dict(pts=pts, dashed=dashed, label=lab, arrow=arrow, src=near(pts[0]),
                          dst=None if arrow == 0 else near(pts[-1]), chain=None))
    for c in conns:
        if c["arrow"] == 0:
            for o in conns:
                if o is not c and (same(o["pts"][0], c["pts"][-1]) or on_path(c["pts"][-1], o)):
                    c["chain"] = o
                    break
    for _ in range(len(conns)):
        for c in conns:
            if c["dst"] is None and c["chain"] is not None and c["chain"]["dst"] is not None:
                c["dst"], c["label"] = c["chain"]["dst"], c["label"] or c["chain"]["label"]
    # a run that starts on another connector's path inherits that connector's source
    for c in conns:
        if c["src"] is None:
            for o in conns:
                if o is not c and o["src"] is not None and on_path(c["pts"][0], o):
                    c["src"] = o["src"]
                    break

    # Eraser also keys groups by name: a second "Public subnet" collapses into the first and
    # its contents vanish, so repeated group names get the zone suffix and keep the label
    gcount = {}
    for g in GROUPS:
        gcount[g[5]] = gcount.get(g[5], 0) + 1
    gname, gused = {}, {}
    for key in gbox:
        name = clean(glabel[key])
        if gcount[glabel[key]] > 1:
            tag = None
            for anc in ancestors(gparent.get(key)):
                if re.search(r"zone|region|account", glabel[anc], re.I):
                    tag = clean(glabel[anc]).split()[-1]
                    break
            name = "%s %s" % (name, tag) if tag else name
        if name in gused:
            gused[name] += 1
            name = "%s %d" % (name, gused[name])
        else:
            gused[name] = 1
        gname[key] = name

    lines = ["direction down", ""]
    emitted_groups = set()

    def emit_group(key, depth):
        ind = "  " * depth
        props = ' [label: "%s"]' % clean(glabel[key]) if gname[key] != clean(glabel[key]) else ""
        lines.append("%s%s%s {" % (ind, gname[key], props))
        for i, (icon, cx, y, label, sub) in enumerate(RES):
            if res_group[i] == key:
                emit_res(i, depth + 1)
        for k2 in [g[0] for g in GROUPS]:
            if gparent.get(k2) == key:
                emit_group(k2, depth + 1)
        lines.append("%s}" % ind)
        emitted_groups.add(key)

    def emit_res(i, depth):
        icon, cx, y, label, sub = RES[i]
        props = []
        if icon in ICONS:
            props.append("icon: %s" % ICONS[icon])
        shown = label + (" " + tags[i] if tags[i] else "") + (" - " + sub if sub else "")
        if shown != label:
            props.append('label: "%s"' % clean(shown).replace('"', ""))
        lines.append("%s%s%s" % ("  " * depth, names[i], " [%s]" % ", ".join(props) if props else ""))

    for k in [g[0] for g in GROUPS]:
        if gparent.get(k) is None:
            emit_group(k, 0)
    for i, g in enumerate(res_group):
        if g is None:
            emit_res(i, 0)
    lines.append("")
    skipped = 0
    for c in conns:
        if c["src"] is None or c["dst"] is None or c["src"] == c["dst"]:
            skipped += 1
            continue
        arrow = "-->" if c["dashed"] else ">"
        lab = (": " + clean(c["label"])) if c["label"] else ""
        lines.append("%s %s %s%s" % (names[c["src"]], arrow, names[c["dst"]], lab))
    text = "\n".join(lines) + "\n"
    io.open(out, "w", encoding="utf-8").write(text)
    print("wrote %s  (%d groups, %d nodes, %d connections%s)"
          % (out, len(GROUPS), len(RES), len(conns) - skipped, ", %d unresolved skipped" % skipped if skipped else ""))
    missing = sorted({r[0] for r in RES if r[0] and r[0] not in ICONS})
    if missing:
        print("no Eraser icon mapped for: %s (plain nodes)" % ", ".join(missing))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Export a diagram data file to a native draw.io (.drawio) file.

    python export_drawio.py DATA.py [--out file.drawio]

Same DATA.py as build_diagram.py. Groups become AWS4 group containers with the official
palette, resources become live mxgraph.aws4 shapes (editable, searchable, restylable in
draw.io) and connectors become orthogonal edges with the same waypoints as the PNG, so
the file opens looking like the render. Open it at https://app.diagrams.net or in the
VS Code Draw.io extension. Icons the AWS4 library does not have (GitLab, Argo, people)
become plain rounded boxes with the caption inside.
"""
import argparse, html, io, os, runpy, xml.etree.ElementTree as ET

# our short icon names -> (aws4 resIcon name, category colour, service-level?)
NET, CMP, DB, STO, SEC, MGT, INT, ML = ("#8C4FFF", "#ED7100", "#C925D1", "#7AA116",
                                        "#DD344C", "#E7157B", "#E7157B", "#01A88D")
AWS4 = {
    "route53": ("route_53", NET, 1), "cloudfront": ("cloudfront", NET, 1), "waf": ("waf", SEC, 1),
    "shield": ("shield", SEC, 1), "elb": ("elastic_load_balancing", NET, 1),
    "alb": ("application_load_balancer", NET, 0), "nlb": ("network_load_balancer", NET, 0),
    "nat": ("nat_gateway", NET, 0), "igw": ("internet_gateway", NET, 0), "vpc": ("vpc", NET, 1),
    "transit-gateway": ("transit_gateway", NET, 1), "direct-connect": ("direct_connect", NET, 1),
    "vpn": ("site_to_site_vpn", NET, 1), "endpoint": ("endpoints", NET, 0),
    "privatelink": ("privatelink", NET, 1), "api-gateway": ("api_gateway", NET, 1),
    "global-accelerator": ("global_accelerator", NET, 1),
    "eks": ("eks", CMP, 1), "ecs": ("ecs", CMP, 1), "fargate": ("fargate", CMP, 1),
    "ec2": ("ec2", CMP, 1), "lambda": ("lambda", CMP, 1), "batch": ("batch", CMP, 1),
    "ecr": ("ecr", CMP, 1), "app-runner": ("app_runner", CMP, 1), "beanstalk": ("elastic_beanstalk", CMP, 1),
    "autoscaling": ("auto_scaling2", CMP, 1),
    "rds": ("rds", DB, 1), "rds-mysql": ("rds_mysql_instance", DB, 0),
    "rds-postgres": ("rds_postgresql_instance", DB, 0), "aurora": ("aurora", DB, 1),
    "dynamodb": ("dynamodb", DB, 1), "elasticache": ("elasticache", DB, 1),
    "redshift": ("redshift", DB, 1), "documentdb": ("documentdb_with_mongodb_compatibility", DB, 1),
    "opensearch": ("opensearch_service", ML, 1), "neptune": ("neptune", DB, 1),
    "s3": ("s3", STO, 1), "efs": ("elastic_file_system", STO, 1), "ebs": ("elastic_block_store", STO, 1),
    "backup": ("backup", STO, 1), "glacier": ("s3_glacier", STO, 1), "fsx": ("fsx", STO, 1),
    "secrets": ("secrets_manager", SEC, 1), "kms": ("key_management_service", SEC, 1),
    "iam": ("identity_and_access_management", SEC, 1), "cognito": ("cognito", SEC, 1),
    "acm": ("certificate_manager", SEC, 1), "guardduty": ("guardduty", SEC, 1),
    "security-hub": ("security_hub", SEC, 1), "inspector": ("inspector", SEC, 1), "macie": ("macie", SEC, 1),
    "cloudwatch": ("cloudwatch_2", MGT, 1), "cloudtrail": ("cloudtrail", MGT, 1),
    "config": ("config", MGT, 1), "ssm": ("systems_manager", MGT, 1),
    "cloudformation": ("cloudformation", MGT, 1), "organizations": ("organizations", MGT, 1),
    "grafana": ("managed_service_for_grafana", MGT, 1), "prometheus": ("managed_service_for_prometheus", MGT, 1),
    "sns": ("sns", INT, 1), "sqs": ("sqs", INT, 1), "eventbridge": ("eventbridge", INT, 1),
    "step-functions": ("step_functions", INT, 1), "ses": ("simple_email_service", INT, 1), "mq": ("mq", INT, 1),
    "codebuild": ("codebuild", "#C925D1", 1), "codepipeline": ("codepipeline", "#C925D1", 1),
    "codedeploy": ("codedeploy", "#C925D1", 1), "xray": ("xray", "#E7157B", 1),
    "kinesis": ("kinesis", "#8C4FFF", 1), "msk": ("managed_streaming_for_kafka", "#8C4FFF", 1),
    "glue": ("glue", "#8C4FFF", 1), "athena": ("athena", "#8C4FFF", 1),
    "sagemaker": ("sagemaker", ML, 1), "bedrock": ("bedrock", ML, 1),
    "users": ("users", "#232F3E", 0), "user": ("user", "#232F3E", 0), "client": ("client", "#232F3E", 0),
    "internet": ("internet", "#232F3E", 0), "server": ("traditional_server", "#232F3E", 0),
}

SVC = ("sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],[0,1,0],[0.25,1,0],"
       "[0.5,1,0],[0.75,1,0],[1,1,0],[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],"
       "[1,0.75,0]];outlineConnect=0;fontColor=#232F3E;fillColor={c};strokeColor=#ffffff;"
       "dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=11;"
       "fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{i};")
RSC = ("sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor={c};"
       "strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;"
       "html=1;fontSize=11;fontStyle=0;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.{i};")
PLAIN = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#5A6C86;"
         "fontColor=#232F3E;fontSize=11;verticalAlign=middle;")
GRP = ("sketch=0;outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;"
       "fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;"
       "shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.{g};{gs}strokeColor={s};fillColor={f};"
       "verticalAlign=top;align=left;spacingLeft=30;fontColor={fc};dashed={d};")
RECT = ("rounded=1;whiteSpace=wrap;html=1;container=1;pointerEvents=0;collapsible=0;"
        "recursiveResize=0;fillColor={f};strokeColor={s};dashed={d};verticalAlign=top;"
        "align=left;spacingLeft=6;fontColor={fc};fontSize=12;fontStyle=0;")
EDGE = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;jettySize=auto;orthogonalLoop=1;"
        "strokeColor=#434e5e;strokeWidth=1.5;fontColor=#232F3E;fontSize=10;endArrow={arrow};"
        "endFill={fill};{d}")
LABEL = ("text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=1;"
         "fillColor=#ffffff;strokeColor=none;fontSize=10;fontStyle=1;fontColor=#232F3E;spacing=0;")
ICON = 48   # aws4 icons look right a little larger than the 42 px PNG icons


def group_style(border, dashed, label):
    """map our palette to the AWS4 group shapes draw.io ships"""
    b, low = border.upper(), label.lower()
    if b == "#232F3E":
        return GRP.format(g="group_aws_cloud_alt", gs="", s=b, f="none", fc=b, d=0)
    if b == "#00A4A6" and dashed:
        return GRP.format(g="group_region", gs="", s=b, f="none", fc="#147EBA", d=1)
    if b == "#8C4FFF":
        return GRP.format(g="group_vpc2", gs="", s=b, f="none", fc=b, d=0)
    if b == "#7AA116":
        return GRP.format(g="group_security_group", gs="grStroke=0;", s=b, f="#F2F6E8", fc="#248814", d=0)
    if b == "#00A4A6":
        return GRP.format(g="group_security_group", gs="grStroke=0;", s=b, f="#E6F6F7", fc="#147EBA", d=0)
    if b == "#DD3522":
        return GRP.format(g="group_security_group", gs="grStroke=0;", s=b, f="none", fc=b, d=0)
    return RECT.format(f="none", s=b, d=1 if dashed else 0, fc=b)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--out")
    a = ap.parse_args()
    path = os.path.abspath(a.data)
    d = runpy.run_path(path)
    GROUPS, RES, CONN = d["GROUPS"], d["RES"], d["CONN"]
    title = d.get("TITLE", "architecture")
    out = a.out or os.path.splitext(d.get("OUT", "architecture.png"))[0] + ".drawio"
    out = os.path.join(os.path.dirname(path), out) if not os.path.isabs(out) else out

    cells, n = [], [1]

    def nid():
        n[0] += 1
        return "n%d" % n[0]

    def vertex(style, x, y, w, h, label="", parent="1"):
        i = nid()
        cells.append('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="%s">'
                     '<mxGeometry x="%g" y="%g" width="%g" height="%g" as="geometry"/></mxCell>'
                     % (i, html.escape(label, quote=True).replace("\n", "&#10;"), style, parent, x, y, w, h))
        return i

    # groups, nested by geometric containment (outer first in data order)
    gbox, gid, gparent = {}, {}, {}
    for key, x, y, w, h, label, bc, fc, dashed, ico in GROUPS:
        gbox[key] = (x, y, x + w, y + h)
    for key, x, y, w, h, label, bc, fc, dashed, ico in GROUPS:
        parent, best = "1", None
        for k2, (x0, y0, x1, y1) in gbox.items():
            if k2 != key and x0 <= x and y0 <= y and x1 >= x + w and y1 >= y + h:
                area = (x1 - x0) * (y1 - y0)
                if best is None or area < best:
                    parent, best = k2, area
        gparent[key] = parent
    def origin(key):   # absolute origin of a group's coordinate space (gbox is absolute)
        return (gbox[key][0], gbox[key][1]) if key != "1" else (0, 0)
    for key, x, y, w, h, label, bc, fc, dashed, ico in GROUPS:
        p = gparent[key]
        px, py = origin(p) if p != "1" else (0, 0)
        gid[key] = vertex(group_style(bc, dashed, label), x - px, y - py, w, h, label, gid.get(p, "1"))

    def innermost(px, py):
        best, key = None, "1"
        for k, (x0, y0, x1, y1) in gbox.items():
            if x0 <= px <= x1 and y0 <= py <= y1:
                area = (x1 - x0) * (y1 - y0)
                if best is None or area < best:
                    best, key = area, k
        return key

    # resources
    rid, rbox = [], []
    for icon, cx, y, label, sub in RES:
        text = label + ("\n" + sub if sub else "")
        k = innermost(cx, y + 21)
        ox, oy = origin(k) if k != "1" else (0, 0)
        parent = gid.get(k, "1")
        if icon in AWS4:
            name, colour, svc = AWS4[icon]
            style = (SVC if svc else RSC).format(c=colour, i=name)
            i = vertex(style, cx - ICON / 2 - ox, y - 3 - oy, ICON, ICON, text, parent)
        else:
            i = vertex(PLAIN, cx - 80 - ox, y - 4 - oy, 160, 50, text, parent)
        rid.append(i)
        rbox.append((cx - 21, y, cx + 21, y + 42))

    def anchor(pt):
        """resource whose icon-plus-caption block the point touches, and the exit/entry
        fraction on the icon; a fan-out that starts under a caption still attaches"""
        best = None
        for i, (x0, y0, x1, y1) in zip(rid, rbox):
            if x0 - 14 <= pt[0] <= x1 + 14 and y0 - 14 <= pt[1] <= y1 + 52:
                dist = abs(pt[0] - (x0 + x1) / 2) + abs(pt[1] - (y0 + y1) / 2)
                if best is None or dist < best[0]:
                    fx = min(1, max(0, (pt[0] - x0) / (x1 - x0)))
                    fy = min(1, max(0, (pt[1] - y0) / (y1 - y0)))
                    best = (dist, i, fx, fy)
        return best[1:] if best else (None, None, None)

    # connectors
    for conn in CONN:
        pts, dashed, lab, lp = conn[:4]
        arrow = conn[4] if len(conn) > 4 else 1
        src, sx, sy = anchor(pts[0])
        dst, tx, ty = anchor(pts[-1])
        st = EDGE.format(arrow="blockThin" if arrow else "none", fill=1 if arrow else 0,
                         d="dashed=1;" if dashed else "")
        if src:
            st += "exitX=%g;exitY=%g;exitDx=0;exitDy=0;" % (sx, sy)
        if dst:
            st += "entryX=%g;entryY=%g;entryDx=0;entryDy=0;" % (tx, ty)
        geo = '<mxGeometry relative="1" as="geometry">'
        if not src:
            geo += '<mxPoint x="%g" y="%g" as="sourcePoint"/>' % pts[0]
        if not dst:
            geo += '<mxPoint x="%g" y="%g" as="targetPoint"/>' % pts[-1]
        inner = pts[1:-1]
        if inner:
            geo += '<Array as="points">' + "".join('<mxPoint x="%g" y="%g"/>' % p for p in inner) + "</Array>"
        geo += "</mxGeometry>"
        i = nid()
        attrs = ' source="%s"' % src if src else ""
        attrs += ' target="%s"' % dst if dst else ""
        cells.append('<mxCell id="%s" value="" style="%s" edge="1" parent="1"%s>%s</mxCell>' % (i, st, attrs, geo))
        if lab and lp:
            w = len(lab) * 6.2 + 16
            vertex(LABEL, lp[0] - w / 2, lp[1] - 9, w, 18, lab)

    xml = ('<mxfile host="app.diagrams.net" type="device"><diagram id="d1" name="%s">'
           '<mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
           'arrows="1" fold="1" page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0">'
           '<root><mxCell id="0"/><mxCell id="1" parent="0"/>%s</root></mxGraphModel></diagram></mxfile>'
           % (html.escape(title, quote=True), d.get("W", 1900) + 100, d.get("H", 1200) + 100, "".join(cells)))
    ET.fromstring(xml)   # raises if the XML is malformed
    io.open(out, "w", encoding="utf-8").write(xml)
    missing = sorted({r[0] for r in RES if r[0] and r[0] not in AWS4})
    print("wrote %s  (%d cells)" % (out, len(cells)))
    if missing:
        print("no AWS4 shape for %s: drawn as plain boxes" % ", ".join(missing))


if __name__ == "__main__":
    main()

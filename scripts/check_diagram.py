#!/usr/bin/env python3
"""Collision audit for a diagram data file used with build_diagram.py.

    python check_diagram.py DATA.py [--calibrate]

Rebuilds the boxes Chrome draws (icons, captions, group labels, connector label chips) from
the same data and reports every collision with a connector or another box. Text widths come
from the real font when available (Segoe UI Bold, then Arial Bold, then DejaVu Sans Bold),
otherwise from a per-character estimate. Exit code is the number of findings, capped at 99.

Findings, and the rule behind each:
  label-on-border      a chip covers a group border (use a different point on the line)
  label-on-text        a chip overlaps a caption or another chip
  label-on-icon        a chip touches an icon
  label-hides-line     a chip sits over a line that is not its own
  line-through-text    a segment crosses a caption or a group label
  line-through-icon    a segment passes through an icon it does not start or end at
  floating-end         an endpoint is not near an icon, a caption block or another line
  lines-too-close      two parallel runs under 14 px apart for more than 20 px
  line-on-border       a run lies within 6 px of a border it is parallel to
  lines-cross          two connectors cross (list accepted pairs in ACCEPTED_CROSSINGS)
  grouplabel-on-icon   a group label overlaps an icon
"""
import argparse, itertools, os, runpy, sys

CHIP_PAD, CHIP_H = 20, 19          # white chip: 9 px padding each side plus 2 px safety, 19 px tall
GL_H, GL_PAD, GL_CHIP = 18, 14, 20  # group label: 5 px padding each side plus 4 px safety, 13 px chip + 7 px gap
CAP_Y0, CAP_Y1, SUB_Y1 = 48, 64, 79  # caption rows relative to the icon top
ICON = 42


def load_data(path):
    d = runpy.run_path(os.path.abspath(path))
    return d


def get_font(size, bold=True):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    names = (["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"] if bold
             else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "Arial.ttf"])
    dirs = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"), "/usr/share/fonts",
            "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "/System/Library/Fonts/Supplemental", ""]
    for n in names:
        for d in dirs:
            p = os.path.join(d, n) if d else n
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return None


FONTS = {}


def text_w(s, size, bold=True, spacing=0.0):
    key = (size, bold)
    if key not in FONTS:
        FONTS[key] = get_font(size, bold)
    f = FONTS[key]
    if f is None:
        w = len(s) * size * (0.62 if bold else 0.55)
    else:
        w = f.getlength(s)
    return w * (1 + spacing)


def boxes(d):
    GROUPS_D, RES, CONN = d["GROUPS"], d["RES"], d["CONN"]
    straddle = set(d.get("STRADDLE", ()))
    labels = []          # (text, box, owner index)
    for i, c in enumerate(CONN):
        if c[2] and c[3]:
            w = text_w(c[2], 11.5) + CHIP_PAD
            cx, cy = c[3]
            labels.append((c[2], [cx - w / 2, cy - CHIP_H / 2, cx + w / 2, cy + CHIP_H / 2], i))
    groups = [(g[5], [g[1], g[2], g[1] + g[3], g[2] + g[4]], g[0]) for g in GROUPS_D]
    glabels = []
    for key, x, y, w, h, label, bc, fc, dashed, ico in GROUPS_D:
        lw = text_w(label, 12, spacing=0.03) + GL_PAD + (GL_CHIP if ico else 0)
        top = y - 9 if key in straddle else y + 7
        glabels.append((label, [x + 5, top, x + 5 + lw, top + GL_H], key))
    icons = [(r[3], [r[1] - ICON / 2, r[2], r[1] + ICON / 2, r[2] + ICON]) for r in RES]
    captions = []
    for icon, cx, y, label, sub in RES:
        w = text_w(label, 12.5)
        captions.append((label, [cx - w / 2, y + CAP_Y0, cx + w / 2, y + CAP_Y1]))
        if sub:
            w = text_w(sub, 11, bold=False)
            captions.append((sub, [cx - w / 2, y + CAP_Y1 + 1, cx + w / 2, y + SUB_Y1]))
    paths = []
    for i, c in enumerate(CONN):
        pts = c[0]
        paths.append({"i": i, "pts": pts, "segs": list(zip(pts, pts[1:])),
                      "name": c[2] or "unlabelled#%d" % i})
    return labels, groups, glabels, icons, captions, paths


def seg_hits_box(a, b, box, pad=0):
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    (ax, ay), (bx, by) = a, b
    if ax == bx:
        return x0 <= ax <= x1 and max(ay, by) >= y0 and min(ay, by) <= y1
    if ay == by:
        return y0 <= ay <= y1 and max(ax, bx) >= x0 and min(ax, bx) <= x1
    return False


def near_box(pt, box, tol):
    return box[0] - tol <= pt[0] <= box[2] + tol and box[1] - tol <= pt[1] <= box[3] + tol


def edges(box):
    x0, y0, x1, y1 = box
    return [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]


def overlap(a, b, pad=0):
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])


def parallel_gap(s1, s2):
    (a, b), (c, d) = s1, s2
    if a[0] == b[0] and c[0] == d[0]:
        lo, hi = max(min(a[1], b[1]), min(c[1], d[1])), min(max(a[1], b[1]), max(c[1], d[1]))
        return abs(a[0] - c[0]), hi - lo
    if a[1] == b[1] and c[1] == d[1]:
        lo, hi = max(min(a[0], b[0]), min(c[0], d[0])), min(max(a[0], b[0]), max(c[0], d[0]))
        return abs(a[1] - c[1]), hi - lo
    return None, None


def crossing(s1, s2, tol=2):
    """point where a horizontal and a vertical segment cross strictly inside both, or None"""
    (a, b), (c, d) = s1, s2
    if a[1] == b[1] and c[0] == d[0]:
        h, v = (a, b), (c, d)
    elif a[0] == b[0] and c[1] == d[1]:
        h, v = (c, d), (a, b)
    else:
        return None
    y, x = h[0][1], v[0][0]
    hx0, hx1 = sorted((h[0][0], h[1][0]))
    vy0, vy1 = sorted((v[0][1], v[1][1]))
    if hx0 + tol < x < hx1 - tol and vy0 + tol < y < vy1 - tol:
        return (x, y)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--calibrate", action="store_true", help="print measured chip widths and exit")
    a = ap.parse_args()
    d = load_data(a.data)
    labels, groups, glabels, icons, captions, paths = boxes(d)
    accepted = {tuple(sorted(p)) for p in d.get("ACCEPTED_CROSSINGS", ())}

    if a.calibrate:
        print("font:", FONTS.get((11.5, True)) and FONTS[(11.5, True)].path or "estimate")
        for t, b, _ in labels:
            print("  %-30s chip %3d x %d px" % (t, round(b[2] - b[0]), CHIP_H))
        for t, b, _ in glabels:
            print("  %-30s group label %3d px" % (t, round(b[2] - b[0])))
        return

    text = [(t, b, "label") for t, b, _ in labels] + [(t, b, "grouplabel") for t, b, _ in glabels] \
        + [(t, b, "caption") for t, b in captions]
    straddle = set(d.get("STRADDLE", ()))
    straddle_labels = {t for t, b, k in glabels if k in straddle}
    F = []
    flag = lambda kind, msg: F.append((kind, msg))
    short = lambda g: g.split("  ")[0]

    # 1. connector label chips
    for t, box, owner in labels:
        for gname, gbox, _ in groups:
            if any(seg_hits_box(p, q, box) for p, q in edges(gbox)):
                flag("label-on-border", "'%s' chip covers the %s border" % (t, short(gname)))
        for t2, b2, kind in text:
            if b2 is box:
                continue
            if overlap(box, b2):
                flag("label-on-text", "'%s' chip overlaps %s '%s'" % (t, kind, t2))
        for name, ib in icons:
            if overlap(box, ib, pad=4):
                flag("label-on-icon", "'%s' chip touches icon %s" % (t, name))
        own = paths[owner]["segs"]
        for p in paths:
            if p["i"] == owner:
                continue
            shared = lambda p1, q1: any(p1[1] == q1[1] == c[1] == e[1] or p1[0] == q1[0] == c[0] == e[0]
                                        for c, e in own)
            if any(seg_hits_box(p1, q1, box) and not shared(p1, q1) for p1, q1 in p["segs"]):
                flag("label-hides-line", "'%s' chip sits over the %s line" % (t, p["name"]))

    # 2. lines through text or icons
    for p in paths:
        for p1, q1 in p["segs"]:
            for t, b, kind in text:
                if kind == "label" or (kind == "grouplabel" and t in straddle_labels):
                    continue
                if seg_hits_box(p1, q1, b):
                    flag("line-through-text", "%s line crosses %s '%s'" % (p["name"], kind, t))
            for name, ib in icons:
                if seg_hits_box(p1, q1, ib, pad=-1):
                    if not (near_box(p["pts"][0], ib, 12) or near_box(p["pts"][-1], ib, 12)):
                        flag("line-through-icon", "%s line passes through icon %s" % (p["name"], name))

    # 3. endpoints that touch nothing
    anchors = icons + [(t, b) for t, b in captions]
    for p in paths:
        for which, pt in (("start", p["pts"][0]), ("end", p["pts"][-1])):
            on_line = any(seg_hits_box(p1, q1, [pt[0], pt[1], pt[0], pt[1]], 2)
                          for q in paths if q["i"] != p["i"] for p1, q1 in q["segs"])
            if not (any(near_box(pt, b, 12) for _, b in anchors) or on_line):
                flag("floating-end", "%s %s at %s touches nothing" % (p["name"], which, pt))

    # 4. parallel runs too close, runs on a border, crossings
    seen = set()
    for p, q in itertools.combinations(paths, 2):
        for s1 in p["segs"]:
            for s2 in q["segs"]:
                gap, ov = parallel_gap(s1, s2)
                if gap is not None and 0 < gap < 14 and ov > 20 and (p["name"], q["name"], gap) not in seen:
                    seen.add((p["name"], q["name"], gap))
                    flag("lines-too-close", "%s and %s run %dpx apart for %dpx" % (p["name"], q["name"], gap, ov))
                x = crossing(s1, s2)
                if x and tuple(sorted((p["name"], q["name"]))) not in accepted:
                    flag("lines-cross", "%s crosses %s at %s" % (p["name"], q["name"], x))
    for p in paths:
        for s1 in p["segs"]:
            for gname, gbox, _ in groups:
                for e in edges(gbox):
                    gap, ov = parallel_gap(s1, e)
                    if gap is not None and gap < 6 and ov > 20:
                        flag("line-on-border", "%s runs %dpx from the %s border for %dpx"
                             % (p["name"], gap, short(gname), ov))

    # 5. group labels over icons
    for t, b, _ in glabels:
        for name, ib in icons:
            if overlap(b, ib):
                flag("grouplabel-on-icon", "group label '%s' overlaps icon %s" % (t, name))

    F.sort()
    for kind, msg in F:
        print("%-20s %s" % (kind, msg))
    print("--", len(F), "findings")
    sys.exit(min(len(F), 99))


if __name__ == "__main__":
    main()

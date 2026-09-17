#!/usr/bin/env python3
"""Render an architecture diagram described in a Python data file to a PNG.

    python build_diagram.py DATA.py [--out file.png] [--scale 2] [--margin 28] [--no-shot]

DATA.py defines GROUPS, RES, CONN and optionally TITLE, SUBTITLE, W, H, ICON_DIR, OUT,
STRADDLE (see SKILL.md). Paths in the data file are relative to the data file. The script
writes _layout.html next to the data file, screenshots it with Chrome headless at the
device scale factor, crops to the content plus a margin, and writes the PNG.
"""
import argparse, base64, io, os, runpy, subprocess, sys


def load_data(path):
    path = os.path.abspath(path)
    d = runpy.run_path(path)
    cfg = {
        "TITLE": d.get("TITLE", ""), "SUBTITLE": d.get("SUBTITLE", ""),
        "W": d.get("W", 1900), "H": d.get("H", 1200),
        "ICON_DIR": d.get("ICON_DIR", "icons-aws"), "OUT": d.get("OUT", "architecture.png"),
        "STRADDLE": set(d.get("STRADDLE", ())),
        "GROUPS": d["GROUPS"], "RES": d["RES"], "CONN": d["CONN"],
        "ACCEPTED_CROSSINGS": set(d.get("ACCEPTED_CROSSINGS", ())),
        "_dir": os.path.dirname(path),
    }
    return cfg


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def find_chrome():
    env = os.environ.get("CHROME")
    if env and os.path.exists(env):
        return env
    cands = []
    if sys.platform.startswith("win"):
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                     os.environ.get("LOCALAPPDATA")):
            if base:
                cands.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
                cands.append(os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"))
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    else:
        cands += ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium",
                  "/usr/bin/chromium-browser", "/snap/bin/chromium"]
    for c in cands:
        if os.path.exists(c):
            return c
    sys.exit("Chrome not found; set CHROME=/path/to/chrome")


def render_html(cfg):
    icons = {}
    idir = os.path.join(cfg["_dir"], cfg["ICON_DIR"])
    if os.path.isdir(idir):
        for n in os.listdir(idir):
            if n.lower().endswith(".png"):
                icons[n[:-4]] = "data:image/png;base64," + base64.b64encode(
                    open(os.path.join(idir, n), "rb").read()).decode()
    missing = sorted({r[0] for r in cfg["RES"] if r[0] and r[0] not in icons})

    groups = ""
    for key, x, y, w, h, label, bc, fc, dashed, ico in cfg["GROUPS"]:
        style = "dashed" if dashed else "solid"
        chip = '<span class="gi" style="background:%s"></span>' % bc if ico else ""
        top = -9 if key in cfg["STRADDLE"] else 7
        groups += ('<div class="grp" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;border:2px %s %s">'
                   '<span class="gl" style="color:%s;top:%dpx">%s%s</span></div>'
                   % (x, y, w, h, style, bc, fc, top, chip, esc(label)))

    res = ""
    for icon, cx, y, label, sub in cfg["RES"]:
        img = '<img src="%s"/>' % icons[icon] if icon in icons else '<span class="noico"></span>'
        s2 = '<div class="rs">%s</div>' % esc(sub) if sub else ""
        res += ('<div class="res" style="left:%dpx;top:%dpx">%s<div class="rl">%s</div>%s</div>'
                % (cx - 90, y, img, esc(label), s2))

    paths, labels = "", ""
    for conn in cfg["CONN"]:
        pts, dashed, lab, lp = conn[:4]
        arrow = conn[4] if len(conn) > 4 else 1
        d = "M " + " L ".join("%s,%s" % (x, y) for x, y in pts)
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        head = ' marker-end="url(#a)"' if arrow else ""
        paths += ('<path d="%s" fill="none" stroke="#434e5e" stroke-width="1.7" stroke-linejoin="round"%s%s/>'
                  % (d, dash, head))
        if lab and lp:
            labels += '<div class="el" style="left:%dpx;top:%dpx">%s</div>' % (lp[0], lp[1], esc(lab))

    head_html = ""
    if cfg["TITLE"]:
        head_html += "<h1>%s</h1>" % esc(cfg["TITLE"])
    if cfg["SUBTITLE"]:
        head_html += '<div class="sb">%s</div>' % cfg["SUBTITLE"]   # may contain <br>

    html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}
body{margin:0;background:#fff;font-family:"Segoe UI",Inter,Arial,sans-serif;-webkit-font-smoothing:antialiased}
#c{position:relative;width:%(W)dpx;height:%(H)dpx}
svg{position:absolute;inset:0;width:100%%;height:100%%;z-index:2}
.grp{position:absolute;background:none;border-radius:4px}
.gl{position:absolute;top:7px;left:10px;display:flex;align-items:center;gap:7px;
     font-size:12px;font-weight:700;letter-spacing:.03em;white-space:nowrap;
     background:#fff;padding:1px 5px;border-radius:2px;z-index:5}
.gi{width:13px;height:13px;border-radius:2px;display:inline-block;opacity:.85}
.res{position:absolute;width:180px;text-align:center;z-index:3}
.res img{width:42px;height:42px;display:block;margin:0 auto}
.noico{display:block;width:42px;height:42px;margin:0 auto;border:1.6px solid #5A6C86;border-radius:5px}
.rl{font-size:12.5px;font-weight:700;color:#232f3e;margin-top:6px;line-height:1.25;
     text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff,0 0 3px #fff}
.rs{font-size:11px;color:#4a5568;line-height:1.3;margin-top:1px;
     text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff,0 0 3px #fff}
.el{position:absolute;z-index:4;transform:translate(-50%%,-50%%);background:#fff;padding:2px 9px;
     font-size:11.5px;color:#232f3e;border-radius:3px;white-space:nowrap;font-weight:700}
h1{font:700 19px "Segoe UI",Inter,Arial,sans-serif;margin:0;padding:26px 0 0 40px;color:#151d2b}
.sb{font:400 12.5px "Segoe UI",Inter,Arial,sans-serif;color:#4b5563;padding:4px 0 0 40px}
</style></head><body>
%(head)s
<div id="c">
%(groups)s
<svg><defs><marker id="a" viewBox="0 0 10 10" refX="9.5" refY="5" markerWidth="5.5"
 markerHeight="5.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#434e5e"/>
</marker></defs>%(paths)s</svg>
%(res)s%(labels)s
</div></body></html>""" % {"W": cfg["W"], "H": cfg["H"], "head": head_html, "groups": groups,
                              "paths": paths, "res": res, "labels": labels}
    return html, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--out", help="output PNG (default: OUT in the data file)")
    ap.add_argument("--scale", type=float, default=2.0, help="device scale factor (default 2)")
    ap.add_argument("--margin", type=int, default=28, help="white margin around the content in canvas px")
    ap.add_argument("--no-shot", action="store_true", help="write _layout.html only")
    a = ap.parse_args()

    cfg = load_data(a.data)
    html, missing = render_html(cfg)
    html_path = os.path.join(cfg["_dir"], "_layout.html")
    io.open(html_path, "w", encoding="utf-8").write(html)
    print("wrote %s  (%d groups, %d resources, %d connectors)"
          % (html_path, len(cfg["GROUPS"]), len(cfg["RES"]), len(cfg["CONN"])))
    if missing:
        print("WARNING: no icon PNG for: %s  (placeholder boxes drawn; run fetch_icons.py)" % ", ".join(missing))
    if a.no_shot:
        return

    from PIL import Image, ImageChops
    out = os.path.abspath(os.path.join(cfg["_dir"], a.out or cfg["OUT"]))
    shot = os.path.join(cfg["_dir"], "_shot.png")
    src = "file:///" + html_path.replace(os.sep, "/")
    head_h = 120 if (cfg["TITLE"] or cfg["SUBTITLE"]) else 0
    subprocess.run([find_chrome(), "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=%g" % a.scale,
                    "--window-size=%d,%d" % (cfg["W"], cfg["H"] + head_h + 40),
                    "--screenshot=" + shot, src], check=True, capture_output=True, timeout=180)
    im = Image.open(shot).convert("RGB")
    mask = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255)))
    bb = mask.convert("L").point(lambda v: 255 if v > 8 else 0).getbbox()
    m = int(a.margin * a.scale)
    im.crop((max(0, bb[0] - m), max(0, bb[1] - m),
             min(im.width, bb[2] + m), min(im.height, bb[3] + m))).save(out)
    os.remove(shot)
    print("wrote %s  %dx%d" % (out, *Image.open(out).size))


if __name__ == "__main__":
    main()

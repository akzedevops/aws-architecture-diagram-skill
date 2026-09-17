---
name: aws-architecture-diagram
description: Draw a clean, print-ready AWS architecture diagram (network boundaries, availability zones, subnets, security groups, official AWS icons, labelled connectors) as a PNG from a small Python data file, rendered with Chrome and audited by a geometry checker so no line crosses text, no label sits on a border and no connector floats. Use this whenever the user wants an architecture, target-state, infrastructure, cloud, VPC, network or deployment diagram for AWS (or a mostly-AWS system with GitLab, Argo CD or Kubernetes parts), whether for a proposal, a submission, a design doc, a README or a slide, even if they only say "draw the setup" or "show how traffic flows". Also use it to change or fix an existing diagram built this way.
---

# AWS architecture diagram

The diagram is data, not a drawing. A Python file lists groups (cloud, region, VPC, zones,
subnets, security groups), resources (icon, position, caption) and connectors (polyline,
dashed or solid, label). One script renders that to HTML with the official AWS icon set and
the AWS group palette and screenshots it with Chrome at 2x. A second script audits the same
data for collisions. You edit numbers, run both, and only look at the picture when the
checker is at zero findings. Eyeballing a 3700 px image misses things; the checker does not.

Scripts live in `scripts/` next to this file. Read `references/conventions.md` before laying
out anything: it holds the palette, the spacing rules and the lessons that cost a day.

## Workflow

1. **Agree the content first.** List every group, resource and flow the diagram must show.
   Ask what the reader must be able to see (boundaries, zones, where data lives, how traffic
   reaches the app, how deploys happen) and what to leave out. One icon per concept, one
   caption line each; a second small line for the detail that matters (size, mode, count).
   Resist adding: the checker gets harder to satisfy with every resource, and a reader gets
   nothing from the tenth arrow.

2. **Start from the template.** Copy `assets/template_diagram.py` into the project as
   `diagram.py` (any name). It is a complete small two-zone web app that builds cleanly.

3. **Fetch icons.** `python <skill>/scripts/fetch_icons.py --dir icons-aws eks rds s3 ...`
   copies PNGs out of the `diagrams` package (`pip install diagrams`) under short names.
   `--list kube` searches the whole icon tree when a short name does not exist. Icons render
   at 42 px; the caption sits under them, so no cards, no boxes around icons.

4. **Lay out groups on a grid**, outermost first: cloud, region, VPC, zones side by side,
   public subnet row above private subnet row, security groups around the data tier.
   Leave gutters (30 px or more) between nested borders so connectors have lanes to run in.

5. **Place resources.** `x` is the icon centre, `y` the icon top. Rows 110 to 130 px apart
   leave room for two caption lines. Put the things that talk to each other in the same
   column or row so connectors are straight.

6. **Draw connectors** as orthogonal polylines from an icon edge (8 to 10 px off it) to
   another icon edge. Solid for request or data flow, dashed for control and replication.
   Give each a short label placed on the line as a white chip, or beside a vertical run.
   Long cross-diagram lines go in lanes: the gutter between borders, above the region,
   below the zones. See the lane rules in the conventions file.

7. **Build and check, in that order, every time:**
   ```
   python <skill>/scripts/build_diagram.py diagram.py
   python <skill>/scripts/check_diagram.py diagram.py
   ```
   The checker prints one line per finding: label on a border, label over text, line through
   an icon or caption, endpoint touching nothing, parallel runs under 14 px apart, a run
   lying on a border, and two connectors crossing. Fix the data, rebuild, re-check. Zero is
   the bar. Crossings you decide to keep go in `ACCEPTED_CROSSINGS` in the data file with a
   comment saying why.

8. **Then look.** Open the PNG, or crop regions with PIL at 100%, and read it as the audience
   will: can a non-technical reader follow the request path, can an engineer see where the
   database is and what replicates to what. Check the chip text is legible at the size the
   diagram will be printed. A4 portrait at full width makes 11.5 px text about 3.5 pt, so
   prefer landscape or a half-page crop if the image must be small.

9. **Embed the PNG; export copies from the same data.** The PNG is what ships. When an
   editable or shared copy is wanted, run an exporter on the same data file rather than
   redrawing, and regenerate after every change; a hand-edited copy drifts immediately.
   - `export_drawio.py diagram.py` writes a native `.drawio` with live AWS4 shapes, the
     same groups, routes and labels. Opens at app.diagrams.net or in the VS Code Draw.io
     extension. Non-AWS icons (GitLab, Argo, people) become plain boxes.
   - `export_eraser.py diagram.py` writes Eraser diagram-as-code (`.eraser`). With the
     Eraser MCP connected: `create_file`, then `manually_create_diagram` with diagramType
     `cloud-architecture-diagram` and the text as `code`, then `export_diagram` for a PNG.
     Eraser lays out on its own, so expect a tall top-down picture, not the PNG's lanes.
   - `export_figma.py diagram.py` writes `_figma/figma_step1.js`. Load the `figma-use`
     skill, run the script through `use_figma`, take `rootId` from the result, rerun with
     `--root <id>` to get `figma_step2.js`, run that too, then `upload_assets` the icon
     PNGs onto the placeholder nodes in `icon_order.txt` order. Two calls minimum.
   - `export_mermaid.py diagram.py` writes an `architecture-beta` block for READMEs and
     wikis: stock icons only, no edge labels, Mermaid's own layout.

## What the build does

`build_diagram.py DATA.py [--out file.png] [--scale 2] [--margin 28] [--no-shot]`

- Loads `DATA.py`, resolves `ICON_DIR` and `OUT` relative to it.
- Writes `_layout.html` next to the data file, then screenshots it with Chrome headless at
  the device scale factor, crops to the content plus the margin, and writes the PNG.
- Warns for every resource whose icon PNG is missing and draws a bordered placeholder box
  instead, which is also the right look for things outside AWS (shoppers, a payment gateway).
- Finds Chrome on Windows, macOS and Linux; set `CHROME=/path/to/chrome` to override.

## What the checker does

`check_diagram.py DATA.py [--calibrate]`

Measures every label with the real font (Segoe UI or Arial bold, falling back to a
per-character estimate), rebuilds the boxes Chrome will draw, and tests them against each
other and against every connector segment. `--calibrate` prints the measured chip widths so
you can compare with `getBoundingClientRect()` in a browser if a font differs. The rules it
enforces and why they exist are in `references/conventions.md`.

## Data file format

```python
TITLE, SUBTITLE = "Client  ·  target-state architecture", "line one<br>line two"
W, H = 1900, 1200                 # canvas in CSS px; the PNG is 2x that, cropped
ICON_DIR, OUT = "icons-aws", "architecture.png"
STRADDLE = {"sg-a"}               # group keys whose label sits on the top border
ACCEPTED_CROSSINGS = set()        # {("label a", "label b")} pairs you decided to keep
GROUPS = [(key, x, y, w, h, label, border_colour, label_colour, dashed, chip), ...]
RES    = [(icon_name_or_None, centre_x, top_y, label, sublabel), ...]
CONN   = [(points, dashed, label, (label_x, label_y)), ...]   # 5th item 0 = no arrowhead
```

Unlabelled connectors use `""` and `None`. A 5th tuple item of `0` draws a run with no
arrowhead, for a shared trunk that several arrows join.

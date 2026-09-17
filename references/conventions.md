# Conventions and lessons

Everything here was learned on a real 27-resource, three-zone production diagram that
went through four rounds of visual review before a checker replaced the eyeballing. The rules exist because each one was broken once and a reader noticed.

## Palette and group styling (AWS Architecture Icons "group" set)

| Group | Border | Style | Label colour | Chip |
|---|---|---|---|---|
| AWS Cloud | `#232F3E` | solid | `#232F3E` | yes |
| Region | `#00A4A6` | dashed | `#147EBA` | yes |
| Availability Zone | `#147EBA` | dashed | `#147EBA` | no |
| VPC | `#8C4FFF` | solid | `#8C4FFF` | yes |
| Public subnet | `#7AA116` | solid | `#248814` | yes |
| Private subnet | `#00A4A6` | solid | `#147EBA` | yes |
| Security group | `#DD3522` | solid | `#DD3522` | yes |
| Anything outside AWS (delivery, on-prem) | `#5A6C86` | dashed | `#5A6C86` | no |

All groups are transparent, 2 px borders, 4 px radius. Labels are 12 px bold, letter-spaced
3%, on a white plate so a line passing under the label is hidden rather than struck through.
Red is the standard colour for a security group; readers who know the icon set expect it.

Resources are bare 42 px icons with a 12.5 px bold caption and an optional 11 px grey
sub-caption, centred in a 180 px block. No cards, no boxes, no shadows. Things that are not
AWS services and have no icon (shoppers, a payment gateway) are a 42 px rounded outline box.

Connectors: `#434e5e`, 1.7 px, round joins, `5 4` dash for control and replication flows,
solid for request and data flows. Arrowhead 5.5 px at the end. Labels are 11.5 px bold on a
white chip with 9 px side padding, centred on the point you give.

## Spacing rules the checker enforces

- **Endpoints touch something.** Start and end within 12 px of an icon edge or its caption
  block, or on another connector's segment (a fan-out trunk). A floating end reads as a
  mistake even when the reader can guess.
- **Connectors leave 8 to 10 px off the icon edge.** Start at `edge ± 10`. On the target
  side end at `edge - 4` so the arrowhead tip meets the icon.
- **Lines never enter an icon or a caption box** except at their own ends.
- **Parallel runs stay 14 px apart or more.** Closer than that, the dash patterns merge and
  two flows read as one thick line. 20 to 30 px between lanes is comfortable.
- **Nothing runs along a border** closer than 6 px. Lines should cross borders at right
  angles, never ride them.
- **Label chips never cover a border, another chip, a caption or a foreign line.** A chip on
  its own line is fine; that is the point of the white plate.
- **Group labels never overlap an icon.** Leave the top-left 220 x 30 px of every group
  empty.
- **Two connectors do not cross.** Route around; swap two rows in a column; give the second
  line a different lane. When a crossing is genuinely unavoidable, list the pair in
  `ACCEPTED_CROSSINGS` with a comment, so the next person knows it was a decision.

## Layout patterns that work

- **Columns.** Edge services (Route 53, CloudFront, WAF) in a row above the region. The
  load balancer centred above the zones, fanning out with one trunk and one arrowhead per
  zone. Data stores under the compute in each zone. A right-hand column outside the VPC
  for regional services (S3, Backup, ECR, Secrets, CloudWatch, SNS, GuardDuty). A left-hand
  column outside the cloud for people, monitors and delivery (GitLab, CI, deploy repo).
- **Lanes.** Cross-diagram lines need a corridor with nothing in it. The good ones: the
  gutter between the region border and the VPC border (left and right), the strip between
  the AWS Cloud label row and the top of the region, and the strips between the zone
  bottoms, the VPC bottom and the region bottom. Give each long line its own lane, 27 px or
  more from the next, and enter the target from the side that has no other line.
- **Straddle security-group labels.** A security group box around two 180 px resources is
  about 236 px wide and its label fills it. Inside the box the label blocks the only column
  an inbound connector can use, so put it on the top border (`STRADDLE`) like draw.io does.
- **Replication pairs** (RDS primary and standby, cache primary and replica) sit on the same
  row in adjacent zones with one horizontal arrow between them, labelled with what the
  reader must know: `RPO ~ 0` for synchronous, `async copy` for asynchronous.
- **Pods in every zone but a writer in one.** Draw the storefront tier in all zones and the
  database pair in two. Say in the caption that the single writer is in zone a; a reader
  will otherwise assume the third zone has no database by accident.
- **Order the right-hand column by connector geometry, not by importance.** A line that
  arrives from below and wraps up the right side walls off every row it passes. Put the
  resource that must be reached from outside (ECR, fed by CI) above the one that is reached
  from below (Backup, fed by the daily snapshot), and the push arrow arrives clean.

## Lessons

- **Build the checker before the third round of eyeballing.** The first run of the audit on
  a diagram that three visual passes had approved found six defects: two chips over foreign
  lines, a line through a caption, a stub that stopped 40 px short, two parallel runs 8 px
  apart. Reviewing 2x crops one by one is slow and still misses things.
- **Measure, do not estimate, when you can.** Chip widths from the real font beat character
  counts; the checker uses Segoe UI Bold when it is installed, Arial Bold otherwise, and only
  then falls back to an estimate. `--calibrate` prints what it measured.
- **A white label plate needs the right stacking context.** If the group `div` has its own
  `z-index`, the label's plate ends up below the SVG and the line shows through it. The
  group has no `z-index`; the label has `z-index: 5`, above the SVG at 2.
- **The PNG is the only source that ships.** Draw.io, Figma and Eraser copies generated
  from the data are for walkthroughs. The moment someone edits one by hand it drifts, and
  the next build overwrites nothing there. Regenerate copies from data; never sync back.
- **A control-plane arrow to the cluster is easy to forget.** CI pushes to the registry,
  the GitOps controller pulls desired state, the nodes pull images. Draw all three, and the
  controller's arrow into the workloads. Reviewers asked "how does Argo deploy" and "how
  does ECR get the image" on a diagram that had only the pull.
- **Say where a shared component runs.** A GitOps controller drawn once inside zone c looks
  pinned there. Caption it `any zone` or the reader assumes a single point of failure.
- **Two builds are not chained.** If the PNG is embedded in a PDF or doc, rebuild that after
  the PNG. Compare timestamps when unsure; a stale embed has shipped before.
- **Keep the data honest with the prose.** Every count in a caption (three zones, one NAT
  per zone, 2 to 20 pods, 180 GB) must match the document it sits in. Grep for the figure
  in both before sending.

## Print size

At 2x the canvas is about 3700 x 2500 px. Embedded across an A4 portrait text width
(170 mm) the 11.5 px chips print at roughly 3.5 pt, readable on screen when zoomed and
marginal on paper. If the diagram must be small, use a landscape page, a wider canvas
with fewer resources, or larger fonts in `build_diagram.py` (then recalibrate the checker's
font sizes to match).

# Starter data file for build_diagram.py / check_diagram.py. Builds at zero findings.
# A two-zone web application: CloudFront and WAF at the edge, an ALB above the zones, app
# containers in the private subnets, RDS Multi-AZ inside security groups, S3 and CloudWatch
# in a regional column outside the VPC. Copy this next to your project, rename, edit.
#
# Coordinates are CSS px on a W x H canvas; the PNG is rendered at 2x.
# GROUPS: (key, x, y, w, h, label, border colour, label colour, dashed, colour chip)
# RES:    (icon name in ICON_DIR or None, icon centre x, icon top y, label, sub-label)
# CONN:   (points, dashed, label, (label x, label y)[, arrow])   arrow 0 = no arrowhead
# Connectors start 10 px off an icon edge and end 4 px before the target edge.

TITLE = "Example Shop  ·  target-state architecture"
SUBTITLE = "AWS ap-southeast-1 · two availability zones · single region"
W, H = 1500, 1030
ICON_DIR = "icons-aws"   # python fetch_icons.py --dir icons-aws users cloudfront waf alb ecs rds s3 cloudwatch nat
OUT = "architecture.png"
STRADDLE = {"sga", "sgb"}   # security-group labels sit on the top border, like draw.io
ACCEPTED_CROSSINGS = set()

CLOUD, REGION, AZ, VPC, PUB, PRIV, SG = "#232F3E", "#00A4A6", "#147EBA", "#8C4FFF", "#7AA116", "#00A4A6", "#DD3522"

GROUPS = [
 ("cloud",  260, 100, 1220, 910, "AWS Cloud",                          CLOUD,  "#232F3E", 0, 1),
 ("region", 292, 250, 1156, 736, "Region  ap-southeast-1  Singapore",  REGION, "#147EBA", 1, 1),
 ("vpc",    322, 322,  840, 634, "VPC  10.0.0.0/16",                   VPC,    "#8C4FFF", 0, 1),
 ("aza",    352, 470,  380, 460, "Availability Zone  1a",               AZ,     "#147EBA", 1, 0),
 ("azb",    752, 470,  380, 460, "Availability Zone  1b",               AZ,     "#147EBA", 1, 0),
 ("puba",   372, 512,  340, 118, "Public subnet",                       PUB,    "#248814", 0, 1),
 ("pubb",   772, 512,  340, 118, "Public subnet",                       PUB,    "#248814", 0, 1),
 ("pria",   372, 660,  340, 240, "Private subnet",                      PRIV,   "#147EBA", 0, 1),
 ("prib",   772, 660,  340, 240, "Private subnet",                      PRIV,   "#147EBA", 0, 1),
 ("sga",    420, 760,  244, 130, "Security group · app only",      SG,     "#DD3522", 0, 1),
 ("sgb",    820, 760,  244, 130, "Security group · app only",      SG,     "#DD3522", 0, 1),
]

RES = [
 ("users",      120, 150, "Customers",                 "web and mobile"),
 ("cloudfront", 560, 150, "CloudFront",                "TLS · static cache"),
 ("waf",        760, 150, "AWS WAF",                   "managed rules"),
 ("alb",        742, 356, "Application Load Balancer", "spans both zones"),
 ("nat",        430, 540, "NAT Gateway",               ""),
 ("nat",        830, 540, "NAT Gateway",               ""),
 ("ecs",        542, 690, "app containers",            "ECS Fargate"),
 ("ecs",        942, 690, "app containers",            "ECS Fargate"),
 ("rds",        542, 800, "RDS PostgreSQL",            "PRIMARY"),
 ("rds",        942, 800, "RDS PostgreSQL",            "STANDBY · synchronous"),
 ("s3",        1300, 350, "S3",                        "media · SSE-KMS"),
 ("cloudwatch", 1300, 500, "CloudWatch",               "logs · alarms"),
]

CONN = [
 ([(151, 171), (531, 171)],                              0, "HTTPS",      (340, 157)),
 ([(589, 171), (731, 171)],                              1, "inspects",   (660, 171)),
 ([(560, 236), (560, 288), (742, 288), (742, 352)],      0, "cache miss", (650, 288)),
 ([(742, 440), (742, 452), (542, 452), (542, 686)],      0, "",           None),
 ([(742, 440), (742, 452), (942, 452), (942, 686)],      0, "routes",     (842, 452)),
 ([(542, 774), (542, 796)],                              0, "queries",    (600, 785)),
 ([(571, 821), (913, 821)],                              0, "RPO ~ 0",    (860, 821)),
 ([(971, 700), (1200, 700), (1200, 371), (1271, 371)],   1, "media",      (1236, 371)),
 ([(971, 724), (1230, 724), (1230, 521), (1271, 521)],   1, "metrics",    (1040, 724)),
]

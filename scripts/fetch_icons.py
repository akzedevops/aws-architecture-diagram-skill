#!/usr/bin/env python3
"""Copy architecture icons from the `diagrams` package into a folder under short names.

    python fetch_icons.py --dir icons-aws eks rds s3 cloudfront alb nat
    python fetch_icons.py --dir icons-aws msk=aws/analytics/managed-streaming-for-kafka
    python fetch_icons.py --list kube            # search the whole icon tree

Requires `pip install diagrams` (it bundles the official AWS Architecture Icons plus
Kubernetes, on-prem and SaaS sets). Short names below cover the common services; anything
else is given as name=path, where path is relative to the package's resources folder
without the .png extension.
"""
import argparse, os, shutil, sys

ALIASES = {
    # compute
    "eks": "aws/compute/elastic-kubernetes-service", "ecs": "aws/compute/elastic-container-service",
    "fargate": "aws/compute/fargate", "ec2": "aws/compute/ec2", "lambda": "aws/compute/lambda",
    "batch": "aws/compute/batch", "ecr": "aws/compute/ec2-container-registry",
    "app-runner": "aws/compute/app-runner", "beanstalk": "aws/compute/elastic-beanstalk",
    "autoscaling": "aws/compute/ec2-auto-scaling",
    # database
    "rds": "aws/database/rds", "rds-mysql": "aws/database/rds-mysql-instance",
    "rds-postgres": "aws/database/rds-postgresql-instance", "aurora": "aws/database/aurora",
    "dynamodb": "aws/database/dynamodb", "elasticache": "aws/database/elasticache",
    "redshift": "aws/database/redshift", "documentdb": "aws/database/documentdb-mongodb-compatibility",
    "opensearch": "aws/analytics/amazon-opensearch-service", "neptune": "aws/database/neptune",
    # storage
    "s3": "aws/storage/simple-storage-service-s3", "efs": "aws/storage/elastic-file-system-efs",
    "ebs": "aws/storage/elastic-block-store-ebs", "backup": "aws/storage/backup",
    "glacier": "aws/storage/s3-glacier", "fsx": "aws/storage/fsx",
    # network
    "cloudfront": "aws/network/cloudfront", "route53": "aws/network/route-53",
    "elb": "aws/network/elastic-load-balancing", "alb": "aws/network/elb-application-load-balancer",
    "nlb": "aws/network/elb-network-load-balancer", "nat": "aws/network/nat-gateway",
    "igw": "aws/network/internet-gateway", "vpc": "aws/network/vpc",
    "transit-gateway": "aws/network/transit-gateway", "direct-connect": "aws/network/direct-connect",
    "vpn": "aws/network/site-to-site-vpn", "endpoint": "aws/network/endpoint",
    "privatelink": "aws/network/privatelink", "api-gateway": "aws/network/api-gateway",
    "global-accelerator": "aws/network/global-accelerator", "app-mesh": "aws/network/app-mesh",
    # security
    "waf": "aws/security/waf", "shield": "aws/security/shield", "guardduty": "aws/security/guardduty",
    "secrets": "aws/security/secrets-manager", "kms": "aws/security/key-management-service",
    "iam": "aws/security/identity-and-access-management-iam", "cognito": "aws/security/cognito",
    "acm": "aws/security/certificate-manager", "security-hub": "aws/security/security-hub",
    "inspector": "aws/security/inspector", "macie": "aws/security/macie",
    # management
    "cloudwatch": "aws/management/cloudwatch", "cloudtrail": "aws/management/cloudtrail",
    "config": "aws/management/config", "ssm": "aws/management/systems-manager",
    "cloudformation": "aws/management/cloudformation", "organizations": "aws/management/organizations",
    "grafana": "aws/management/amazon-managed-grafana", "prometheus": "aws/management/amazon-managed-prometheus",
    # integration
    "sns": "aws/integration/simple-notification-service-sns", "sqs": "aws/integration/simple-queue-service-sqs",
    "eventbridge": "aws/integration/eventbridge", "step-functions": "aws/integration/step-functions",
    "ses": "aws/engagement/simple-email-service-ses", "mq": "aws/integration/mq",
    # devtools and data
    "codebuild": "aws/devtools/codebuild", "codepipeline": "aws/devtools/codepipeline",
    "codedeploy": "aws/devtools/codedeploy", "xray": "aws/devtools/x-ray",
    "kinesis": "aws/analytics/kinesis", "msk": "aws/analytics/managed-streaming-for-kafka",
    "glue": "aws/analytics/glue", "athena": "aws/analytics/athena", "sagemaker": "aws/ml/sagemaker",
    "bedrock": "aws/ml/bedrock",
    # general
    "users": "aws/general/users", "user": "aws/general/user", "client": "aws/general/client",
    "internet": "aws/general/internet-alt1", "server": "aws/general/traditional-server",
    "mobile": "aws/general/mobile-client", "office": "aws/general/office-building",
    # not AWS
    "argo": "onprem/gitops/argocd", "flux": "onprem/gitops/flux", "gitlab": "onprem/vcs/gitlab",
    "github": "onprem/vcs/github", "jenkins": "onprem/ci/jenkins", "github-actions": "onprem/ci/github-actions",
    "k8s-pod": "k8s/compute/pod", "k8s-deploy": "k8s/compute/deploy", "k8s-svc": "k8s/network/svc",
    "k8s-ingress": "k8s/network/ing",
}


def resources_root():
    try:
        import diagrams
    except ImportError:
        sys.exit("the `diagrams` package is not installed: pip install diagrams")
    return os.path.abspath(os.path.join(os.path.dirname(diagrams.__file__), "..", "resources"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="short names, or name=provider/category/file")
    ap.add_argument("--dir", default="icons-aws", help="destination folder (default icons-aws)")
    ap.add_argument("--list", metavar="PATTERN", help="search icon paths containing PATTERN and exit")
    a = ap.parse_args()
    root = resources_root()

    if a.list is not None:
        pat = a.list.lower()
        hits = []
        for d, _, files in os.walk(root):
            for f in files:
                if f.endswith(".png") and not f.endswith("-rounded.png"):
                    rel = os.path.relpath(os.path.join(d, f[:-4]), root).replace(os.sep, "/")
                    if pat in rel.lower():
                        hits.append(rel)
        print("\n".join(sorted(hits)) or "no icon path contains %r" % a.list)
        return

    if not a.names:
        ap.error("give at least one icon name, or --list PATTERN")
    os.makedirs(a.dir, exist_ok=True)
    missing = []
    for item in a.names:
        name, _, path = item.partition("=")
        path = path or ALIASES.get(name)
        if not path:
            missing.append("%s (no alias; use %s=provider/category/file, see --list)" % (name, name))
            continue
        src = os.path.join(root, *path.split("/")) + ".png"
        if not os.path.exists(src):
            missing.append("%s -> %s.png not found in the diagrams package" % (name, path))
            continue
        dst = os.path.join(a.dir, name + ".png")
        shutil.copyfile(src, dst)
        print("copied %-16s <- %s" % (name + ".png", path))
    if missing:
        print("\nNOT copied:")
        for m in missing:
            print("  ", m)
        sys.exit(1)


if __name__ == "__main__":
    main()

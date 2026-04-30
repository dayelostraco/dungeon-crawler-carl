#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.achievement_stack import AchievementStack

app = cdk.App()

# Mode: "prod" (default — live crawl.sigilark.com) or "ephemeral" (throwaway).
mode = app.node.try_get_context("mode") or "prod"

# Domain config. Defaults preserve the prod stack as-is.
# Pass --context domain=none (or empty) to deploy without a custom domain
# (ephemeral mode does this automatically).
if mode == "ephemeral":
    stack_id = app.node.try_get_context("stack_id") or "AchievementIntercomStackEphemeral"
    domain_name = None
    hosted_zone_name = None
else:
    stack_id = app.node.try_get_context("stack_id") or "AchievementIntercomStack"
    raw_domain = app.node.try_get_context("domain")
    raw_zone = app.node.try_get_context("hosted_zone")
    domain_name = (
        None if raw_domain in (None, "", "none") else raw_domain
    ) or "crawl.sigilark.com"
    hosted_zone_name = (
        None if raw_zone in (None, "", "none") else raw_zone
    ) or "sigilark.com"
    # Allow explicit opt-out of custom domain in prod mode too.
    if raw_domain in ("", "none"):
        domain_name = None
        hosted_zone_name = None

AchievementStack(
    app,
    stack_id,
    mode=mode,
    domain_name=domain_name,
    hosted_zone_name=hosted_zone_name,
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()

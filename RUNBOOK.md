# The Crawl Log — Runbook

Operations guide for maintaining the production deployment at https://crawl.sigilark.com

---

## Architecture Quick Reference

```
Internet → ALB (HTTPS) → ECS Fargate (1 vCPU, 2GB) → Container (uvicorn :8000)
                                                      ↳ DynamoDB (via VPC endpoint)
                                                      ↳ S3 (via VPC endpoint) → CloudFront CDN
                                                      ↳ Secrets Manager (API keys)
```

- **AWS Region:** us-east-1
- **Stack Name:** AchievementIntercomStack
- **Domain:** crawl.sigilark.com
- **CI/CD:** GitHub Actions → auto-deploy on push to main
- **Dashboard:** [CrawlLog-Operations](https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/CrawlLog-Operations) — latency, requests, errors, ECS resources, DynamoDB, generator retries

---

## Checking Service Health

```bash
# Quick health check
curl https://crawl.sigilark.com/health

# ECS service status
aws ecs describe-services \
  --cluster $(aws ecs list-clusters --query 'clusterArns[0]' --output text) \
  --services $(aws ecs list-services --cluster $(aws ecs list-clusters --query 'clusterArns[0]' --output text) --query 'serviceArns[0]' --output text) \
  --query 'services[0].{status:status,desired:desiredCount,running:runningCount}'

# CloudFormation stack status
aws cloudformation describe-stacks --stack-name AchievementIntercomStack \
  --query 'Stacks[0].StackStatus' --output text
```

---

## Viewing Logs

```bash
# Find the log group
LOG_GROUP=$(aws logs describe-log-groups --log-group-name-prefix "Achievement" \
  --query 'logGroups[0].logGroupName' --output text)

# Latest log stream
STREAM=$(aws logs describe-log-streams --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime --descending --limit 1 \
  --query 'logStreams[0].logStreamName' --output text)

# Tail recent logs
aws logs get-log-events --log-group-name "$LOG_GROUP" \
  --log-stream-name "$STREAM" --limit 50 \
  --query 'events[*].message' --output text
```

---

## Redeploying

### Via CI/CD (recommended)
Push to `main` — GitHub Actions handles lint, test, docker build, and deploy automatically.

```bash
git push origin main
# Monitor: gh run list --repo sigilark/dungeon-crawler-carl --limit 1
```

### Manual deploy (if CI is broken)
```bash
make deploy            # prod stack, crawl.sigilark.com
make diff              # preview pending changes first
```

`make deploy` wraps `cdk deploy AchievementIntercomStack --context mode=prod`. See `make help` for all targets.

---

## Stand up a fresh deployment

### Throwaway / staging environment
Deploys a parallel stack with auto-named resources, no custom domain (ALB DNS only), and `DESTROY` removal policies on everything — clean teardown in one command.

```bash
make deploy-ephemeral          # ~10 min (Fargate + CloudFront)
make set-secrets-ephemeral     # paste API keys when prompted
make redeploy-task-ephemeral   # restart task to pick up secrets

# URL is in the stack output as `Url` (an http://*.elb.amazonaws.com address)
aws cloudformation describe-stacks --stack-name AchievementIntercomStackEphemeral \
  --query "Stacks[0].Outputs[?OutputKey=='Url'].OutputValue" --output text

# When done:
make destroy-ephemeral         # ~15-30 min (CloudFront delete is slow)
```

### Stand up the prod stack in a new AWS account
```bash
# 1. Bootstrap CDK + create empty secrets
make bootstrap AWS_ACCOUNT=<new-account-id>

# 2. Set the API key values
make set-secrets

# 3. Ensure the hosted zone for your domain exists in Route 53
#    (the stack does `from_lookup` on it — must exist before deploy)

# 4. Deploy
make deploy AWS_ACCOUNT=<new-account-id>
```

To use a domain other than `crawl.sigilark.com`, edit `cdk/app.py` defaults or pass `--context domain=foo.example.com --context hosted_zone=example.com`.

---

## Clearing Production Data

### Clear all achievements
```bash
# Scan and delete all items from DynamoDB
for id in $(aws dynamodb scan --table-name achievements \
  --query 'Items[*].id.N' --output text); do
  aws dynamodb delete-item --table-name achievements \
    --key "{\"id\": {\"N\": \"$id\"}}"
done
```

### Clear audio cache
```bash
# List the S3 bucket
BUCKET=$(aws cloudformation describe-stacks --stack-name AchievementIntercomStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)

# Delete all audio files
aws s3 rm s3://$BUCKET --recursive
```

---

## Common Issues

### "Stack is in UPDATE_IN_PROGRESS"
A previous deploy is still running. Wait for it to complete or check:
```bash
aws cloudformation describe-stacks --stack-name AchievementIntercomStack \
  --query 'Stacks[0].StackStatus' --output text
```

### Container keeps restarting
Check logs for import errors or missing dependencies:
```bash
# Check recent ECS events
aws ecs describe-services --cluster <cluster> --services <service> \
  --query 'services[0].events[:5].[message]' --output text
```
Common causes: missing Python package in requirements.txt, missing system dep in Dockerfile.

### Audio not playing on mobile
Browser autoplay restrictions. The Play button should appear — if not, check the browser console for errors.

### ElevenLabs rate limit
The app makes 3 ElevenLabs calls per achievement (title, description, reward). If you hit rate limits, reduce generation frequency or upgrade your ElevenLabs plan.

### Reward format drift
Check if the model is clustering on specific reward formats:
```bash
curl https://crawl.sigilark.com/api/admin/reward-distribution
```
If any format exceeds 40%, consider reviewing the system prompt. Run `python scripts/check_reward_distribution.py --count 20` locally to validate with fresh samples.

### Daily challenge participation
Check how many users are engaging with the daily challenge:
```bash
curl https://crawl.sigilark.com/api/admin/daily-challenge
```

### Generator retry frequency
Check CloudWatch logs for banned content retries:
```bash
aws logs filter-log-events --log-group-name "$LOG_GROUP" \
  --filter-pattern "Banned content detected" --limit 20 \
  --query 'events[*].message' --output text
```
Zero retries is ideal (Streisand fix working). Frequent retries may indicate the prompt needs tuning.

### Claude API errors
Check if the API key is valid and has credits:
```bash
aws secretsmanager get-secret-value \
  --secret-id achievement-intercom/anthropic-api-key \
  --query 'SecretString' --output text | head -c 20
```

---

## Secrets Management

Secrets are stored in AWS Secrets Manager:
- `achievement-intercom/anthropic-api-key`
- `achievement-intercom/elevenlabs-api-key`
- `achievement-intercom/elevenlabs-voice-id`

### Rotate a secret
```bash
aws secretsmanager update-secret \
  --secret-id achievement-intercom/anthropic-api-key \
  --secret-string "new-key-here"
```
Then redeploy to pick up the new value (ECS pulls secrets at task start).

---

## Cost Monitoring

### Current monthly estimate: ~$42
- Fargate: ~$35
- ALB: ~$18
- DynamoDB/S3/CloudFront: ~$2
- Secrets Manager: ~$1.20
- Claude API: ~$3 (at ~10 achievements/day with Sonnet)
- ElevenLabs: ~$3

### Check current month spend
```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY --metrics BlendedCost \
  --query 'ResultsByTime[0].Total.BlendedCost'
```

---

## Disaster Recovery

- **DynamoDB:** RemovalPolicy.RETAIN — survives stack deletion
- **S3 bucket:** RemovalPolicy.RETAIN — survives stack deletion
- **Secrets:** Not managed by CDK in prod mode — persist independently
- **Code:** GitHub repo is the source of truth
- **Full rebuild from nothing:** `make bootstrap && make set-secrets && make deploy`

---

## Pause and Revive (data preserved)

The prod stack supports a "pause" mode where the running compute (ECS, ALB, VPC, CloudFront, etc.) is torn down but the DynamoDB table, S3 audio bucket, and Secrets Manager entries are preserved. Cost while paused: ~$2/mo. Revive cost: full ~$42/mo.

### Pause (destroy compute)
```bash
make destroy-prod CONFIRM=delete-prod
```
What happens:
1. `scripts/capture-orphans.sh` writes `.cdk-orphans.json` with the live table name, bucket name, and their CDK logical IDs.
2. `cdk destroy AchievementIntercomStack` tears down everything except RETAIN'd resources.
3. Site goes offline within ~5 minutes (ALB + DNS removed). CloudFront takes 15-30 min to fully delete.

**Commit `.cdk-orphans.json` to git** so revive works after a fresh clone.

### Revive (re-attach data + redeploy)
```bash
make revive
```
What happens:
1. `cdk import --resource-mapping .cdk-orphans.json` re-attaches the orphaned DynamoDB table and S3 bucket to a new CloudFormation stack via an IMPORT change set. Logical IDs from the synthesized template must match those in `.cdk-orphans.json` — they will, as long as the construct paths in CDK haven't changed.
2. `cdk deploy` then creates everything else (ECS, ALB, CloudFront, ACM, Route 53, dashboard, etc.) and updates the imported resources to match the template.

Total revive time: ~20-25 minutes (CFN change set + Fargate task start + CloudFront propagation).

**The CloudFront domain changes on revive** — but the app reads `CDN_DOMAIN` from env at request time and reconstructs URLs dynamically from S3 keys stored in DynamoDB, so old audio entries serve correctly through the new distribution.

### Recovering `.cdk-orphans.json` if lost
If the file is missing (e.g., destroyed without committing it), recreate it manually:
```bash
# 1. Find the orphaned bucket name
aws s3 ls | grep audiobucket

# 2. Synthesize the template to find current logical IDs
cd cdk && cdk synth AchievementIntercomStack --context mode=prod \
  --context account=<your-account> --context region=us-east-1 --quiet
jq -r '.Resources | to_entries | map(select(.value.Type == "AWS::DynamoDB::Table" or .value.Type == "AWS::S3::Bucket")) | .[] | "\(.value.Type)\t\(.key)"' \
  cdk.out/AchievementIntercomStack.template.json

# 3. Hand-write .cdk-orphans.json:
{
  "<DynamoDB-logical-id>": { "TableName": "achievements" },
  "<S3-logical-id>":       { "BucketName": "<orphaned-bucket-name>" }
}
```

### Fully nuke (no revive intended)
```bash
make destroy-prod CONFIRM=delete-prod
aws dynamodb delete-table --table-name achievements
aws s3 rb s3://<bucket-name> --force
aws secretsmanager delete-secret --secret-id achievement-intercom/anthropic-api-key --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id achievement-intercom/elevenlabs-api-key --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id achievement-intercom/elevenlabs-voice-id --force-delete-without-recovery
```

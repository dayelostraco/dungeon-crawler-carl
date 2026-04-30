.PHONY: help bootstrap set-secrets set-secrets-ephemeral \
        deploy deploy-ephemeral diff diff-ephemeral \
        destroy-ephemeral destroy-prod revive capture-orphans \
        redeploy-task redeploy-task-ephemeral \
        logs health cost

# Override on the command line: `make deploy AWS_ACCOUNT=123456789012`
AWS_ACCOUNT ?= 302654592899
AWS_REGION  ?= us-east-1

STACK_PROD      := AchievementIntercomStack
STACK_EPHEMERAL := AchievementIntercomStackEphemeral

CDK_PROD = cd cdk && cdk
CDK_EPH  = cd cdk && cdk

PROD_CTX = --context account=$(AWS_ACCOUNT) --context region=$(AWS_REGION) --context mode=prod
EPH_CTX  = --context account=$(AWS_ACCOUNT) --context region=$(AWS_REGION) --context mode=ephemeral

help: ## Show this help
	@awk 'BEGIN{FS=":.*## "} /^[a-zA-Z_-]+:.*## /{printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ----- one-time setup -----

bootstrap: ## CDK bootstrap + ensure prod secrets exist (run once per fresh account)
	$(CDK_PROD) bootstrap aws://$(AWS_ACCOUNT)/$(AWS_REGION)
	AWS_REGION=$(AWS_REGION) ./scripts/ensure-secrets.sh

# ----- prod stack (live: crawl.sigilark.com) -----

deploy: ## Deploy prod stack (crawl.sigilark.com)
	$(CDK_PROD) deploy $(STACK_PROD) $(PROD_CTX) --require-approval never

diff: ## Show pending changes vs deployed prod stack
	$(CDK_PROD) diff $(STACK_PROD) $(PROD_CTX)

set-secrets: ## Interactively set prod API keys (Anthropic, ElevenLabs)
	AWS_REGION=$(AWS_REGION) ./scripts/set-secrets.sh

redeploy-task: ## Force ECS to pull new secret values into a fresh task
	@CLUSTER=$$(aws cloudformation describe-stacks --stack-name $(STACK_PROD) \
	  --region $(AWS_REGION) \
	  --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" --output text 2>/dev/null) && \
	if [ -z "$$CLUSTER" ]; then \
	  CLUSTER=$$(aws ecs list-clusters --region $(AWS_REGION) --query 'clusterArns[0]' --output text); \
	  SERVICE=$$(aws ecs list-services --cluster $$CLUSTER --region $(AWS_REGION) --query 'serviceArns[0]' --output text); \
	else \
	  SERVICE=$$(aws cloudformation describe-stacks --stack-name $(STACK_PROD) \
	    --region $(AWS_REGION) \
	    --query "Stacks[0].Outputs[?OutputKey=='ServiceName'].OutputValue" --output text); \
	fi && \
	aws ecs update-service --cluster "$$CLUSTER" --service "$$SERVICE" \
	  --force-new-deployment --region $(AWS_REGION) >/dev/null && \
	echo "Forced new deployment of $$SERVICE"

# ----- ephemeral stack (throwaway, no custom domain, easy teardown) -----

deploy-ephemeral: ## Deploy a throwaway copy (auto-named resources, ALB DNS only)
	$(CDK_EPH) deploy $(STACK_EPHEMERAL) $(EPH_CTX) --require-approval never
	@echo ""
	@echo "Set the API keys: make set-secrets-ephemeral"
	@echo "Then force task restart: make redeploy-task-ephemeral"

diff-ephemeral: ## Show pending changes vs deployed ephemeral stack
	$(CDK_EPH) diff $(STACK_EPHEMERAL) $(EPH_CTX)

set-secrets-ephemeral: ## Set API keys for the ephemeral stack
	AWS_REGION=$(AWS_REGION) ./scripts/set-secrets.sh $(STACK_EPHEMERAL)

redeploy-task-ephemeral: ## Force the ephemeral ECS task to restart with new secrets
	@CLUSTER=$$(aws cloudformation describe-stacks --stack-name $(STACK_EPHEMERAL) \
	  --region $(AWS_REGION) \
	  --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" --output text) && \
	SERVICE=$$(aws cloudformation describe-stacks --stack-name $(STACK_EPHEMERAL) \
	  --region $(AWS_REGION) \
	  --query "Stacks[0].Outputs[?OutputKey=='ServiceName'].OutputValue" --output text) && \
	aws ecs update-service --cluster "$$CLUSTER" --service "$$SERVICE" \
	  --force-new-deployment --region $(AWS_REGION) >/dev/null && \
	echo "Forced new deployment of $$SERVICE"

destroy-ephemeral: ## Tear down the ephemeral stack (clean — DynamoDB + S3 + secrets all DESTROY)
	$(CDK_EPH) destroy $(STACK_EPHEMERAL) $(EPH_CTX) --force

# ----- destructive: prod -----

capture-orphans: ## Save orphan resource IDs (DynamoDB + S3) to .cdk-orphans.json
	AWS_REGION=$(AWS_REGION) AWS_ACCOUNT=$(AWS_ACCOUNT) ./scripts/capture-orphans.sh

destroy-prod: ## Tear down PROD. Leaves DynamoDB + S3 (RETAIN) orphaned. Requires CONFIRM=delete-prod
	@if [ "$(CONFIRM)" != "delete-prod" ]; then \
	  echo ""; \
	  echo "  This destroys the live $(STACK_PROD) (crawl.sigilark.com)."; \
	  echo "  DynamoDB table 'achievements' and the S3 audio bucket are RETAIN —"; \
	  echo "  they will be ORPHANED, not deleted, and survive the teardown."; \
	  echo "  Secrets in Secrets Manager are not stack-managed and survive."; \
	  echo ""; \
	  echo "  Orphan identifiers will be saved to .cdk-orphans.json so"; \
	  echo "  'make revive' can re-attach them via cdk import."; \
	  echo ""; \
	  echo "  To proceed, re-run with CONFIRM=delete-prod:"; \
	  echo "    make destroy-prod CONFIRM=delete-prod"; \
	  echo ""; \
	  exit 1; \
	fi
	@echo "Step 1/2: capturing orphan identifiers..."
	AWS_REGION=$(AWS_REGION) AWS_ACCOUNT=$(AWS_ACCOUNT) ./scripts/capture-orphans.sh
	@echo ""
	@echo "Step 2/2: destroying stack..."
	$(CDK_PROD) destroy $(STACK_PROD) $(PROD_CTX) --force
	@echo ""
	@echo "Stack destroyed. Preserved (orphaned) resources:"
	@echo "  - DynamoDB table:  achievements (data intact)"
	@echo "  - S3 bucket:       (see .cdk-orphans.json — audio cache intact)"
	@echo "  - Secrets Manager: achievement-intercom/{anthropic,elevenlabs}-api-key, elevenlabs-voice-id"
	@echo ""
	@echo "To revive: make revive"
	@echo "(commit .cdk-orphans.json to git so revive works after a fresh checkout)"

revive: ## Re-attach orphaned data (DynamoDB + S3) and redeploy the prod stack
	@if [ ! -f .cdk-orphans.json ]; then \
	  echo "Missing .cdk-orphans.json. Cannot revive without orphan identifiers."; \
	  echo "If you have the table + bucket names, run:"; \
	  echo "  ./scripts/capture-orphans.sh    # if stack still exists"; \
	  echo "  # otherwise hand-write .cdk-orphans.json — see RUNBOOK.md"; \
	  exit 1; \
	fi
	@echo "Step 1/2: cdk import — re-attaching orphaned DynamoDB table + S3 bucket"
	@echo "  Mapping:"
	@cat .cdk-orphans.json | sed 's/^/    /'
	cd cdk && JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 cdk import $(STACK_PROD) \
	  $(PROD_CTX) --resource-mapping ../.cdk-orphans.json
	@echo ""
	@echo "Step 2/2: cdk deploy — creating ECS, ALB, CloudFront, etc."
	$(CDK_PROD) deploy $(STACK_PROD) $(PROD_CTX) --require-approval never
	@echo ""
	@echo "Stack revived. Verify: make health"

# ----- ops -----

logs: ## Tail the latest 50 prod log lines
	@LOG_GROUP=$$(aws logs describe-log-groups --log-group-name-prefix "Achievement" \
	  --region $(AWS_REGION) --query 'logGroups[0].logGroupName' --output text) && \
	STREAM=$$(aws logs describe-log-streams --log-group-name "$$LOG_GROUP" \
	  --region $(AWS_REGION) --order-by LastEventTime --descending --limit 1 \
	  --query 'logStreams[0].logStreamName' --output text) && \
	aws logs get-log-events --log-group-name "$$LOG_GROUP" \
	  --log-stream-name "$$STREAM" --region $(AWS_REGION) --limit 50 \
	  --query 'events[*].message' --output text

health: ## Hit /health on prod
	@curl -fsS https://crawl.sigilark.com/health && echo

cost: ## Current month-to-date AWS spend
	@aws ce get-cost-and-usage \
	  --time-period Start=$$(date +%Y-%m-01),End=$$(date +%Y-%m-%d) \
	  --granularity MONTHLY --metrics BlendedCost \
	  --query 'ResultsByTime[0].Total.BlendedCost' \
	  --output json

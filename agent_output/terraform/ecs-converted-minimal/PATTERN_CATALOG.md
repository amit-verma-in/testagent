# Pattern Catalogue alignment

This directory was produced by `convert_cloudformation_template_to_terraform`.
Raw `aws_*` resources mirror the CloudFormation template; they are **not** necessarily
the approved internal modules for your organization.

## Next steps (agent workflow)

1. Use **Pattern Catalogue** MCP tools exposed in this agent (same session) to search
   for modules covering ECS, ALB, IAM, and logging.
2. Replace resource blocks with `module` calls using the **sources and variable names**
   returned by those tools.
3. Run `terraform fmt` and `terraform validate` locally.
4. Optionally run `scan_local_terraform_code` on this folder after Wiz CLI authentication.

## Hints for this template

- **ECS Fargate**: Call Pattern Catalogue MCP tools (e.g. search/list modules for ECS, Fargate, task definition) and replace aws_ecs_* resources with the approved module blocks and inputs from your catalog.
- **IAM**: Align task execution and task roles with catalog IAM modules or policies; avoid copying admin-equivalent policies from samples.

Output folder (relative to agent output root): `terraform/ecs-converted-minimal/`


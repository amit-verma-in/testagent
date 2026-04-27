# Pattern Catalogue alignment

Terraform in this folder was produced with **Pattern Catalogue** conventions in mind.
Use internal modules and sources returned by the Pattern Catalogue MCP tools for your organization.

## Next steps (agent workflow)

1. Use **Pattern Catalogue** MCP tools in this agent to confirm module sources, versions, and parameters.
2. Replace or refine raw resources with `module` blocks per catalog guidance where applicable.
3. Run `terraform fmt` and `terraform validate` locally.
4. Optionally run `scan_local_terraform_code` on this folder after Wiz CLI authentication.

Output folder (relative to agent output root): `terraform/azure-linux-vm/`

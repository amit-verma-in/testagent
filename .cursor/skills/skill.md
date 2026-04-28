---
name: cfn-to-tf-pattern-catalog-migration
description: >-
  Migrate CloudFormation to Terraform using a Pattern Catalog-first approach.
  Always resolve resources via Pattern Catalog MCP/module templates first.
  Generate raw Terraform resources only when no compatible pattern exists and
  only with explicit manual-review annotations.
---

# Requirements Document

## Project Description (Input)
**Jira Ticket**: [APPSRE-1182](https://mckinsey.atlassian.net/browse/APPSRE-1182)

**Summary**: Create Migration Agent from AWS service Catalog (CFN) to Pattern Catalog (TF)

**Description**: As a SRE, I need an automated workflow to migrate existing CloudFormation infrastructure to Terraform, so that we can standardize on Terraform for infrastructure-as-code and leverage the Pattern Catalog for consistent, reusable infrastructure patterns.

The system will:
- Read current deployed infrastructure from AWS accounts
- Retrieve CloudFormation templates and stack configurations from AWS Service Catalog
- Fetch matching Terraform patterns using the Pattern Catalog MCP (Terraform Enterprise Registry / Pattern Catalog)
- Generate Terraform code (.tf files) with proper resource definitions
- Generate Terraform import blocks for existing resources to enable state management
- Create a Pull Request in the target IAC repository with the generated Terraform code
- Follow repository coding standards and command structure patterns
- Integrate with existing CLI command architecture in `packages/module-commands/`

## Requirements

### Requirement 1: IAC Repository Input and KMS Provisioned Product ID
**Objective:** As a SRE, I want the system to start by requesting the IAC repository path and KMS provisioned product ID, so that the migration workflow targets the correct infrastructure location and can migrate all resources including manually created KMS.

#### Acceptance Criteria
1. When the migration command is invoked, the Migration Agent shall prompt for the IAC repository path as the first required input.
2. When an IAC repository path is provided, the Migration Agent shall validate that the path contains CloudFormation directories: `CloudFormation/Templates` and `CloudFormation/Parameters/<env>` (e.g., `CloudFormation/Parameters/dev`, `CloudFormation/Parameters/stg`, `CloudFormation/Parameters/prod`).
3. When an IAC repository path is provided, the Migration Agent shall verify that the `CloudFormation/Templates` directory exists and contains CloudFormation template files (`.yaml`, `.yml`, or `.json`).
4. When the IAC repository path is validated, the Migration Agent shall prompt for the AWS Service Catalog KMS provisioned product ID as a required input (since KMS is typically created manually and not part of the IAC).
5. When the KMS provisioned product ID is provided, the Migration Agent shall retrieve the KMS configuration from AWS Service Catalog to enable migration of all resources that depend on KMS.
6. If the IAC repository path does not exist, the Migration Agent shall display an error message with the invalid path and exit with a non-zero status code.
7. If the `CloudFormation/Templates` directory does not exist or does not contain any CloudFormation template files, the Migration Agent shall display an error message and exit with a non-zero status code.
8. When scanning for parameters, the Migration Agent shall look for parameter files in `CloudFormation/Parameters/<env>` directories that match the environment being migrated.
9. If the KMS provisioned product ID is not provided, the Migration Agent shall display an error message explaining that it is required to migrate all resources and exit with a non-zero status code.

### Requirement 2: AWS Infrastructure Discovery
**Objective:** As a SRE, I want the system to discover and read current deployed infrastructure from AWS accounts and IAC repository, so that I can identify resources that need to be migrated from CloudFormation to Terraform.

#### Acceptance Criteria
1. When an AWS account ID is provided, the Migration Agent shall authenticate to the specified AWS account using configured credentials and configure AWS SDK to use the us-east-1 region for all API calls.
2. When the IAC repository path is validated, the Migration Agent shall read CloudFormation templates from the `CloudFormation/Templates` directory.
3. When reading CloudFormation templates from the IAC repository, the Migration Agent shall parse template files (`.yaml`, `.yml`, or `.json`) and extract resource definitions, recognizing that these templates call Service Catalog Patterns.
4. When reading CloudFormation parameters, the Migration Agent shall read parameter files from `CloudFormation/Parameters/<env>` directories for the specified environment.
5. When discovering infrastructure, the Migration Agent shall enumerate all CloudFormation stacks in the target AWS account, limited to the us-east-1 region only.
6. When a CloudFormation stack is identified, the Migration Agent shall retrieve the stack's template body and stack parameters from the us-east-1 region (preferring IAC repository templates if available, otherwise from AWS).
7. When a CloudFormation stack calls Service Catalog Patterns, the Migration Agent shall identify the Service Catalog product references and retrieve the corresponding product definitions from the us-east-1 region.
8. When discovering resources, the Migration Agent shall collect metadata for each resource including resource type, logical ID, physical ID, and current configuration, limited to resources in the us-east-1 region.
9. When the KMS provisioned product ID is provided, the Migration Agent shall use it to identify and include all KMS-related resources and their dependencies in the migration scope, limited to the us-east-1 region.
10. If AWS authentication fails, the Migration Agent shall display an error message indicating the authentication failure reason.
11. If a CloudFormation stack cannot be retrieved, the Migration Agent shall log a warning and continue processing other stacks.
12. The Migration Agent shall limit infrastructure discovery to the us-east-1 region only and shall not discover resources in other AWS regions.

### Requirement 3: AWS Service Catalog Integration
**Objective:** As a SRE, I want the system to retrieve CloudFormation templates and stack configurations from AWS Service Catalog, so that I can access standardized product definitions for migration, including manually created KMS resources.

#### Acceptance Criteria
1. When a Service Catalog product is specified, the Migration Agent shall retrieve the product's CloudFormation template from AWS Service Catalog in the us-east-1 region.
2. When retrieving a Service Catalog product, the Migration Agent shall fetch all associated product versions and provisioning artifacts from the us-east-1 region.
3. When the KMS provisioned product ID is provided (as a required input), the Migration Agent shall retrieve the KMS provisioning parameters, tags, and resource configuration associated with that product instance from the us-east-1 region.
4. When the KMS provisioned product is retrieved, the Migration Agent shall use it to identify all resources that depend on KMS (encrypted resources, IAM roles with KMS permissions, etc.) and include them in the migration scope, limited to the us-east-1 region.
5. When a provisioned product is identified, the Migration Agent shall retrieve the CloudFormation stack associated with the provisioned product from the us-east-1 region.
6. When CloudFormation templates in the IAC repository call Service Catalog Patterns, the Migration Agent shall resolve the Service Catalog product references and retrieve the corresponding product definitions.
7. When Service Catalog data is retrieved, the Migration Agent shall preserve the relationship between products, versions, and provisioned instances.
8. If a Service Catalog product is not found, the Migration Agent shall display an error message with the product identifier.
9. If Service Catalog API access is denied, the Migration Agent shall display a clear error message indicating insufficient permissions.
10. When the KMS provisioned product ID is required but not provided, the Migration Agent shall display a clear error message explaining that it is required to migrate all resources (since KMS is manually created and not in IAC) and exit with a non-zero status code.

### Requirement 4: Pattern Catalog Integration
**Objective:** Ensure all Terraform output follows Pattern Catalog standards by default.


<!-- #### Acceptance Criteria
1. When a CloudFormation resource type is identified, the Migration Agent shall fetch matching Terraform patterns using the **Pattern Catalog MCP** (Model Context Protocol); direct REST calls to https://patterncatalog.platform.mckinsey.com/ shall not be used for pattern discovery and retrieval when the MCP is available.
2. When querying via the Pattern Catalog MCP, the Migration Agent shall use MCP operations to search by resource type, service name, and configuration attributes (e.g., `search_pattern_catalog_modules`, `get_module_details`, `get_module_examples`).
3. When multiple matching patterns are found, the Migration Agent shall rank patterns by relevance and compatibility score.
4. When a matching pattern is selected, the Migration Agent shall retrieve the complete Terraform pattern definition (variables, outputs, documentation, examples) via the Pattern Catalog MCP (e.g., `get_module_details`, `get_module_examples`).
5. If no matching pattern is found via the Pattern Catalog MCP, the Migration Agent shall generate a basic Terraform resource definition based on the CloudFormation template.
6. If the Pattern Catalog MCP is unavailable or returns an error, the Migration Agent shall display a warning and proceed with basic Terraform generation.
7. The Migration Agent shall cache Pattern Catalog MCP responses to reduce calls during migration of multiple resources. -->

#### Mandatory Rules
1. For every CFN resource (or Service Catalog product), the agent MUST attempt Pattern Catalog MCP lookup first.
2. The agent MUST call, in order:
   - pattern search (by service/resource type + intent)
   - module details
   - module examples
3. If multiple modules match, the agent MUST select the highest compatibility score and document why.
4. The agent MUST prefer module invocation (`module` blocks) over raw `aws_*` resources.
5. Direct `aws_*` resource generation is allowed only when:
   - no compatible pattern exists after explicit lookup, OR
   - user explicitly asks to bypass Pattern Catalog.
6. On fallback, the generated code MUST include:
   - `MANUAL_REVIEW_REQUIRED` comment
   - reason Pattern Catalog could not be applied
   - suggested candidate patterns/services for future migration.

### Requirement 5: Terraform Code Generation
**Objective:** As a SRE, I want the system to generate Terraform code (.tf files) with proper resource definitions, so that the migrated infrastructure follows Terraform best practices and standards.

<!-- #### Acceptance Criteria
1. When generating Terraform code, the Migration Agent shall create .tf files in the specified target IAC repository path (separate from the source IAC repository that contains CloudFormation templates), following the repository's file naming conventions and directory structure.
2. When mapping CloudFormation resources to Terraform, the Migration Agent shall use appropriate Terraform resource types that match the CloudFormation resource functionality.
3. When generating Terraform resources, the Migration Agent shall convert CloudFormation parameters to Terraform variables with appropriate types and descriptions.
4. When generating Terraform resources, the Migration Agent shall convert CloudFormation outputs to Terraform outputs with proper descriptions.
5. When generating Terraform code, the Migration Agent shall include resource dependencies and relationships using Terraform depends_on or implicit dependencies.
6. When generating Terraform code, the Migration Agent shall apply proper formatting and follow Terraform style guidelines (2-space indentation, consistent spacing).
7. When CloudFormation intrinsic functions are encountered, the Migration Agent shall convert them to equivalent Terraform expressions (e.g., Ref → var, Fn::GetAtt → resource.attribute).
8. If a CloudFormation resource type has no direct Terraform equivalent, the Migration Agent shall generate a comment indicating manual review is required.
9. The Migration Agent shall generate separate .tf files for variables, outputs, and resources following Terraform module structure best practices. -->

#### Pattern-Catalog Output Standard
1. Generated Terraform MUST use Pattern Catalog modules when available.
2. Output structure SHOULD be:
   - `main.tf` (module blocks)
   - `variables.tf` (typed vars mapped from CFN params)
   - `outputs.tf`
   - `imports.tf` (if importing existing infra)
   - `<env>.tfvars`
3. Module versions MUST be pinned (no floating latest).
4. Module input mapping MUST preserve original CFN semantics and defaults.
5. Any unmapped CFN field MUST be listed in a migration notes section.

### Requirement 6: Terraform Import Block Generation
**Objective:** As a SRE, I want the system to generate Terraform import blocks for existing resources, so that I can manage existing infrastructure state without recreating resources.

#### Acceptance Criteria
1. When generating Terraform code for existing resources, the Migration Agent shall create import blocks for each resource that exists in AWS.
2. When generating import blocks, the Migration Agent shall use the correct Terraform resource address format (resource_type.resource_name).
3. When generating import blocks, the Migration Agent shall include the physical resource identifier (ARN or resource ID) from the discovered AWS resource.
4. When generating import blocks, the Migration Agent shall organize import blocks in a separate imports.tf file or within the corresponding resource file.
5. When multiple resources require import, the Migration Agent shall generate import blocks that respect resource dependencies and import order.
6. If a resource identifier cannot be determined, the Migration Agent shall generate a comment indicating manual import configuration is required.
7. The Migration Agent shall generate import blocks using Terraform 1.5+ import block syntax.

### Requirement 7: Pull Request Creation
**Objective:** As a SRE, I want the system to create a Pull Request when Terraform code is generated in the new IAC repository, so that the migrated infrastructure can be reviewed and merged through standard code review processes.

#### Acceptance Criteria
1. When Terraform code generation completes successfully, the Migration Agent shall create a new git branch in the target IAC repository (the repository containing the output directory where Terraform files were generated).
2. When creating a git branch, the Migration Agent shall use a descriptive branch name following the repository's branch naming conventions (e.g., `feat/migrate-cfn-to-tf-<stack-name>`, `migration/cfn-to-tf-<timestamp>`).
3. When Terraform files are generated, the Migration Agent shall stage and commit all generated Terraform files to the new branch with a descriptive commit message.
4. When the commit is created, the Migration Agent shall push the branch to the remote repository.
5. When the branch is pushed, the Migration Agent shall create a Pull Request using GitHub CLI (`gh pr create`) targeting the repository's default branch (e.g., `main`, `master`).
6. When creating the Pull Request, the Migration Agent shall generate a PR title that describes the migration (e.g., "Migrate CloudFormation stack <stack-name> to Terraform").
7. When creating the Pull Request, the Migration Agent shall generate a PR body that includes: summary of migrated resources, list of generated Terraform files, migration statistics (number of resources migrated, warnings, etc.), and any manual review notes.
8. When a PR template exists in the repository (`.github/PULL_REQUEST_TEMPLATE.md` or `.github/pull_request_template.md`), the Migration Agent shall use the template and populate relevant sections with migration details.
9. If GitHub CLI (`gh`) is not installed or not authenticated, the Migration Agent shall display clear error messages with instructions to install or authenticate GitHub CLI.
10. If the target IAC repository is not a git repository or does not have a remote configured, the Migration Agent shall display an error message and skip PR creation.
11. If PR creation fails, the Migration Agent shall display the error message but still report successful Terraform code generation, allowing the user to create the PR manually.
12. When the Pull Request is created successfully, the Migration Agent shall display the PR URL and summary information to the user.

### Requirement 8: CLI Command Integration
**Objective:** As a SRE, I want the migration functionality to integrate with the existing CLI command architecture, so that it follows repository coding standards and is discoverable through the standard command interface.

#### Acceptance Criteria
1. When implementing the migration agent, the system shall follow the command structure pattern in `packages/module-commands/` with manifest.json, cursor-commands/, and README.md.
2. When creating command files, the Migration Agent shall use the markdown command format consistent with other command groups in module-commands.
3. When the migration command is invoked, the Migration Agent shall accept command-line arguments for IAC repository path (pointing to directory containing `CloudFormation/Templates` and `CloudFormation/Parameters/<env>`), AWS account, stack name, KMS provisioned product ID, and target IAC repository path (for Terraform code generation and PR creation). The region parameter is not required as discovery is limited to us-east-1 only.
4. When the migration command is invoked, the Migration Agent shall provide interactive prompts for missing required parameters in the order: IAC repository path (with example showing CloudFormation directory structure), then KMS provisioned product ID (required for migrating all resources), then target IAC repository path (for Terraform output and PR creation), then other parameters.
5. When the migration command is invoked, the Migration Agent shall display progress indicators for long-running operations.
6. When the migration command completes, the Migration Agent shall provide a summary of generated files, resources migrated, and any warnings or errors encountered.
7. The Migration Agent shall be installable via `cb-cli commands install cfn-to-tf-migration-agent`.
8. The Migration Agent shall be discoverable via `cb-cli commands list` and `cb-cli commands info cfn-to-tf-migration-agent`.

### Requirement 9: Error Handling and Validation
**Objective:** As a SRE, I want the system to handle errors gracefully and validate inputs and outputs, so that migration failures are clearly communicated and invalid configurations are caught early.

#### Acceptance Criteria
1. When invalid AWS credentials are provided, the Migration Agent shall display a clear error message and exit with a non-zero status code.
2. When a CloudFormation stack template is malformed, the Migration Agent shall log the error and skip that stack with a warning message.
3. When generated Terraform code fails syntax validation, the Migration Agent shall display validation errors and the file location.
4. When the Pattern Catalog MCP returns an error response, the Migration Agent shall log the error and continue with fallback Terraform generation.
5. When resource mapping cannot be determined, the Migration Agent shall generate a comment in the Terraform code indicating manual review is required.
6. If the target IAC repository path is not writable or is not a valid git repository, the Migration Agent shall display an error message and exit without generating files.
7. When migration completes with warnings, the Migration Agent shall provide a summary of all warnings in the output.
8. The Migration Agent shall validate that all required AWS permissions are available before starting the migration process.

### Requirement 10: Configuration and Customization
**Objective:** As a SRE, I want the system to support configuration options and customization, so that I can adapt the migration process to different environments and requirements.

#### Acceptance Criteria
1. When configuring the migration, the Migration Agent shall support a configuration file (YAML or JSON) for default settings and mappings.
2. When custom resource mappings are provided, the Migration Agent shall use the custom mappings instead of default Pattern Catalog lookups.
3. When target IAC repository path structure is specified, the Migration Agent shall organize generated Terraform files according to the specified structure within the target repository.
4. When filtering options are provided, the Migration Agent shall only migrate resources matching the specified filters (by resource type, stack name, or tags).
5. When dry-run mode is enabled, the Migration Agent shall perform all discovery and analysis operations without generating any files.
6. The Migration Agent shall support configuration of the Pattern Catalog MCP (or API endpoint and authentication) when different from the default Cursor/MCP setup.
7. The Migration Agent shall support configuration of Terraform provider versions and required_providers blocks in generated code.


## Pre-Delivery Quality Gate (Required)

Before presenting generated Terraform, the agent MUST provide:

1. Pattern Resolution Report
   - CFN resource -> selected pattern/module
   - module source + version
   - compatibility rationale

2. Exceptions Report
   - resources not mapped to Pattern Catalog
   - fallback reason
   - manual follow-up needed

3. Validation Report
   - terraform fmt status
   - terraform validate status
   - import readiness status (if applicable)

If Pattern Resolution Report is missing, the migration is incomplete.
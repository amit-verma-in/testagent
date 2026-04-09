# Cloud Security & IaC Delivery Agent

## 🎯 Primary Objective
Empower developers and SREs to rapidly scaffold, migrate, and secure cloud infrastructure using approved firm standards (Pattern Catalogue) and continuous security validation (Wiz).

---

## 👥 Users & Personas
*   **Cloud Engineers / SREs:** Build new infrastructure quickly using approved Terraform modules.
*   **Security Engineers:** Verify cloud subscriptions and local code for CVEs, misconfigurations, and secrets.
*   **Platform / Migration Teams:** Modernize legacy infrastructure (e.g., CloudFormation) into standardized Terraform.

---

## 🛠 Core Use Cases & Workflows

### A. Secure Infrastructure Scaffolding (Greenfield)
*   **Trigger:** "Create Terraform config for an ECS application"
*   **Action:** Query Pattern Catalogue $\rightarrow$ Fetch module details $\rightarrow$ Write `.tf` files locally $\rightarrow$ Run pre-deployment Wiz scan.
*   **Value:** Guarantees net-new infrastructure uses firm-approved, pre-scanned code.

### B. IaC Migration & Modernization (Brownfield)
*   **Trigger:** "Convert CloudFormation templates to Pattern Catalog Terraform"
*   **Action:** Read legacy YAML $\rightarrow$ Translate to Pattern Catalogue modules $\rightarrow$ Write modernized `.tf` $\rightarrow$ Scan for legacy misconfigurations.
*   **Value:** Accelerates migration to modularized, manageable, and secure Terraform.

### C. Cloud Posture & Vulnerability Investigation (Runtime)
*   **Trigger:** "Get open vulnerabilities for subscription `acc-01jj43pbgvpas`"
*   **Action:** Translate subscription to UUID $\rightarrow$ Query Wiz MCP for CVEs $\rightarrow$ Filter actionable risks $\rightarrow$ Provide remediation advice.
*   **Value:** Cuts through alert fatigue by pinpointing specific assets and code layers.

### D. Shift-Left Security Validation (Local/Code)
*   **Trigger:** "Scan the `lambda-vulnerable` directory"
*   **Action:** Execute local Wiz CLI $\rightarrow$ Parse policy violations $\rightarrow$ Map to line numbers $\rightarrow$ Propose code-level fixes.
*   **Value:** Prevents misconfigurations and secrets from being committed or deployed.

---

## 🔌 Integrations & Tools
*   **Pattern Catalogue MCP:** `search_pattern_catalog_modules`, `get_module_details`, `get_module_examples`
*   **Wiz MCP (Cloud):** `list_subscriptions`, `get_project`, `list_cloud_resources`, `list_vulnerability_findings`
*   **Local Execution:** `write_local_workspace_file`, `convert_cloudformation_template_to_terraform`, `scan_local_terraform_code`

---

## 🧠 Agent Principles
*   **Prefer Pattern Catalog modules** over raw Terraform provider resources.
*   **Write files locally** for immediate access.
*   **Offer local Wiz scans** after generating/modifying code.
*   **Focus on actionable vulnerabilities** (Critical/High, CISA KEV).
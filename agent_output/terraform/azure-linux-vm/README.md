# Azure Linux Virtual Machine

This stack provisions an Azure Linux Virtual Machine using standard `azurerm` resources alongside approved Pattern Catalogue modules for networking and resource groups.

**Note:** The Pattern Catalogue currently doesn't provide a dedicated module for Virtual Machines, so the native `azurerm_linux_virtual_machine` resource is used, enforcing standard properties like SSH key authentication and standard managed disks.

## Features
- **Resource Group**: Handled via the approved `resourcegroup-azvm` module.
- **Networking**: Creates a Virtual Network and Subnet using the `vnet-azvm` module, and a Static Public IP using the `publicipaddress-azvm` module.
- **Compute**: Deploys an Ubuntu 22.04 LTS VM utilizing SSH key-based login for security.

## Usage
1. Make sure to update the `admin_ssh_public_key` with your actual SSH public key (e.g., in a `terraform.tfvars` file):
   ```hcl
   admin_ssh_public_key = "ssh-rsa AAAAB3Nza..."
   ```
2. Initialize Terraform: `terraform init`
3. Review the execution plan: `terraform plan`
4. Apply the configuration: `terraform apply`

## Inputs
See `variables.tf` for the full list of customizable inputs including region, sizes, and network prefixes.

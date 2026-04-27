terraform {
  required_version = ">= 1.3.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Approved Resource Group Module
module "rg" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/resourcegroup-azvm/azure"
  version = "0.6.0"

  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# Approved VNET Module
module "vnet" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/vnet-azvm/azure"
  version = "0.8.0"

  resource_group_name = module.rg.name
  location            = var.location
  vnet_name           = var.vnet_name
  address_space       = [var.vnet_address_space]

  subnets = {
    "vm-subnet" = {
      address_prefixes = [var.subnet_address_prefix]
    }
  }

  tags = var.tags
}

# Public IP (Optional, but usually needed for a simple VM example)
module "public_ip" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/publicipaddress-azvm/azure"
  version = "0.2.0"

  name                = "${var.vm_name}-pip"
  resource_group_name = module.rg.name
  location            = var.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

# Network Interface (Native resource since there's no specific NIC module)
resource "azurerm_network_interface" "this" {
  name                = "${var.vm_name}-nic"
  location            = var.location
  resource_group_name = module.rg.name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = module.vnet.subnet_ids["vm-subnet"]
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = module.public_ip.id
  }
}

# Linux Virtual Machine (Native resource since there's no specific VM module in the Pattern Catalogue)
resource "azurerm_linux_virtual_machine" "this" {
  name                = var.vm_name
  resource_group_name = module.rg.name
  location            = var.location
  size                = var.vm_size
  admin_username      = var.admin_username
  tags                = var.tags

  network_interface_ids = [
    azurerm_network_interface.this.id,
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.admin_ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }
}

variable "location" {
  type        = string
  description = "The Azure Region where resources should be created"
  default     = "East US"
}

variable "resource_group_name" {
  type        = string
  description = "The name of the Resource Group"
  default     = "rg-my-app-env"
}

variable "vnet_name" {
  type        = string
  description = "The name of the Virtual Network"
  default     = "vnet-my-app"
}

variable "vnet_address_space" {
  type        = string
  description = "The address space for the VNet"
  default     = "10.0.0.0/16"
}

variable "subnet_address_prefix" {
  type        = string
  description = "The address prefix for the VM subnet"
  default     = "10.0.1.0/24"
}

variable "vm_name" {
  type        = string
  description = "The name of the Virtual Machine"
  default     = "vm-ubuntu-app"
}

variable "vm_size" {
  type        = string
  description = "The size of the Virtual Machine"
  default     = "Standard_B2s"
}

variable "admin_username" {
  type        = string
  description = "The admin username for the VM"
  default     = "azureuser"
}

variable "admin_ssh_public_key" {
  type        = string
  description = "The public SSH key to be used for the VM"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the resources"
  default = {
    Environment = "Development"
    ManagedBy   = "Terraform"
  }
}

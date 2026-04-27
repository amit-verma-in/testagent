output "resource_group_name" {
  description = "The name of the resource group"
  value       = module.rg.name
}

output "virtual_machine_id" {
  description = "The ID of the Virtual Machine"
  value       = azurerm_linux_virtual_machine.this.id
}

output "public_ip_address" {
  description = "The public IP address of the Virtual Machine"
  value       = module.public_ip.ip_address
}

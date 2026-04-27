# Azure SQL Database — ARM / Bicep

Deploy a **logical SQL server**, **single user database**, and **firewall rules** into a resource group.

## Files

| File | Use |
|------|-----|
| `main.bicep` | Bicep source (recommended for iteration) |
| `azuredeploy.json` | ARM template for `az deployment group create` or portal “Custom deployment” |
| `azuredeploy.parameters.json` | Example parameters — **edit** `sqlServerName` and `sqlAdminPassword` before deploy; **do not commit** real passwords (prefer `az deployment group create ... --parameters key=value` or Key Vault references) |

## Deploy

```bash
az group create --name rg-azure-sql-demo --location eastus2

az deployment group create \
  --resource-group rg-azure-sql-demo \
  --template-file azuredeploy.json \
  --parameters @azuredeploy.parameters.json
```

Or with Bicep:

```bash
az deployment group create \
  --resource-group rg-azure-sql-demo \
  --template-file main.bicep \
  --parameters sqlServerName='unique-server-name-2026' sqlAdminLogin='sqladmin' sqlAdminPassword='<StrongP@ss!>'
```

`sqlServerName` must be **globally unique** across Azure. Replace firewall rule IPs for production; `0.0.0.0`–`0.0.0.0` is only for the “Allow Azure services” pattern when combined with the dedicated rule name.

## Security notes

- Prefer **private endpoint** + **Azure AD only** for production (not in this minimal template).
- Use **Key Vault references** or **deployment-time** secure parameters for passwords; rotate regularly.
- Review [Azure SQL security baseline](https://learn.microsoft.com/azure/sql-database/security-best-practice).

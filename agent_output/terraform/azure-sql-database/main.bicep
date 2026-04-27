// Minimal Azure SQL: logical server + database + firewall.
// sqlServerName must be globally unique.

@description('Azure region (defaults to resource group location).')
param location string = resourceGroup().location

@description('Logical SQL server name — globally unique.')
param sqlServerName string

@description('Database name.')
param databaseName string = 'appdb'

@description('SQL administrator login.')
param sqlAdminLogin string

@secure()
@description('SQL administrator password.')
param sqlAdminPassword string

@description('Database SKU name (e.g. Basic, S0, GP_Gen5_2).')
param skuName string = 'Basic'

@description('Database SKU tier (e.g. Basic, Standard, GeneralPurpose).')
param skuTier string = 'Basic'

@description('Add firewall rule so Azure services can reach the server.')
param allowAzureServices bool = true

@description('Optional: allow a single client IPv4 (set both to same IP, or leave 0.0.0.0 to skip extra rule).')
param clientIpStart string = ''

@description('Optional: client IP end (same as start for single IP).')
param clientIpEnd string = ''

resource sqlServer 'Microsoft.Sql/servers@2021-11-01' = {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource firewallAzure 'Microsoft.Sql/servers/firewallRules@2021-11-01' = if (allowAzureServices) {
  parent: sqlServer
  name: 'AllowAllWindowsAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource firewallClient 'Microsoft.Sql/servers/firewallRules@2021-11-01' = if (clientIpStart != '' && clientIpEnd != '') {
  parent: sqlServer
  name: 'ClientIpRule'
  properties: {
    startIpAddress: clientIpStart
    endIpAddress: clientIpEnd
  }
}

resource database 'Microsoft.Sql/servers/databases@2021-11-01' = {
  parent: sqlServer
  name: databaseName
  location: location
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
  }
}

output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output databaseId string = database.id

# AWS RDS Aurora Cluster

This stack deploys a secure, highly available AWS RDS Aurora cluster using the firm's approved Pattern Catalogue module (`rds-aurora`).

## Features
- **Engine Support:** Easily deploy Aurora PostgreSQL or Aurora MySQL.
- **Secure by Default:** Storage encryption is enabled, and the master password is automatically generated and safely stored in AWS SSM Parameter Store.
- **High Availability:** Uses multiple database instances across Availability Zones as defined in the `instances` map.

## Usage
1. Provide the target VPC's security groups and subnets via a `terraform.tfvars` file:
   ```hcl
   vpc_security_group_ids = ["sg-0123456789abcdef0"]
   subnets                = ["subnet-01234567", "subnet-89abcdef"]
   ```
2. Initialize Terraform: `terraform init`
3. Review the execution plan: `terraform plan`
4. Apply the configuration: `terraform apply`

## Inputs

| Name | Description | Default | Required |
|------|-------------|---------|:--------:|
| `cluster_name` | Name used across resources created | `my-aurora-cluster` | No |
| `engine` | Database engine to use (`aurora-postgresql`, `aurora-mysql`, etc.) | `aurora-postgresql` | No |
| `engine_version` | The database engine version | `15.4` | No |
| `database_name` | Name for an automatically created database on cluster creation | `mydatabase` | No |
| `master_username` | Username for the master DB user | `root` | No |
| `vpc_security_group_ids` | List of VPC security groups to associate to the cluster | n/a | **Yes** |
| `subnets` | List of subnet IDs used by database subnet group created | n/a | **Yes** |
| `instances` | Map of cluster instances and their overriding attributes | 2 instances (`db.r6g.large`) | No |

## Outputs
- `cluster_endpoint`: The primary writer endpoint.
- `cluster_reader_endpoint`: The read-only endpoint, automatically load-balanced across replicas.
- `cluster_master_username`: The master DB user.
- `cluster_database_name`: The initial database created.
- `cluster_arn`: Amazon Resource Name (ARN) of the cluster.

variable "cluster_name" {
  type        = string
  description = "Name used across resources created"
  default     = "my-aurora-cluster"
}

variable "engine" {
  type        = string
  description = "The name of the database engine to be used for this DB cluster. Valid Values: aurora, aurora-mysql, aurora-postgresql"
  default     = "aurora-postgresql"
}

variable "engine_version" {
  type        = string
  description = "The database engine version"
  default     = "15.4"
}

variable "vpc_security_group_ids" {
  type        = list(string)
  description = "List of VPC security groups to associate to the cluster"
}

variable "subnets" {
  type        = list(string)
  description = "List of subnet IDs used by database subnet group created"
}

variable "instances" {
  description = "Map of cluster instances and any specific/overriding attributes to be created"
  type        = any
  default = {
    1 = {
      instance_class = "db.r6g.large"
    }
    2 = {
      instance_class = "db.r6g.large"
    }
  }
}

variable "database_name" {
  type        = string
  description = "Name for an automatically created database on cluster creation"
  default     = "mydatabase"
}

variable "master_username" {
  type        = string
  description = "Username for the master DB user"
  default     = "root"
}

terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.23, < 7.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- CloudWatch Log Group ---
module "cloudwatch_log_group" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/cloudwatch/aws//modules/log-group"
  version = "~> 1.0"

  name              = "/ecs/${var.environment_name}"
  retention_in_days = 30
}

# --- IAM Roles ---
module "ecs_execution_role" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/iam/aws//modules/ecs-execution-role"
  version = "~> 1.0"
  name    = "${var.environment_name}-ecs-exec-${var.stack_name}"
}

module "ecs_task_role" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/iam/aws//modules/ecs-task-role"
  version = "~> 1.0"
  name    = "${var.environment_name}-ecs-task-${var.stack_name}"
}

# --- Security Groups ---
resource "aws_security_group" "alb_security_group" {
  description = "ALB HTTP for ${var.environment_name}"
  vpc_id      = var.vpc_id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "service_security_group" {
  description = "ECS tasks for ${var.environment_name}"
  vpc_id      = var.vpc_id
  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_security_group.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Application Load Balancer ---
module "alb" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/alb/aws"
  version = "~> 3.0"

  name               = "${var.environment_name}-alb"
  vpc_id             = var.vpc_id
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb_security_group.id]
  internal           = false
  load_balancer_type = "application"

  target_groups = [
    {
      name        = "${var.environment_name}-tg"
      port        = var.container_port
      protocol    = "HTTP"
      target_type = "ip"
      health_check = {
        path = "/"
      }
    }
  ]

  http_tcp_listeners = [
    {
      port               = 80
      protocol           = "HTTP"
      target_group_index = 0
    }
  ]
}

# --- ECS Cluster ---
module "ecs_cluster" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/ecs/aws//modules/cluster"
  version = "~> 3.2"

  name = "${var.environment_name}-cluster"

  fargate_capacity_providers = {
    FARGATE = {
      default_capacity_provider_strategy = {
        weight = 100
      }
    }
  }
}

# --- Task Definition ---
module "ecs_task_definition" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/ecs/aws//modules/task-definition"
  version = "~> 3.2"

  family                   = "${var.environment_name}-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory

  execution_role_arn = module.ecs_execution_role.arn
  task_role_arn      = module.ecs_task_role.arn

  container_definitions = {
    "app" = {
      image     = var.container_image
      essential = true
      port_mappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]
      log_configuration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = module.cloudwatch_log_group.log_group_name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  }
}

# --- ECS Service ---
module "ecs_service" {
  source  = "terraform.mckinsey.cloud/FIRM-TF-MODULES/ecs/aws//modules/service"
  version = "~> 3.2"

  name            = "${var.environment_name}-svc"
  cluster_arn     = module.ecs_cluster.arn
  task_definition = module.ecs_task_definition.arn
  desired_count   = var.desired_count

  capacity_provider_strategy = {
    FARGATE = {
      weight = 100
      base   = 1
    }
  }

  network_configuration = {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.service_security_group.id]
    assign_public_ip = false
  }

  load_balancer = [
    {
      target_group_arn = module.alb.target_group_arns[0]
      container_name   = "app"
      container_port   = var.container_port
    }
  ]
}

resource "aws_ecs_task_definition" "ecs_task_definition" {
  family                   = "webapp"
  network_mode             = "awsvpc"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = "arn:aws:iam::781581113404:role/LabRole"
  cpu                      = 1024
  memory                   = 512

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = "webapp-ctr"
      image     = "${aws_ecr_repository.app_repo.repository_url}:latest"
      cpu       = 1024
      memory    = 256
      essential = true

      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/webapp"
          awslogs-region        = "us-east-1"
          awslogs-stream-prefix = "ecs"
        }
      }

      "environment": [
        {
          "name": "SERVICE_NAME",
          "value": "supermercado-api-prod"
        },
        {
          "name": "SIGNOZ_OTLP_URL",
          "value": "https://ingest.us.signoz.cloud:443"
        },
        {
          "name": "SIGNOZ_INGEST_KEY",
          "value": "2ceecf63-9045-4206-97a7-d75bb2196313"
        },
        {
          "name": "DATABASE_URL",
          "value": "cockroachdb://admin@10.0.1.20:26257/defaultdb?sslmode=disable"
        },
        {
          "name": "SQLALCHEMY_DATABASE_URI",
          "value": "cockroachdb://admin@10.0.1.20:26257/defaultdb?sslmode=disable"
        }
      ]
    }
  ])
}

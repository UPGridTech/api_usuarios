resource "aws_alb" "ec2_alb" {
  name               = "ec2-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.security_group.id]
  subnets = [
    aws_subnet.sub-pub1.id,
    aws_subnet.sub-pub2.id
  ]

  tags = {
    name = "ecs-alb"
  }
}

resource "aws_lb_target_group" "ec2_tg" {
  name        = "tg-webapp"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # <- CORREÇÃO CRUCIAL
  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}


resource "aws_lb_listener" "ec2_alb_listener" {
  load_balancer_arn = aws_alb.ec2_alb.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward" # ecaminha tráfeto para o TARGET GROUP
    target_group_arn = aws_lb_target_group.ec2_tg.arn
  }
}

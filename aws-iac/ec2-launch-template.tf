resource "aws_launch_template" "ec2_lt" {
  name_prefix = "ec2-template"
  image_id    = "ami-0c45946ade6066f3d"


  instance_type = "t2.micro"

  key_name               = "vockey"
  vpc_security_group_ids = [aws_security_group.security_group.id]
  iam_instance_profile {
    name = "LabInstanceProfile"
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "esc_instance"
    }
  }
  user_data = base64encode(templatefile("${path.module}/ecs.sh", {
    signoz_ingestion_key = var.signoz_ingestion_key
  }))
}



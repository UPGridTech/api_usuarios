resource "aws_instance" "cockroach" {
  ami           = "ami-0c7217cdde317cfec"
  instance_type = "t3.micro"
  key_name      = "vockey"
  subnet_id     = aws_subnet.sub-priv1.id

  vpc_security_group_ids = [aws_security_group.cockroach_sg.id]

  user_data = file("${path.module}/cockroach.sh")

  tags = {
    Name = "cockroach-db"
  }
}

output "cockroach_public_ip" {
  value = aws_instance.cockroach.private_ip
}

output "instance_id" {
  value = var.enable_controller ? aws_instance.controller[0].id : null
}

output "private_ip" {
  value = var.enable_controller ? aws_instance.controller[0].private_ip : null
}

output "public_ip" {
  value = var.enable_controller ? aws_instance.controller[0].public_ip : null
}

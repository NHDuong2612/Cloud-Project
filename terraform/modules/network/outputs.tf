output "vpc_id" {
  value = var.enable_network ? aws_vpc.this[0].id : null
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_db_subnet_ids" {
  value = aws_subnet.private_db[*].id
}

output "availability_zones_used" {
  value = local.azs
}

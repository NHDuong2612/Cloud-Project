output "vpc_id" {
  description = "VPC ID (null until enable_network)"
  value       = var.enable_network ? aws_vpc.this[0].id : null
}

output "vpc_cidr_block" {
  description = "VPC CIDR"
  value       = var.enable_network ? aws_vpc.this[0].cidr_block : null
}

output "public_subnet_id" {
  description = "Public subnet for controller/target"
  value       = var.enable_network ? aws_subnet.public[0].id : null
}

output "public_subnet_az" {
  description = "AZ of the public subnet"
  value       = var.enable_network ? aws_subnet.public[0].availability_zone : null
}

output "private_db_subnet_ids" {
  description = "Two private subnet IDs for RDS DB subnet group"
  value       = var.enable_network ? aws_subnet.private_db[*].id : []
}

output "private_db_subnet_azs" {
  description = "AZs of the private DB subnets"
  value       = var.enable_network ? aws_subnet.private_db[*].availability_zone : []
}

output "igw_id" {
  description = "Internet Gateway ID"
  value       = var.enable_network ? aws_internet_gateway.this[0].id : null
}

output "public_route_table_id" {
  value = var.enable_network ? aws_route_table.public[0].id : null
}

output "private_db_route_table_ids" {
  value = var.enable_network ? aws_route_table.private_db[*].id : []
}

output "availability_zones_used" {
  value = var.enable_network ? local.azs : []
}

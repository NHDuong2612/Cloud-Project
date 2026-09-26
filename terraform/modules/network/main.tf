# Module: network
# Task 5 — VPC + public subnet (controller/target) + 2 private DB subnets (2 AZs)
#
# Cost note: VPC/subnet/IGW/route table are free.
# Intentionally NO NAT Gateway (~$32+/month) — private DB subnets have no Internet route.
# Controller/target in public subnet reach AWS APIs (S3/SSM) via IGW + public IP / VPC endpoints later.

data "aws_availability_zones" "available" {
  count = var.enable_network ? 1 : 0
  state = "available"
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  # Prefer explicit AZs from tfvars; otherwise first 2 available in the region.
  azs = var.enable_network ? (
    length(var.availability_zones) >= 2
    ? slice(var.availability_zones, 0, 2)
    : slice(data.aws_availability_zones.available[0].names, 0, 2)
  ) : []
}

resource "aws_vpc" "this" {
  count = var.enable_network ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  count = var.enable_network ? 1 : 0

  vpc_id = aws_vpc.this[0].id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-igw"
  })
}

# Public subnet — controller + target EC2 (demo: outbound via IGW, no NAT cost)
resource "aws_subnet" "public" {
  count = var.enable_network ? 1 : 0

  vpc_id                  = aws_vpc.this[0].id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = local.azs[0]
  map_public_ip_on_launch = true

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-subnet-public-a"
    Tier = "public"
  })
}

# Private DB subnets — RDS only (2 AZs required by aws_db_subnet_group)
resource "aws_subnet" "private_db" {
  count = var.enable_network ? 2 : 0

  vpc_id                  = aws_vpc.this[0].id
  cidr_block              = var.private_db_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = false

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-subnet-db-${count.index == 0 ? "a" : "b"}"
    Tier = "private-db"
  })
}

# Public route table: default route → Internet Gateway
resource "aws_route_table" "public" {
  count = var.enable_network ? 1 : 0

  vpc_id = aws_vpc.this[0].id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-rtb-public"
  })
}

resource "aws_route" "public_internet" {
  count = var.enable_network ? 1 : 0

  route_table_id         = aws_route_table.public[0].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this[0].id
}

resource "aws_route_table_association" "public" {
  count = var.enable_network ? 1 : 0

  subnet_id      = aws_subnet.public[0].id
  route_table_id = aws_route_table.public[0].id
}

# Private DB route tables: local VPC traffic only (no 0.0.0.0/0 → keeps RDS off the Internet)
resource "aws_route_table" "private_db" {
  count = var.enable_network ? 2 : 0

  vpc_id = aws_vpc.this[0].id

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-rtb-db-${count.index == 0 ? "a" : "b"}"
  })
}

resource "aws_route_table_association" "private_db" {
  count = var.enable_network ? 2 : 0

  subnet_id      = aws_subnet.private_db[count.index].id
  route_table_id = aws_route_table.private_db[count.index].id
}

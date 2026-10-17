# Shared network foundation for CloudHub templates that need a VPC.
# Public subnets support a two-AZ ALB; private subnets support RDS.
# Session resources must be tracked and removed by CloudHub's own lifecycle.

data "aws_availability_zones" "available" {
  count = var.enable_network ? 1 : 0
  state = "available"
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  azs = var.enable_network ? (
    length(var.availability_zones) == 2
    ? var.availability_zones
    : slice(data.aws_availability_zones.available[0].names, 0, 2)
  ) : []
}

resource "aws_vpc" "this" {
  count = var.enable_network ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.common_tags, { Name = "${local.name_prefix}-vpc" })
}

resource "aws_internet_gateway" "this" {
  count  = var.enable_network ? 1 : 0
  vpc_id = aws_vpc.this[0].id

  tags = merge(var.common_tags, { Name = "${local.name_prefix}-igw" })
}

resource "aws_subnet" "public" {
  count = var.enable_network ? 2 : 0

  vpc_id                  = aws_vpc.this[0].id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = false

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-public-${count.index + 1}"
    Tier = "public"
  })
}

resource "aws_subnet" "private_db" {
  count = var.enable_network ? 2 : 0

  vpc_id                  = aws_vpc.this[0].id
  cidr_block              = var.private_db_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = false

  tags = merge(var.common_tags, {
    Name = "${local.name_prefix}-db-${count.index + 1}"
    Tier = "private-db"
  })
}

resource "aws_route_table" "public" {
  count  = var.enable_network ? 1 : 0
  vpc_id = aws_vpc.this[0].id

  tags = merge(var.common_tags, { Name = "${local.name_prefix}-public-rt" })
}

resource "aws_route" "public_internet" {
  count = var.enable_network ? 1 : 0

  route_table_id         = aws_route_table.public[0].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this[0].id
}

resource "aws_route_table_association" "public" {
  count = var.enable_network ? 2 : 0

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table" "private_db" {
  count  = var.enable_network ? 2 : 0
  vpc_id = aws_vpc.this[0].id

  tags = merge(var.common_tags, { Name = "${local.name_prefix}-db-${count.index + 1}-rt" })
}

resource "aws_route_table_association" "private_db" {
  count = var.enable_network ? 2 : 0

  subnet_id      = aws_subnet.private_db[count.index].id
  route_table_id = aws_route_table.private_db[count.index].id
}

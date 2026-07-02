terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ---------------------------------------------------------------------------
# Hosted zone
# ---------------------------------------------------------------------------
resource "aws_route53_zone" "vr4deaf" {
  name    = var.domain
  comment = "vr4deaf.org – migrated from Google-hosted DNS"

  tags = merge(var.tags, {
    Domain = var.domain
  })
}

# ---------------------------------------------------------------------------
# Root A record  (replace values with real IP(s) from Google export)
# ---------------------------------------------------------------------------
resource "aws_route53_record" "root_a" {
  zone_id = aws_route53_zone.vr4deaf.zone_id
  name    = var.domain
  type    = "A"
  ttl     = var.ttl

  records = var.root_ipv4_addresses
}

# Root AAAA (optional – remove block if no IPv6)
resource "aws_route53_record" "root_aaaa" {
  count   = length(var.root_ipv6_addresses) > 0 ? 1 : 0
  zone_id = aws_route53_zone.vr4deaf.zone_id
  name    = var.domain
  type    = "AAAA"
  ttl     = var.ttl

  records = var.root_ipv6_addresses
}

# ---------------------------------------------------------------------------
# www CNAME
# ---------------------------------------------------------------------------
resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.vr4deaf.zone_id
  name    = "www.${var.domain}"
  type    = "CNAME"
  ttl     = var.ttl

  records = [var.www_target]
}

# ---------------------------------------------------------------------------
# Mail (MX) records
# ---------------------------------------------------------------------------
resource "aws_route53_record" "mx" {
  count   = length(var.mx_records) > 0 ? 1 : 0
  zone_id = aws_route53_zone.vr4deaf.zone_id
  name    = var.domain
  type    = "MX"
  ttl     = var.ttl

  records = var.mx_records
}

# ---------------------------------------------------------------------------
# SPF / DKIM / DMARC and other TXT records
# ---------------------------------------------------------------------------
resource "aws_route53_record" "txt_root" {
  count   = length(var.root_txt_records) > 0 ? 1 : 0
  zone_id = aws_route53_zone.vr4deaf.zone_id
  name    = var.domain
  type    = "TXT"
  ttl     = var.ttl

  records = var.root_txt_records
}

# ---------------------------------------------------------------------------
# Subdomain remaps  (one record per entry in var.subdomain_remaps)
# ---------------------------------------------------------------------------
resource "aws_route53_record" "subdomain" {
  for_each = { for s in var.subdomain_remaps : s.name => s }

  zone_id = aws_route53_zone.vr4deaf.zone_id
  name    = "${each.key}.${var.domain}"
  type    = each.value.type
  ttl     = lookup(each.value, "ttl", var.ttl)
  records = each.value.records
}

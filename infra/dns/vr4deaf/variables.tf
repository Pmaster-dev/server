variable "aws_region" {
  description = "AWS region for the provider (Route53 is global but a region is still required)."
  type        = string
  default     = "us-east-1"
}

variable "domain" {
  description = "Apex domain managed by this hosted zone."
  type        = string
  default     = "vr4deaf.org"
}

variable "ttl" {
  description = "Default TTL (seconds) for all records. Set low (60) before cutover, raise after."
  type        = number
  default     = 300
}

variable "root_ipv4_addresses" {
  description = "IPv4 addresses for the root A record."
  type        = list(string)
  default     = ["76.76.21.21"]
}

variable "root_ipv6_addresses" {
  description = "IPv6 addresses for the root AAAA record. Leave empty to skip."
  type        = list(string)
  default     = []
}

variable "www_target" {
  description = "CNAME target for www.vr4deaf.org. Vercel default: cname.vercel-dns.com"
  type        = string
  default     = "cname.vercel-dns.com"
}

variable "mx_records" {
  description = "MX records in priority-hostname format, e.g. [\"10 mail.example.com.\"]."
  type        = list(string)
  default     = []
}

variable "root_txt_records" {
  description = "TXT records for the apex domain (SPF, site-verification, DMARC, etc.)."
  type        = list(string)
  default     = []
}

variable "subdomain_remaps" {
  description = <<-EOT
    List of subdomain records to create. Each object must have:
      name    – subdomain label (e.g. "app", "api")
      type    – DNS record type (A | AAAA | CNAME | MX | TXT)
      records – list of values for the record
      ttl     – (optional) override default TTL
  EOT
  type = list(object({
    name    = string
    type    = string
    records = list(string)
    ttl     = optional(number)
  }))
  default = []
}

variable "tags" {
  description = "AWS tags to apply to the hosted zone."
  type        = map(string)
  default = {
    Project     = "VR4Deaf"
    ManagedBy   = "Terraform"
    Environment = "production"
  }
}

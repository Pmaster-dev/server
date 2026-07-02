variable "aws_region" {
  description = "AWS region for the provider (Route53 is global but a region is still required)."
  type        = string
  default     = "us-east-1"
}

# ── Example tfvars to fill in after Google DNS export ─────────────────────
# domain               = "vr4deaf.org"
# ttl                  = 60   # use 60 during cutover, raise to 300+ after
#
# root_ipv4_addresses  = ["203.0.113.10"]
# www_target           = "vr4deaf.org"
#
# mx_records = [
#   "1 aspmx.l.google.com.",
#   "5 alt1.aspmx.l.google.com.",
#   "10 alt2.aspmx.l.google.com.",
# ]
#
# root_txt_records = [
#   "v=spf1 include:_spf.google.com ~all",
#   "google-site-verification=<token>",
# ]
#
# subdomain_remaps = [
#   { name = "app",  type = "CNAME", records = ["app-prod.example.com."] },
#   { name = "api",  type = "A",     records = ["203.0.113.20"]          },
#   { name = "mail", type = "CNAME", records = ["ghs.google.com."]       },
# ]

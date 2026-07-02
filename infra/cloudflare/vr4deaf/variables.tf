variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for vr4deaf.org (shown in the Cloudflare dashboard Overview tab)."
  type        = string
}

variable "domain" {
  description = "Apex domain managed by this module."
  type        = string
  default     = "vr4deaf.org"
}

# ---------------------------------------------------------------------------
# Vercel record targets (do not change unless Vercel changes their IPs/CNAMEs)
# ---------------------------------------------------------------------------
variable "vercel_apex_ip" {
  description = "Vercel's shared Anycast IP for apex A records."
  type        = string
  default     = "76.76.21.21"
}

variable "vercel_cname_target" {
  description = "CNAME target for www and subdomain records pointing to Vercel."
  type        = string
  default     = "cname.vercel-dns.com"
}

# ---------------------------------------------------------------------------
# Proxy / TTL
# ---------------------------------------------------------------------------
variable "proxied" {
  description = "Enable Cloudflare proxy (orange cloud). Set false during initial Vercel verification."
  type        = bool
  default     = false
}

variable "ttl" {
  description = "TTL in seconds. Cloudflare forces 1 (auto) when proxied=true."
  type        = number
  default     = 300
}

# ---------------------------------------------------------------------------
# Mail
# ---------------------------------------------------------------------------
variable "mx_records" {
  description = "MX records in priority-hostname format, e.g. [\"10 aspmx.l.google.com\"]."
  type        = list(string)
  default     = []
}

variable "root_txt_records" {
  description = "TXT records for the apex domain (SPF, DKIM, site-verification, DMARC, etc.)."
  type        = list(string)
  default     = []
}

# ---------------------------------------------------------------------------
# Subdomain remaps
# ---------------------------------------------------------------------------
variable "subdomain_records" {
  description = <<-EOT
    Extra subdomain records beyond apex and www. Each object:
      name    – subdomain label ("app", "api", "mail", …)
      type    – "A" | "AAAA" | "CNAME" | "TXT" | "MX"
      value   – single record value
      proxied – (optional) override module-level proxied setting
      ttl     – (optional) override module-level ttl
  EOT
  type = list(object({
    name    = string
    type    = string
    value   = string
    proxied = optional(bool)
    ttl     = optional(number)
  }))
  default = []
}

# ---------------------------------------------------------------------------
# Cloudflare zone settings
# ---------------------------------------------------------------------------
variable "ssl_mode" {
  description = "Cloudflare SSL mode: off | flexible | full | strict."
  type        = string
  default     = "full"

  validation {
    condition     = contains(["off", "flexible", "full", "strict"], var.ssl_mode)
    error_message = "ssl_mode must be one of: off, flexible, full, strict."
  }
}

variable "always_use_https" {
  description = "Redirect all HTTP traffic to HTTPS."
  type        = bool
  default     = true
}

variable "min_tls_version" {
  description = "Minimum TLS version Cloudflare will accept."
  type        = string
  default     = "1.2"
}

# ---------------------------------------------------------------------------
# Zone settings (SSL, HTTPS redirect, TLS floor)
# ---------------------------------------------------------------------------
resource "cloudflare_zone_settings_override" "vr4deaf" {
  zone_id = var.cloudflare_zone_id

  settings {
    ssl              = var.ssl_mode
    always_use_https = var.always_use_https ? "on" : "off"
    min_tls_version  = var.min_tls_version
    # Disable automatic HTTPS rewrites while Vercel cert is being issued
    automatic_https_rewrites = "off"
  }
}

# ---------------------------------------------------------------------------
# Apex A record → Vercel
# ---------------------------------------------------------------------------
resource "cloudflare_record" "apex_a" {
  zone_id = var.cloudflare_zone_id
  name    = var.domain
  type    = "A"
  value   = var.vercel_apex_ip
  proxied = var.proxied
  ttl     = var.proxied ? 1 : var.ttl
}

# ---------------------------------------------------------------------------
# www CNAME → Vercel
# ---------------------------------------------------------------------------
resource "cloudflare_record" "www" {
  zone_id = var.cloudflare_zone_id
  name    = "www"
  type    = "CNAME"
  value   = var.vercel_cname_target
  proxied = var.proxied
  ttl     = var.proxied ? 1 : var.ttl
}

# ---------------------------------------------------------------------------
# MX records
# ---------------------------------------------------------------------------
resource "cloudflare_record" "mx" {
  for_each = {
    for idx, rec in var.mx_records : tostring(idx) => rec
  }

  zone_id  = var.cloudflare_zone_id
  name     = var.domain
  type     = "MX"
  # MX value format: "10 mail.example.com" → split priority from hostname
  value    = trimspace(regex("\\d+\\s+(.*)", each.value))
  priority = tonumber(regex("^(\\d+)", each.value))
  proxied  = false # MX records must never be proxied
  ttl      = var.ttl
}

# ---------------------------------------------------------------------------
# Root TXT records (SPF, DKIM, DMARC, site-verification)
# ---------------------------------------------------------------------------
resource "cloudflare_record" "txt_root" {
  for_each = { for idx, v in var.root_txt_records : tostring(idx) => v }

  zone_id = var.cloudflare_zone_id
  name    = var.domain
  type    = "TXT"
  value   = each.value
  proxied = false
  ttl     = var.ttl
}

# ---------------------------------------------------------------------------
# Subdomain records (flexible list)
# ---------------------------------------------------------------------------
resource "cloudflare_record" "subdomain" {
  for_each = { for s in var.subdomain_records : s.name => s }

  zone_id = var.cloudflare_zone_id
  name    = each.key
  type    = each.value.type
  value   = each.value.value
  proxied = coalesce(each.value.proxied, var.proxied)
  ttl     = coalesce(each.value.ttl, var.proxied ? 1 : var.ttl)
}

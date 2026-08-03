# vr4deaf.org — DNS Migration Runbook (Cloudflare → Route53)

## Overview

`vr4deaf.org` was previously managed by **Cloudflare DNS** with **Vercel** as the app host.  
This runbook covers the migration to **AWS Route53** as the new DNS authority, keeping Vercel as the origin.

- **Past (current):** Cloudflare manages DNS → Vercel hosts app  
- **New (target):** AWS Route53 manages DNS → Vercel hosts app  

Terraform modules:

| State | Module path |
|---|---|
| Past (Cloudflare) | `infra/cloudflare/vr4deaf/` |
| New (Route53) | `infra/dns/vr4deaf/` |

---

## Phase 0 — Prerequisites

| Item | Status |
|---|---|
| AWS credentials configured (`aws configure` or IAM role) | ☐ |
| Terraform ≥ 1.5 installed | ☐ |
| Access to Cloudflare dashboard for `vr4deaf.org` | ☐ |
| Access to domain registrar (to update nameservers) | ☐ |
| Current DNS records exported from Cloudflare (Phase 1) | ☐ |

---

## Phase 1 — Export current DNS from Cloudflare

1. Cloudflare dashboard → `vr4deaf.org` → **DNS → Records**.
2. Click **Export** (downloads a BIND zone file) or copy each record manually.
3. Fill in the table below before touching anything.

### Current DNS records (fill in before migration)

| Subdomain | Type | TTL | Value(s) | Proxied? |
|---|---|---|---|---|
| `@` (root) | A | | `76.76.21.21` | ☐ |
| `www` | CNAME | | `cname.vercel-dns.com` | ☐ |
| `@` | MX | | | No |
| `@` | TXT (SPF) | | | No |
| `@` | TXT (site-verify) | | | No |
| `_dmarc` | TXT | | | No |
| *(add rows)* | | | | |

---

## Phase 2 — Populate Route53 Terraform variables

```bash
cd infra/dns/vr4deaf
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars and fill in your values
```

Key variables (defaults already set for Vercel):

| Variable | Default | Notes |
|---|---|---|
| `root_ipv4_addresses` | `["76.76.21.21"]` | Vercel apex IP – no change needed |
| `www_target` | `"cname.vercel-dns.com"` | Vercel CNAME – no change needed |
| `mx_records` | `[]` | Copy from Cloudflare export |
| `root_txt_records` | `[]` | Copy SPF/DKIM/verification from export |
| `subdomain_remaps` | `[]` | Add any extra subdomains |
| `ttl` | `300` | Set to `60` during cutover window |

---

## Phase 3 — Create Route53 hosted zone (dry run first)

```bash
cd infra/dns/vr4deaf
terraform init
terraform plan    # preview – no writes yet
terraform apply   # creates hosted zone + all records
```

After apply, note the four **Route53 nameservers** from the output:

```
nameservers = [
  "ns-XXXX.awsdns-XX.org.",
  "ns-XXXX.awsdns-XX.co.uk.",
  "ns-XXXX.awsdns-XX.net.",
  "ns-XXXX.awsdns-XX.com.",
]
```

> **Do not update the registrar yet.** Verify all records look correct in the AWS Console first.

---

## Phase 4 — Lower TTLs in Cloudflare

In Cloudflare DNS, change all active record TTLs to **60 seconds**.  
Wait 1 minute (one TTL cycle) before cutting over.

---

## Phase 5 — Switch nameservers at the registrar

1. Log in to the domain registrar managing `vr4deaf.org`.
2. Replace the Cloudflare nameservers with the four Route53 NS values from Phase 3.
3. Save. Propagation typically completes in 5–30 minutes (up to 48 h worst case).

---

## Phase 6 — Validate after propagation

```bash
# Root domain
dig @8.8.8.8 vr4deaf.org A

# www
dig @8.8.8.8 www.vr4deaf.org CNAME

# Mail
dig @8.8.8.8 vr4deaf.org MX
dig @8.8.8.8 vr4deaf.org TXT

# Each subdomain
dig @8.8.8.8 app.vr4deaf.org
```

| Check | Expected | Status |
|---|---|---|
| Root A → `76.76.21.21` | Vercel IP | ☐ |
| www CNAME → `cname.vercel-dns.com` | Vercel CNAME | ☐ |
| MX records present | Priority + hostname | ☐ |
| SPF TXT present | `v=spf1 …` | ☐ |
| SSL cert valid (HTTPS) | No browser warning | ☐ |
| Email send/receive | Test round-trip | ☐ |
| Vercel project domain shows "Valid Configuration" | Green in Vercel | ☐ |
| Each subdomain resolves correctly | Correct target | ☐ |

---

## Phase 7 — Clean up Cloudflare

Only after **all** Phase 6 checks pass:

1. Remove the `vr4deaf.org` zone from Cloudflare (or leave it inactive).
2. The `infra/cloudflare/vr4deaf/` Terraform module is now historical reference — run `terraform destroy` inside it to clean up any managed Cloudflare resources.
3. Raise `ttl` in Route53 `terraform.tfvars` back to `300` and run `terraform apply`.

---

## Subdomain remap reference

Add subdomains to `subdomain_remaps` in `infra/dns/vr4deaf/terraform.tfvars`:

```hcl
subdomain_remaps = [
  # Vercel-hosted sub-apps
  { name = "app",  type = "CNAME", records = ["cname.vercel-dns.com."] },
  # Direct server
  { name = "api",  type = "A",     records = ["<api-server-ip>"]       },
  # Mail passthrough (must never be CNAME)
  { name = "mail", type = "CNAME", records = ["ghs.googlemail.com."]   },
]
```

---

## Rollback

Revert the registrar nameservers back to the Cloudflare NS values.  
Cloudflare DNS will resume serving within the 60-second TTL set in Phase 4.

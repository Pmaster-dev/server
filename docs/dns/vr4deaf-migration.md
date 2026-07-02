# vr4deaf.org — DNS Migration Runbook (Google → Route53)

## Overview

This runbook covers the safe migration of `vr4deaf.org` from Google-hosted DNS to AWS Route53.  
The Terraform module lives at `infra/dns/vr4deaf/`.

---

## Phase 0 — Prerequisites

| Item | Status |
|---|---|
| AWS credentials configured (`aws configure` or IAM role) | ☐ |
| Terraform ≥ 1.5 installed | ☐ |
| Access to Google Domains / registrar for `vr4deaf.org` | ☐ |
| Current DNS records exported (see Phase 1) | ☐ |

---

## Phase 1 — Export current DNS from Google

1. Open [Google Domains](https://domains.google.com) → select `vr4deaf.org` → **DNS**.
2. Copy every record into the table below before touching anything.

### Current DNS records (fill in before migration)

| Subdomain | Type | TTL | Value(s) |
|---|---|---|---|
| `@` (root) | A | | |
| `@` (root) | AAAA | | |
| `www` | CNAME | | |
| `@` | MX | | |
| `@` | TXT (SPF) | | |
| `@` | TXT (site-verify) | | |
| `_dmarc` | TXT | | |
| *(add rows)* | | | |

---

## Phase 2 — Populate Terraform variables

Edit `infra/dns/vr4deaf/provider.tf` (the commented `tfvars` block at the bottom) or create a
`terraform.tfvars` file in the same directory using the records captured above.

Key variables to set:

| Variable | Description |
|---|---|
| `root_ipv4_addresses` | IP(s) for the root A record |
| `root_ipv6_addresses` | IP(s) for AAAA (omit if none) |
| `www_target` | CNAME target for `www` |
| `mx_records` | MX records with priority prefix |
| `root_txt_records` | SPF, site-verification, etc. |
| `subdomain_remaps` | List of subdomain records (see below) |
| `ttl` | Set to `60` before cutover |

---

## Phase 3 — Subdomain remap plan

Define each subdomain's destination before the cutover.

| Subdomain | Current target | New target | Action |
|---|---|---|---|
| `www` | *(Google)* | | `CNAME → <new host>` |
| `app` | | | |
| `api` | | | |
| `mail` | | | |
| *(add rows)* | | | |

**Action key:**
- `keep` — same target, just re-create in Route53
- `remap` — new target endpoint
- `redirect` — HTTP 301 (needs redirect infrastructure)
- `decommission` — do not create in Route53

---

## Phase 4 — Create Route53 hosted zone (dry run first)

```bash
cd infra/dns/vr4deaf

# Preview changes (no writes)
terraform init
terraform plan

# Apply – creates the hosted zone and all records
terraform apply
```

After `apply`, note the four **nameservers** from the Terraform output:

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

## Phase 5 — Lower TTLs at Google DNS

In Google Domains, change all active record TTLs to **60 seconds**.  
Wait one full TTL cycle (1 minute) before proceeding.

---

## Phase 6 — Switch nameservers at the registrar

1. Log in to the domain registrar managing `vr4deaf.org`.
2. Replace the existing Google nameservers with the four Route53 NS values from Phase 4.
3. Save. Propagation typically completes within 5–30 minutes (up to 48 h worst case).

---

## Phase 7 — Validation checklist

Run these checks after propagation:

```bash
# Root domain
dig @8.8.8.8 vr4deaf.org A
dig @8.8.8.8 vr4deaf.org AAAA

# www
dig @8.8.8.8 www.vr4deaf.org CNAME

# Mail
dig @8.8.8.8 vr4deaf.org MX
dig @8.8.8.8 vr4deaf.org TXT

# Each subdomain
dig @8.8.8.8 app.vr4deaf.org
dig @8.8.8.8 api.vr4deaf.org
```

| Check | Expected | Status |
|---|---|---|
| Root A resolves | Correct IP | ☐ |
| www resolves | Correct CNAME/IP | ☐ |
| MX records present | Priority + hostname | ☐ |
| SPF TXT present | `v=spf1 ...` | ☐ |
| Site verification TXT | Token visible | ☐ |
| SSL cert valid (HTTPS) | No browser warning | ☐ |
| Email send/receive | Test round-trip | ☐ |
| Each subdomain resolves | Correct target | ☐ |

---

## Phase 8 — Clean up Google DNS

Only after **all** checks in Phase 7 pass:

1. Remove the custom DNS records from Google Domains.
2. Optionally transfer domain registration to AWS Route53 (separate process).
3. Raise `ttl` in `terraform.tfvars` back to `300` and run `terraform apply`.

---

## Rollback

If something breaks during cutover, revert the registrar nameservers back to the Google NS values.  
Propagation to the old DNS will complete within the 60-second TTL set in Phase 5.

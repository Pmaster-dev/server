# vr4deaf.org — Cloudflare + Vercel Setup Runbook

This runbook walks through configuring `vr4deaf.org` with **Cloudflare as DNS manager**
and **Vercel as the app host**.  
The Terraform module lives at `infra/cloudflare/vr4deaf/`.

---

## Architecture

```
Browser → Cloudflare (DNS proxy, WAF, SSL edge) → Vercel (app edge / CDN)
```

| Layer | Provider | Role |
|---|---|---|
| Domain registration | Registrar (any) | Owns nameserver delegation |
| DNS + proxy | Cloudflare | Resolves records, optional WAF/cache |
| App hosting | Vercel | Serves Next.js / static app |
| SSL | Cloudflare (edge) + Vercel (origin) | TLS end-to-end |

---

## Phase 0 — Prerequisites

| Item | Status |
|---|---|
| Domain registered (any registrar) | ☐ |
| Cloudflare account with zone added for `vr4deaf.org` | ☐ |
| Cloudflare Zone ID copied from dashboard Overview tab | ☐ |
| `CLOUDFLARE_API_TOKEN` env var set (Zone:Edit permission) | ☐ |
| Vercel project created and linked to `pinkycollie/vr4deaf` repo | ☐ |
| Terraform ≥ 1.5 installed | ☐ |

---

## Phase 1 — Point nameservers to Cloudflare

At your domain registrar, replace the current nameservers with the two Cloudflare NS values shown in your Cloudflare zone dashboard (e.g. `aria.ns.cloudflare.com`, `bob.ns.cloudflare.com`).

Wait for Cloudflare to confirm "Active" zone status before proceeding.

---

## Phase 2 — Configure Terraform variables

```bash
cd infra/cloudflare/vr4deaf
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars – fill in cloudflare_zone_id and any mail/TXT records
```

Key decisions:

| Variable | Value during verification | Value after stable |
|---|---|---|
| `proxied` | `false` (DNS only) | `true` (orange cloud) |
| `ssl_mode` | `"full"` | `"full"` or `"strict"` |
| `ttl` | `60` | `300` |

---

## Phase 3 — Apply Terraform (DNS only, proxy off)

```bash
export CLOUDFLARE_API_TOKEN="<your-token>"

terraform init
terraform plan   # review – should create ~4+ records
terraform apply
```

Records created:

| Name | Type | Value | Proxied |
|---|---|---|---|
| `vr4deaf.org` | A | `76.76.21.21` | No |
| `www` | CNAME | `cname.vercel-dns.com` | No |
| `vr4deaf.org` | MX | *(your mail provider)* | No |
| `vr4deaf.org` | TXT | SPF / verification | No |
| *(subdomains)* | * | *(per config)* | No |

---

## Phase 4 — Add domain in Vercel

1. Vercel dashboard → Project → **Settings → Domains**.
2. Add `vr4deaf.org` and `www.vr4deaf.org`.
3. Vercel will check DNS and show **"Valid Configuration"** once it detects the records.

If Vercel shows a conflict or asks for a TXT verification record, add it to
`root_txt_records` in your `terraform.tfvars` and re-run `terraform apply`.

---

## Phase 5 — Verify SSL and routing

```bash
# Check DNS (proxy off – should return Vercel IP directly)
dig vr4deaf.org A
dig www.vr4deaf.org CNAME

# Check HTTPS
curl -I https://vr4deaf.org
curl -I https://www.vr4deaf.org
```

Confirm:
- [ ] HTTP → HTTPS redirect works
- [ ] `www` redirects to apex (or apex to www – set in Vercel domain settings)
- [ ] SSL cert is valid, no browser warning

---

## Phase 6 — Enable Cloudflare proxy

Once Vercel reports **"Valid Configuration"** and HTTPS is working:

```hcl
# terraform.tfvars
proxied = true
ttl     = 1   # auto – Cloudflare ignores this when proxied = true
```

```bash
terraform apply
```

Traffic now flows through Cloudflare's edge (DDoS protection, WAF, cache).

---

## Phase 7 — Subdomain remaps

Add any project subdomains to the `subdomain_records` list in `terraform.tfvars`:

```hcl
subdomain_records = [
  { name = "app",  type = "CNAME", value = "cname.vercel-dns.com", proxied = false },
  { name = "api",  type = "A",     value = "<api-server-ip>",       proxied = true  },
  { name = "mail", type = "CNAME", value = "ghs.googlemail.com",    proxied = false },
]
```

Then run `terraform apply`.

---

## Phase 8 — Optional hardening

- **WAF**: Enable Cloudflare Managed Rules in Security → WAF.
- **Rate limiting**: Add rate-limit rules for `/api/*` paths.
- **Cache rules**: Cache static assets at edge; bypass for `/api/*`.
- **Email security**: Add DMARC TXT record (`_dmarc.vr4deaf.org`) via `root_txt_records`.

---

## DNS record quick-reference (copy-paste)

| Name | Type | Value | Notes |
|---|---|---|---|
| `vr4deaf.org` | A | `76.76.21.21` | Vercel apex |
| `www` | CNAME | `cname.vercel-dns.com` | Vercel www |
| `vr4deaf.org` | MX | `1 aspmx.l.google.com` | Gmail (adjust priority) |
| `vr4deaf.org` | TXT | `v=spf1 include:_spf.google.com ~all` | SPF |

---

## Rollback

Revert `proxied = false` and re-run `terraform apply` to drop back to DNS-only mode.  
To fully disable Cloudflare, update nameservers at the registrar back to the previous values.

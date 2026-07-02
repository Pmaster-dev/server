output "apex_a_hostname" {
  description = "Apex A record hostname."
  value       = cloudflare_record.apex_a.hostname
}

output "www_cname_hostname" {
  description = "www CNAME record hostname."
  value       = cloudflare_record.www.hostname
}

output "zone_id" {
  description = "Cloudflare Zone ID in use."
  value       = var.cloudflare_zone_id
}

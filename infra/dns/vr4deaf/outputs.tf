output "hosted_zone_id" {
  description = "Route53 Hosted Zone ID."
  value       = aws_route53_zone.vr4deaf.zone_id
}

output "nameservers" {
  description = "The four NS records to paste into your domain registrar (replace the current Cloudflare nameservers)."
  value       = aws_route53_zone.vr4deaf.name_servers
}

output "zone_arn" {
  description = "ARN of the hosted zone."
  value       = aws_route53_zone.vr4deaf.arn
}

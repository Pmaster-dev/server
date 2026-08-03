terraform {
  required_version = ">= 1.5"
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "cloudflare" {
  # Set CLOUDFLARE_API_TOKEN env var – do not hardcode credentials here.
  # api_token = var.cloudflare_api_token
}

# ── .gitignore hint ─────────────────────────────────────────────────────────
# Add these lines to your root .gitignore (or infra/.gitignore):
#   terraform.tfvars
#   .terraform/
#   *.tfstate
#   *.tfstate.backup

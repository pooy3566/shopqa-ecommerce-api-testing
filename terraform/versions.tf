// Pin the Terraform core version and every provider version.
//
// Why pin: `terraform apply` on an unpinned provider can pick up a new major
// version months later and destroy-and-recreate resources you did not touch.
// The lock file (.terraform.lock.hcl) records exact versions and IS committed,
// so a rebuild months from now produces the same infrastructure.
terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  // azurerm 4.x requires the subscription to be named explicitly rather than
  // inherited silently from whatever `az account` happens to have selected.
  // That is deliberate on HashiCorp's part: provisioning into the wrong
  // subscription is a mistake you only notice when the bill arrives.
  subscription_id = var.subscription_id

  features {}
}

// Managed Postgres.
//
// The single most important decision in this whole stack. The app's data cannot
// live in the container: pods are replaced on every deploy, every crash and
// every node drain, and anything written inside one dies with it. Moving state
// out of the compute is what makes the compute disposable, and disposable
// compute is what makes rolling deploys and node failure survivable.

// Generated, never typed, never committed.
//
// The value exists only in Terraform state and in the Kubernetes secret built
// from it. Nobody ever sees it, which means nobody can accidentally paste it
// into a commit.
resource "random_password" "postgres" {
  length  = 32
  special = true
  // Azure rejects these three characters in a Postgres admin password.
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "${var.prefix}-pg-${local.suffix}" // must be globally unique
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  version    = var.postgres_version
  sku_name   = var.postgres_sku
  storage_mb = var.postgres_storage_mb

  administrator_login    = var.postgres_admin_user
  administrator_password = random_password.postgres.result

  // Seven days is the minimum. Backups are not optional even on a demo: the
  // point of a managed database is that this is handled for you, and turning it
  // off to save pennies gives away the only thing you are paying for.
  backup_retention_days = 7

  // Pinned to a single zone. The high-availability properties this project
  // documents apply to the stateless tier; the database is not zone-redundant,
  // and that distinction is stated rather than implied.
  zone = "1"

  // Public endpoint guarded by firewall rules, rather than a private endpoint
  // inside the cluster's VNet.
  //
  // Private networking is the production-correct answer. It is deliberately not
  // used here because it requires a delegated subnet, a private DNS zone and a
  // VNet peering, and none of that can be reached from a workstation to run
  // migrations. The tradeoff is real and you should name it when asked.
  public_network_access_enabled = true

  tags = local.tags

  lifecycle {
    // Changing the admin password out from under a running app is a silent
    // outage. If it ever needs rotating, that is a deliberate operation.
    ignore_changes = [administrator_password]
  }
}

// The application database inside the server.
resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"

  lifecycle {
    // Guard rail. Without this, a rename in variables.tf silently drops the
    // database and everything in it.
    prevent_destroy = false // set true if this ever holds data you care about
  }
}

// Allow other Azure services (which is how the AKS nodes appear) to connect.
//
// The 0.0.0.0 start/end pair is an Azure special case meaning "Azure internal
// traffic", NOT "the entire internet". It is confusing and worth knowing.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

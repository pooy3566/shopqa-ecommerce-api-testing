// Outputs are the seam between Terraform and everything downstream: the
// kubectl commands, the Kubernetes secret, and the CI workflow. Anything one
// of those needs to know is published here rather than copied by hand.

output "resource_group" {
  description = "Resource group holding every resource in this stack."
  value       = azurerm_resource_group.main.name
}

output "cluster_name" {
  description = "AKS cluster name. Used by: az aks get-credentials"
  value       = azurerm_kubernetes_cluster.main.name
}

output "acr_login_server" {
  description = "Registry hostname, e.g. ecomapiacrab12cd.azurecr.io. This is the prefix of the image tag in the Kubernetes deployment."
  value       = azurerm_container_registry.main.login_server
}

output "acr_name" {
  description = "Registry short name. Used by: az acr login --name <this>"
  value       = azurerm_container_registry.main.name
}

output "postgres_fqdn" {
  description = "Hostname of the Postgres server."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

// Marked sensitive, so Terraform redacts it in plan output and in CI logs.
//
// `sensitive` hides it from the terminal. It does NOT encrypt it: the value sits
// in plain text inside terraform.tfstate, which is exactly why that file is
// gitignored and why real teams keep state in a remote backend with access
// control rather than on a workstation.
output "database_url" {
  description = "Full SQLAlchemy connection string for the app's DATABASE_URL."
  value = format(
    "postgresql://%s:%s@%s:5432/%s?sslmode=require",
    var.postgres_admin_user,
    random_password.postgres.result,
    azurerm_postgresql_flexible_server.main.fqdn,
    var.database_name,
  )
  sensitive = true
}

output "kubectl_setup" {
  description = "Copy-paste command to point kubectl at the new cluster."
  value = format(
    "az aks get-credentials --resource-group %s --name %s --overwrite-existing",
    azurerm_resource_group.main.name,
    azurerm_kubernetes_cluster.main.name,
  )
}

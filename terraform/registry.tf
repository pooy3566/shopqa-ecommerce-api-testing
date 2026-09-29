// Azure Container Registry: the private store the cluster pulls images from.
//
// Why a registry at all, when Docker Hub exists: the cluster needs credentials
// to pull, and wiring those credentials by hand is the step that leaks. With
// ACR the cluster's own managed identity is granted pull rights (see the role
// assignment below) and no password exists anywhere to be leaked.
resource "azurerm_container_registry" "main" {
  name                = "${var.prefix}acr${local.suffix}" // globally unique, alphanumeric only
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  // Basic is the cheapest tier. It differs from Standard only in included
  // storage and throughput, neither of which matters for one small image.
  sku = "Basic"

  // Admin user disabled on purpose. Enabling it creates a static username and
  // password for the registry, which is exactly the long-lived shared secret
  // that managed identity exists to avoid. CI authenticates with OIDC instead.
  admin_enabled = false

  tags = local.tags
}

// Let the cluster pull from the registry.
//
// This is the piece people usually solve by pasting a registry password into a
// Kubernetes imagePullSecret. This is the better answer: the AKS kubelet has a
// managed identity, and that identity is granted the AcrPull role directly.
// No secret is created, so no secret can be stolen or has to be rotated.
resource "azurerm_role_assignment" "aks_pull_from_acr" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id

  // The role assignment API is eventually consistent and will occasionally
  // reject a principal that was created moments earlier. Terraform retries,
  // but if apply fails here once, re-running it is the fix, not a bug.
  skip_service_principal_aad_check = true
}

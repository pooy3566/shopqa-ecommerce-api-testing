// Every value that might reasonably differ between two runs of this stack lives
// here. Nothing environment-specific is hardcoded further down.

variable "subscription_id" {
  description = "Azure subscription to deploy into. Get it with: az account show --query id -o tsv"
  type        = string
}

variable "location" {
  // This subscription carries an Azure Policy named "Allowed resource deployment
  // regions" limiting deployment to: westus, northcentralus, centralus,
  // mexicocentral, canadacentral. southcentralus is NOT on that list and every
  // create returns 403 RequestDisallowedByAzure. centralus is the nearest allowed
  // region that also offers the Arm64 node size this subscription has quota for.
  description = "Azure region. Must be one of the regions permitted by the subscription policy: westus, northcentralus, centralus, mexicocentral, canadacentral."
  type        = string
  default     = "centralus"

  validation {
    condition     = contains(["westus", "northcentralus", "centralus", "mexicocentral", "canadacentral"], var.location)
    error_message = "Subscription policy 'Allowed resource deployment regions' rejects everything outside westus, northcentralus, centralus, mexicocentral, canadacentral."
  }
}

variable "prefix" {
  description = "Short name prefix for every resource. Lowercase alphanumeric only: the container registry name has to be globally unique across all of Azure and allows nothing else."
  type        = string
  default     = "ecomapi"

  validation {
    condition     = can(regex("^[a-z0-9]{3,12}$", var.prefix))
    error_message = "prefix must be 3-12 lowercase letters or digits, because the container registry name is built from it."
  }
}

// ----------------------------------------------------------------- cluster

variable "node_count" {
  description = "Number of worker nodes. Two, so a pod on each means the service survives losing a node, not just losing a pod. That distinction is what 'high availability' actually means."
  type        = number
  default     = 2
}

variable "node_size" {
  description = "VM size for the node pool. Arm64 is not a preference: this subscription has a hard quota of 0 vCPUs for every x64 family in this region, so Arm is the only thing that can be provisioned. The app image is built for linux/arm64 to match."
  type        = string
  default     = "Standard_B2ps_v2" // 2 vCPU, 8 GB, Arm64
}

variable "kubernetes_version" {
  description = "Leave null to take the region's default supported version. Pin it once the cluster is real, so an upgrade is a decision rather than an accident."
  type        = string
  default     = null
}

// ---------------------------------------------------------------- database

variable "postgres_sku" {
  description = "Burstable tier. This workload is a demo API, not a production write path, and burstable is the cheapest thing that is still a managed server with backups."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  description = "32 GB is the smallest Flexible Server allows. Storage can grow later but never shrink, so start at the floor."
  type        = number
  default     = 32768
}

variable "postgres_version" {
  description = "Postgres major version."
  type        = string
  default     = "16"
}

variable "database_name" {
  description = "Application database created inside the server. Matches POSTGRES_DB in .env.example."
  type        = string
  default     = "ecommerce_db"
}

variable "postgres_admin_user" {
  description = "Administrator login for the Postgres server. Not 'postgres': that name is reserved by Azure Flexible Server and the create call fails."
  type        = string
  default     = "ecomadmin"
}

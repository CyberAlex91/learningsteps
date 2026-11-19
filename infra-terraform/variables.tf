# Zweck: Definiert die Eingaben für AKS-Verwaltung und erlaubten Entwicklerzugang.
variable "aks_admin_object_id" {
  description = "Stable Entra object ID of the human cluster administrator, not the CI identity."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.aks_admin_object_id))
    error_message = "Provide an Entra user object UUID."
  }
}

variable "aks_api_allowed_cidr" {
  description = "Developer public IPv4 /32 allowed to reach the Kubernetes API. Recheck after IP changes."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.aks_api_allowed_cidr)) && endswith(var.aks_api_allowed_cidr, "/32")
    error_message = "Provide one IPv4 address as a /32 CIDR."
  }
}
# AI can be removed deliberately without deleting the Foundry account or notes.
variable "enable_ai_summary" {
  type        = bool
  default     = true
  description = "Deploy the pay-per-use summary model and API inference role."
}

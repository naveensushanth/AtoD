# Resource Group Handling Guide

## 🎯 Overview

The Terraform Generator has been updated to **exclude resource group creation**. Instead, it references an **existing resource group** using Terraform data sources. This approach is more flexible and aligns with common enterprise practices.

## 🔄 What Changed

### Before (Old Approach)
```hcl
# main.tf - CREATED resource group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  
  tags = var.tags
}

# Other resources reference it
resource "azurerm_app_service" "example" {
  name                = "my-app-service"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  # ...
}
```

### After (New Approach)
```hcl
# main.tf - REFERENCES existing resource group
data "azurerm_resource_group" "existing" {
  name = var.resource_group_name
}

# Other resources reference the data source
resource "azurerm_app_service" "example" {
  name                = "my-app-service"
  location            = data.azurerm_resource_group.existing.location
  resource_group_name = data.azurerm_resource_group.existing.name
  # ...
}
```

## ✅ Benefits

### 1. **Separation of Concerns**
- Resource groups are infrastructure foundations
- Often managed separately from application resources
- Allows different lifecycle management

### 2. **Enterprise Compliance**
- Many organizations have policies requiring pre-approved resource groups
- Naming conventions enforced at organization level
- Cost center tagging and access control pre-configured

### 3. **Security & Governance**
- Resource groups often have RBAC policies
- Prevent accidental deletion of resource groups
- Audit trails for resource group creation separate from resources

### 4. **Flexibility**
- Deploy to different resource groups without code changes
- Easy environment separation (dev, staging, prod)
- Support for multi-region deployments

### 5. **Existing Infrastructure**
- Works with brownfield deployments
- Can add resources to existing resource groups
- No conflicts with manually created infrastructure

## 📋 Prerequisites

### Before Running Terraform

You must create the resource group manually:

#### Option 1: Azure Portal
```
1. Go to Azure Portal
2. Click "Resource groups" → "Create"
3. Select subscription
4. Enter resource group name (e.g., "rg-platform-core")
5. Select region
6. Add tags if needed
7. Click "Review + create"
```

#### Option 2: Azure CLI
```bash
# Create resource group
az group create \
  --name rg-platform-core \
  --location eastus \
  --tags Environment=dev ManagedBy=Terraform

# Verify creation
az group show --name rg-platform-core
```

#### Option 3: PowerShell
```powershell
# Create resource group
New-AzResourceGroup `
  -Name "rg-platform-core" `
  -Location "East US" `
  -Tag @{Environment="dev"; ManagedBy="Terraform"}

# Verify creation
Get-AzResourceGroup -Name "rg-platform-core"
```

#### Option 4: Separate Terraform Project
```hcl
# resource-groups/main.tf
resource "azurerm_resource_group" "platform" {
  name     = "rg-platform-core"
  location = "East US"
  
  tags = {
    Environment = "production"
    ManagedBy   = "Terraform"
    CostCenter  = "Engineering"
  }
}

# Run separately before main infrastructure
terraform init
terraform apply
```

## 🔧 Configuration

### Variables.tf
```hcl
variable "resource_group_name" {
  description = "Name of the EXISTING resource group"
  type        = string
  default     = "rg-terraform-deployment"
}
```

### Usage in Main.tf
```hcl
# Data source to reference existing RG
data "azurerm_resource_group" "existing" {
  name = var.resource_group_name
}

# Example resource using the existing RG
resource "azurerm_storage_account" "example" {
  name                     = "mystorageacct"
  resource_group_name      = data.azurerm_resource_group.existing.name
  location                 = data.azurerm_resource_group.existing.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
```

## 🚀 Deployment Workflow

### Step 1: Create Resource Group (One Time)
```bash
# Create the resource group first
az group create \
  --name rg-terraform-deployment \
  --location eastus
```

### Step 2: Configure Terraform Variables
```hcl
# terraform.tfvars
resource_group_name = "rg-terraform-deployment"
location            = "eastus"
environment         = "dev"
```

### Step 3: Initialize and Plan
```bash
# Initialize Terraform
terraform init

# Validate the data source can find the RG
terraform plan
```

### Step 4: Apply
```bash
terraform apply
```

## 🔍 Verification

### Check if Resource Group Exists
```bash
# Azure CLI
az group exists --name rg-terraform-deployment

# Should return: true
```

### View Resource Group Details
```bash
# Azure CLI
az group show --name rg-terraform-deployment --output table

# PowerShell
Get-AzResourceGroup -Name "rg-terraform-deployment" | Format-List
```

### Terraform Plan Check
```bash
# If RG doesn't exist, you'll see this error:
terraform plan

# Error: Error: Resource Group "rg-terraform-deployment" was not found
```

## ⚠️ Common Issues

### Issue 1: Resource Group Not Found

**Error:**
```
Error: Error reading Resource Group "rg-terraform-deployment": 
resources.GroupsClient#Get: Failure responding to request: 
StatusCode=404 -- Original Error: autorest/azure: 
Service returned an error. Status=404 
Code="ResourceGroupNotFound" 
Message="Resource group 'rg-terraform-deployment' could not be found."
```

**Solution:**
```bash
# Create the resource group
az group create --name rg-terraform-deployment --location eastus

# Or verify the name is correct
az group list --output table
```

### Issue 2: Wrong Resource Group Name

**Symptom:** Terraform plan succeeds but applies to wrong RG

**Solution:**
```bash
# Check current value
terraform show

# Update terraform.tfvars
echo 'resource_group_name = "correct-rg-name"' >> terraform.tfvars

# Re-plan
terraform plan
```

### Issue 3: Permission Issues

**Error:**
```
Error: Authorization failed for data.azurerm_resource_group.existing
```

**Solution:**
```bash
# Check your permissions
az role assignment list --assignee $(az account show --query user.name -o tsv)

# You need at least "Reader" role on the resource group
az role assignment create \
  --role "Reader" \
  --assignee your-email@example.com \
  --resource-group rg-terraform-deployment
```

## 📊 Multi-Environment Setup

### Separate Resource Groups per Environment

```hcl
# environments/dev/terraform.tfvars
resource_group_name = "rg-myapp-dev"
environment         = "dev"

# environments/staging/terraform.tfvars
resource_group_name = "rg-myapp-staging"
environment         = "staging"

# environments/prod/terraform.tfvars
resource_group_name = "rg-myapp-prod"
environment         = "prod"
```

### Create All Resource Groups
```bash
# Create all environment RGs
for env in dev staging prod; do
  az group create \
    --name "rg-myapp-${env}" \
    --location eastus \
    --tags Environment=$env
done
```

### Deploy to Each Environment
```bash
# Dev
cd environments/dev
terraform init
terraform apply

# Staging
cd ../staging
terraform init
terraform apply

# Production
cd ../prod
terraform init
terraform apply
```

## 🔐 Best Practices

### 1. **Consistent Naming Convention**
```
Pattern: rg-<project>-<environment>-<region>
Examples:
  - rg-webapp-dev-eastus
  - rg-webapp-prod-westeurope
  - rg-platform-shared-centralindia
```

### 2. **Resource Group Tagging**
```hcl
tags = {
  Environment  = "production"
  ManagedBy    = "Terraform"
  CostCenter   = "Engineering"
  Project      = "WebApp"
  Owner        = "platform-team@company.com"
  Compliance   = "PCI-DSS"
}
```

### 3. **Use Remote State**
```hcl
# Store RG name in remote state
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "tfstatestore"
    container_name       = "tfstate"
    key                  = "platform.terraform.tfstate"
  }
}
```

### 4. **Document Prerequisites**
```markdown
## Prerequisites

Before deploying this infrastructure:

1. Create resource group:
   ```bash
   az group create --name rg-myapp-prod --location eastus
   ```

2. Configure access:
   ```bash
   az role assignment create \
     --role Contributor \
     --assignee <service-principal-id> \
     --resource-group rg-myapp-prod
   ```
```

## 🔄 Migration Guide

### If You Have Existing Terraform with RG Creation

#### Step 1: Import Existing RG to State
```bash
# Import the existing resource group
terraform import azurerm_resource_group.main /subscriptions/{subscription-id}/resourceGroups/{rg-name}
```

#### Step 2: Remove RG from Code
```bash
# Remove the resource block from main.tf
# Change from:
resource "azurerm_resource_group" "main" { ... }

# To:
data "azurerm_resource_group" "existing" {
  name = var.resource_group_name
}
```

#### Step 3: Update References
```bash
# Change all references from:
azurerm_resource_group.main.name

# To:
data.azurerm_resource_group.existing.name
```

#### Step 4: Remove from State
```bash
# Remove RG from Terraform state (it still exists in Azure)
terraform state rm azurerm_resource_group.main
```

#### Step 5: Verify
```bash
# Plan should show no changes
terraform plan
```

## 📚 Additional Resources

- [Terraform Data Sources](https://www.terraform.io/language/data-sources)
- [Azure Resource Group Management](https://docs.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)
- [Terraform Azure Provider Docs](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

## 🤔 FAQ

**Q: Why not create the resource group in Terraform?**  
A: Resource groups are foundational infrastructure, often managed separately with stricter governance and lifecycle policies.

**Q: Can I still create RGs if needed?**  
A: Yes! You can modify the generated code or create a separate Terraform project for RGs.

**Q: What if I want both options?**  
A: You could add a variable `create_resource_group = false` to toggle between creation and data source.

**Q: Does this work with GitHub Actions?**  
A: Yes! Just ensure the RG exists before the workflow runs. You can add a step to create it if needed.

**Q: How do I handle multiple resource groups?**  
A: Create multiple data sources:
```hcl
data "azurerm_resource_group" "compute" {
  name = var.compute_rg_name
}

data "azurerm_resource_group" "storage" {
  name = var.storage_rg_name
}
```

---

**Last Updated:** January 7, 2025  
**Version:** 2.0 (Excluding RG Creation)
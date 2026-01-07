"""
Terraform Generator Module
Generates Terraform code from analyzed Azure architecture
Modified for Azure OpenAI - Excludes Resource Group creation
"""

from openai import AzureOpenAI
from typing import Dict, Any
import re


class TerraformGenerator:
    """Generate Terraform code for Azure resources"""
    
    def __init__(self, api_key: str, azure_endpoint: str, deployment_name: str, api_version: str = "2024-02-15-preview"):
        """
        Initialize the TerraformGenerator with Azure OpenAI credentials.
        
        Args:
            api_key (str): Azure OpenAI API key
            azure_endpoint (str): Azure OpenAI endpoint URL
            deployment_name (str): Name of the deployed model
            api_version (str): API version to use
        """
        self.api_key = api_key
        self.azure_endpoint = azure_endpoint
        self.deployment_name = deployment_name
        self.api_version = api_version
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint
        )
    
    def generate_terraform(self, analysis_result: Dict[str, Any], region: str = "East US") -> Dict[str, str]:
        """
        Generate Terraform code from analysis results
        
        Args:
            analysis_result: The diagram analysis result
            region: Azure region for deployment
            
        Returns:
            dict: Contains main.tf, variables.tf, and outputs.tf code
        """
        try:
            resources = analysis_result.get('resources', [])
            
            if not resources:
                return self._create_empty_terraform()
            
            # Generate main.tf
            main_tf = self._generate_main_tf(resources, region)
            
            # Generate variables.tf
            variables_tf = self._generate_variables_tf(resources, region)
            
            # Generate outputs.tf
            outputs_tf = self._generate_outputs_tf(resources)
            
            return {
                'main_tf': main_tf,
                'variables_tf': variables_tf,
                'outputs_tf': outputs_tf
            }
        
        except Exception as e:
            return self._create_error_terraform(str(e))
    
    def _generate_main_tf(self, resources: list, region: str) -> str:
        """Generate main.tf file"""
        
        prompt = f"""
Generate a complete Terraform main.tf file for the following Azure resources.

**Region:** {region}

**Resources to create:**
{self._format_resources_for_prompt(resources)}

**Requirements:**
1. Include proper provider configuration for Azure (azurerm)
2. **IMPORTANT: Do NOT create a resource group - assume it already exists**
3. Reference the existing resource group using: data.azurerm_resource_group.existing.name and data.azurerm_resource_group.existing.location
4. Generate realistic Terraform resource blocks for each Azure service
5. Use proper resource naming conventions (lowercase, hyphens)
6. Include necessary dependencies between resources
7. Add appropriate tags for all resources
8. Use variables where appropriate (reference from variables.tf)
9. Include comments explaining each resource block

**CRITICAL:** 
- DO NOT include any resource group creation (no "resource "azurerm_resource_group"")
- Use data source to reference existing resource group
- Return ONLY the Terraform code, no markdown formatting, no explanations
- Use valid Terraform HCL syntax
- Make the code deployment-ready
- Include realistic default configurations

Generate the complete main.tf file now:
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert DevOps engineer specializing in Terraform and Azure infrastructure as code. Generate clean, production-ready Terraform code. NEVER create resource groups - always use existing ones via data sources."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            terraform_code = self._clean_code_response(response.choices[0].message.content)
            
            # Remove any resource group creation that might have been generated
            terraform_code = self._remove_resource_group_creation(terraform_code)
            
            # Ensure it has provider block and data source
            if 'provider "azurerm"' not in terraform_code:
                terraform_code = self._add_provider_block(region) + "\n\n" + terraform_code
            
            # Ensure it has data source for existing resource group
            if 'data "azurerm_resource_group"' not in terraform_code:
                terraform_code = self._add_data_source() + "\n\n" + terraform_code
            
            return terraform_code
        
        except Exception as e:
            return f"# Error generating main.tf: {str(e)}\n\n{self._get_basic_main_tf(region)}"
    
    def _generate_variables_tf(self, resources: list, region: str) -> str:
        """Generate variables.tf file"""
        
        prompt = f"""
Generate a Terraform variables.tf file for the Azure infrastructure with these resources:

{self._format_resources_for_prompt(resources)}

**Region:** {region}

Create variables for:
1. Azure region/location
2. **Existing resource group name (not creating new one)**
3. Environment (dev, staging, prod)
4. Common tags
5. Resource-specific configurations (SKUs, sizes, etc.)

**Requirements:**
- Use descriptive variable names
- Include descriptions for each variable
- Provide sensible default values
- Use appropriate variable types
- **IMPORTANT: Variable for resource group should indicate it's existing, not new**

Return ONLY the Terraform variables.tf code with no markdown formatting:
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert DevOps engineer specializing in Terraform. Generate clean variables.tf files. Remember that resource groups are pre-existing, not created by this code."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return self._clean_code_response(response.choices[0].message.content)
        
        except Exception as e:
            return self._get_basic_variables_tf(region)
    
    def _generate_outputs_tf(self, resources: list) -> str:
        """Generate outputs.tf file"""
        
        prompt = f"""
Generate a Terraform outputs.tf file for these Azure resources:

{self._format_resources_for_prompt(resources)}

Create outputs for:
1. Resource group name and ID (from existing resource group)
2. Important resource IDs
3. Connection strings (where applicable)
4. Endpoints and URLs
5. Any other useful information for users

**Note:** Resource group is existing (referenced via data source), not created.

Use descriptive output names and include descriptions.

Return ONLY the Terraform outputs.tf code with no markdown formatting:
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert DevOps engineer specializing in Terraform. Generate clean outputs.tf files."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return self._clean_code_response(response.choices[0].message.content)
        
        except Exception as e:
            return self._get_basic_outputs_tf()
    
    def _format_resources_for_prompt(self, resources: list) -> str:
        """Format resources list for AI prompt"""
        formatted = []
        for idx, resource in enumerate(resources, 1):
            formatted.append(f"""
{idx}. **{resource.get('resource_name', 'Unnamed')}**
   - Type: {resource.get('resource_type', 'Unknown')}
   - Category: {resource.get('category', 'Other')}
   - Description: {resource.get('description', 'N/A')}
   - Connections: {', '.join(resource.get('connections', []))}
""")
        return '\n'.join(formatted)
    
    def _clean_code_response(self, response_text: str) -> str:
        """Clean AI response to extract pure code"""
        # Remove markdown code blocks
        cleaned = re.sub(r'```(?:hcl|terraform)?\s*|\s*```', '', response_text)
        cleaned = cleaned.strip()
        return cleaned
    
    def _remove_resource_group_creation(self, terraform_code: str) -> str:
        """Remove any resource group creation from generated code"""
        # Pattern to match resource group resource block
        # This handles multi-line resource blocks
        pattern = r'resource\s+"azurerm_resource_group"\s+"[^"]+"\s*\{[^}]*\}'
        
        # Remove the resource group creation
        cleaned_code = re.sub(pattern, '', terraform_code, flags=re.DOTALL)
        
        # Also remove any comments about resource group creation
        cleaned_code = re.sub(r'#\s*Resource\s+Group.*\n', '', cleaned_code, flags=re.IGNORECASE)
        
        # Clean up multiple empty lines
        cleaned_code = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_code)
        
        return cleaned_code.strip()
    
    def _add_provider_block(self, region: str) -> str:
        """Add basic provider configuration (without resource group)"""
        region_map = {
            "East US": "eastus",
            "West US": "westus",
            "Central US": "centralus",
            "Central India": "centralindia",
            "North Europe": "northeurope",
            "West Europe": "westeurope",
            "Southeast Asia": "southeastasia",
            "East Asia": "eastasia",
            "UK South": "uksouth",
            "Australia East": "australiaeast"
        }
        
        location = region_map.get(region, "eastus")
        
        return f"""terraform {{
  required_version = ">= 1.0"
  
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}
}}"""
    
    def _add_data_source(self) -> str:
        """Add data source for existing resource group"""
        return """# Reference to existing resource group
# The resource group must already exist in Azure
data "azurerm_resource_group" "existing" {
  name = var.resource_group_name
}"""
    
    def _get_basic_main_tf(self, region: str) -> str:
        """Get basic main.tf template (without resource group creation)"""
        provider_block = self._add_provider_block(region)
        data_source = self._add_data_source()
        
        return f"""{provider_block}

{data_source}

# Resources will be created in the existing resource group
# Reference: data.azurerm_resource_group.existing.name
#           data.azurerm_resource_group.existing.location"""
    
    def _get_basic_variables_tf(self, region: str) -> str:
        """Get basic variables.tf template"""
        region_map = {
            "East US": "eastus",
            "West US": "westus",
            "Central US": "centralus",
            "Central India": "centralindia",
            "North Europe": "northeurope",
            "West Europe": "westeurope",
            "Southeast Asia": "southeastasia",
            "East Asia": "eastasia",
            "UK South": "uksouth",
            "Australia East": "australiaeast"
        }
        
        location = region_map.get(region, "eastus")
        
        return f"""variable "location" {{
  description = "Azure region for resources"
  type        = string
  default     = "{location}"
}}

variable "resource_group_name" {{
  description = "Name of the existing resource group"
  type        = string
  default     = "rg-terraform-deployment"
}}

variable "environment" {{
  description = "Environment name"
  type        = string
  default     = "dev"
}}

variable "tags" {{
  description = "Common tags for all resources"
  type        = map(string)
  default = {{
    Environment = "dev"
    ManagedBy   = "Terraform"
    CreatedBy   = "Azure Architecture Analyzer"
  }}
}}"""
    
    def _get_basic_outputs_tf(self) -> str:
        """Get basic outputs.tf template (referencing existing resource group)"""
        return """output "resource_group_name" {
  description = "Name of the existing resource group"
  value       = data.azurerm_resource_group.existing.name
}

output "resource_group_id" {
  description = "ID of the existing resource group"
  value       = data.azurerm_resource_group.existing.id
}

output "location" {
  description = "Azure region"
  value       = data.azurerm_resource_group.existing.location
}"""
    
    def _create_empty_terraform(self) -> Dict[str, str]:
        """Create empty Terraform structure"""
        return {
            'main_tf': '# No resources identified\n',
            'variables_tf': '# No variables needed\n',
            'outputs_tf': '# No outputs available\n'
        }
    
    def _create_error_terraform(self, error_msg: str) -> Dict[str, str]:
        """Create error Terraform structure"""
        error_comment = f"# Error generating Terraform: {error_msg}\n"
        return {
            'main_tf': error_comment,
            'variables_tf': error_comment,
            'outputs_tf': error_comment
        }
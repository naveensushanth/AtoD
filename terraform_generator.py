"""
Terraform Generator Module
Generates Terraform code from analyzed Azure architecture
"""

import google.generativeai as genai
from typing import Dict, Any
import re


class TerraformGenerator:
    """Generate Terraform code for Azure resources"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        # FIX: Remove -latest suffix
        if model_name.endswith("-latest"):
            model_name = model_name.replace("-latest", "")
        self.model_name = model_name
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
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
2. Create a resource group named "rg-terraform-deployment"
3. Generate realistic Terraform resource blocks for each Azure service
4. Use proper resource naming conventions (lowercase, hyphens)
5. Include necessary dependencies between resources
6. Add appropriate tags for all resources
7. Use variables where appropriate (reference from variables.tf)
8. Include comments explaining each resource block

**IMPORTANT:** 
- Return ONLY the Terraform code, no markdown formatting, no explanations
- Use valid Terraform HCL syntax
- Make the code deployment-ready
- Include realistic default configurations

Generate the complete main.tf file now:
"""
        
        try:
            response = self.model.generate_content(prompt)
            terraform_code = self._clean_code_response(response.text)
            
            # Ensure it has provider block
            if 'provider "azurerm"' not in terraform_code:
                terraform_code = self._add_provider_block(region) + "\n\n" + terraform_code
            
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
2. Resource group name
3. Environment (dev, staging, prod)
4. Common tags
5. Resource-specific configurations (SKUs, sizes, etc.)

**Requirements:**
- Use descriptive variable names
- Include descriptions for each variable
- Provide sensible default values
- Use appropriate variable types

Return ONLY the Terraform variables.tf code with no markdown formatting:
"""
        
        try:
            response = self.model.generate_content(prompt)
            return self._clean_code_response(response.text)
        
        except Exception as e:
            return self._get_basic_variables_tf(region)
    
    def _generate_outputs_tf(self, resources: list) -> str:
        """Generate outputs.tf file"""
        
        prompt = f"""
Generate a Terraform outputs.tf file for these Azure resources:

{self._format_resources_for_prompt(resources)}

Create outputs for:
1. Resource group name and ID
2. Important resource IDs
3. Connection strings (where applicable)
4. Endpoints and URLs
5. Any other useful information for users

Use descriptive output names and include descriptions.

Return ONLY the Terraform outputs.tf code with no markdown formatting:
"""
        
        try:
            response = self.model.generate_content(prompt)
            return self._clean_code_response(response.text)
        
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
    
    def _add_provider_block(self, region: str) -> str:
        """Add basic provider configuration"""
        region_map = {
            "East US": "eastus",
            "West US": "westus",
            "Central US": "centralus",
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
}}

# Resource Group
resource "azurerm_resource_group" "main" {{
  name     = var.resource_group_name
  location = var.location
  
  tags = var.tags
}}"""
    
    def _get_basic_main_tf(self, region: str) -> str:
        """Get basic main.tf template"""
        return self._add_provider_block(region)
    
    def _get_basic_variables_tf(self, region: str) -> str:
        """Get basic variables.tf template"""
        region_map = {
            "East US": "eastus",
            "West US": "westus",
            "Central US": "centralus",
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
  description = "Name of the resource group"
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
        """Get basic outputs.tf template"""
        return """output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.main.id
}

output "location" {
  description = "Azure region"
  value       = azurerm_resource_group.main.location
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
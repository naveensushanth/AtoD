"""
Azure Cost Estimator Module
Estimates monthly costs for Azure resources
"""

import google.generativeai as genai
from typing import Dict, Any, List
import json
import re


class AzureCostEstimator:
    """Estimate costs for Azure resources"""
    
    # Baseline cost estimates (USD per month) - These are approximate
    BASELINE_COSTS = {
        # Compute
        'Virtual Machine': 50.0,
        'App Service': 75.0,
        'Azure Functions': 20.0,
        'Container Instances': 30.0,
        'Kubernetes Service': 150.0,
        'Azure Batch': 40.0,
        
        # Storage
        'Blob Storage': 25.0,
        'File Storage': 30.0,
        'Queue Storage': 10.0,
        'Table Storage': 15.0,
        'Data Lake': 100.0,
        
        # Database
        'SQL Database': 100.0,
        'Cosmos DB': 120.0,
        'MySQL': 80.0,
        'PostgreSQL': 80.0,
        'Redis Cache': 50.0,
        
        # Networking
        'Virtual Network': 5.0,
        'Load Balancer': 25.0,
        'Application Gateway': 150.0,
        'VPN Gateway': 140.0,
        'Traffic Manager': 20.0,
        'Front Door': 35.0,
        'CDN': 40.0,
        
        # Security
        'Key Vault': 5.0,
        'Security Center': 15.0,
        'Active Directory': 6.0,
        'Azure Firewall': 175.0,
        
        # Analytics
        'Synapse Analytics': 300.0,
        'Data Factory': 60.0,
        'Stream Analytics': 90.0,
        'HDInsight': 200.0,
        'Databricks': 250.0,
        
        # AI/ML
        'Cognitive Services': 40.0,
        'Machine Learning': 100.0,
        'Bot Service': 30.0,
        
        # Integration
        'Logic Apps': 35.0,
        'Service Bus': 25.0,
        'Event Grid': 15.0,
        'Event Hubs': 50.0,
        'API Management': 100.0,
        
        # Monitoring
        'Monitor': 20.0,
        'Application Insights': 30.0,
        'Log Analytics': 40.0
    }
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        # FIX: Remove -latest suffix
        if model_name.endswith("-latest"):
            model_name = model_name.replace("-latest", "")
        self.model_name = model_name
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
    def estimate_costs(self, analysis_result: Dict[str, Any], region: str = "East US") -> Dict[str, Any]:
        """
        Estimate monthly costs for all resources
        
        Args:
            analysis_result: The diagram analysis result
            region: Azure region (affects pricing)
            
        Returns:
            dict: Cost estimates including per-resource and total costs
        """
        try:
            resources = analysis_result.get('resources', [])
            
            if not resources:
                return self._create_empty_estimate()
            
            # Get AI-enhanced cost estimates
            enhanced_estimates = self._get_ai_cost_estimates(resources, region)
            
            # Calculate total
            total_cost = sum(r['estimated_monthly_cost'] for r in enhanced_estimates)
            
            return {
                'total_monthly_cost': round(total_cost, 2),
                'region': region,
                'resources': enhanced_estimates,
                'currency': 'USD',
                'estimate_date': self._get_timestamp(),
                'disclaimer': 'Estimates are approximate and may vary based on actual usage, configuration, and Azure pricing changes.'
            }
        
        except Exception as e:
            return self._create_error_estimate(str(e))
    
    def _get_ai_cost_estimates(self, resources: List[Dict], region: str) -> List[Dict]:
        """Use AI to get more accurate cost estimates"""
        
        prompt = f"""
Analyze these Azure resources and provide realistic monthly cost estimates in USD for the {region} region.

**Resources:**
{self._format_resources_for_prompt(resources)}

For each resource, estimate the monthly cost based on:
1. Typical production usage patterns
2. Standard pricing tiers (not premium unless specified)
3. Moderate traffic/usage assumptions
4. {region} region pricing

Return ONLY a JSON array with this exact structure (no markdown, no code blocks):
[
  {{
    "resource_name": "exact name from input",
    "resource_type": "exact type from input",
    "estimated_monthly_cost": 123.45,
    "pricing_tier": "Standard/Basic/Premium",
    "assumptions": "Brief explanation of cost assumptions"
  }}
]

Be realistic - don't underestimate or overestimate. Use actual Azure pricing as reference.
"""
        
        try:
            response = self.model.generate_content(prompt)
            estimates = self._parse_cost_response(response.text)
            
            # Validate and fallback to baseline if needed
            return self._validate_and_enhance_estimates(estimates, resources)
        
        except Exception as e:
            print(f"AI estimation failed: {e}, using baseline costs")
            return self._get_baseline_estimates(resources)
    
    def _parse_cost_response(self, response_text: str) -> List[Dict]:
        """Parse AI cost response"""
        # Clean response
        cleaned = re.sub(r'```json\s*|\s*```', '', response_text)
        cleaned = cleaned.strip()
        
        # Parse JSON
        estimates = json.loads(cleaned)
        
        if not isinstance(estimates, list):
            raise ValueError("Response is not a list")
        
        return estimates
    
    def _validate_and_enhance_estimates(self, ai_estimates: List[Dict], original_resources: List[Dict]) -> List[Dict]:
        """Validate AI estimates and add missing resources"""
        
        result = []
        resource_map = {r['resource_name']: r for r in original_resources}
        estimated_names = set()
        
        # Process AI estimates
        for estimate in ai_estimates:
            if estimate['resource_name'] in resource_map:
                estimated_names.add(estimate['resource_name'])
                
                # Ensure cost is reasonable
                cost = estimate.get('estimated_monthly_cost', 0)
                if cost < 0 or cost > 10000:
                    # Use baseline if unreasonable
                    resource = resource_map[estimate['resource_name']]
                    cost = self._get_baseline_cost(resource.get('resource_type', ''))
                
                result.append({
                    'resource_name': estimate['resource_name'],
                    'resource_type': estimate['resource_type'],
                    'estimated_monthly_cost': round(cost, 2),
                    'pricing_tier': estimate.get('pricing_tier', 'Standard'),
                    'assumptions': estimate.get('assumptions', 'Standard configuration')
                })
        
        # Add missing resources with baseline costs
        for resource in original_resources:
            if resource['resource_name'] not in estimated_names:
                result.append({
                    'resource_name': resource['resource_name'],
                    'resource_type': resource.get('resource_type', 'Unknown'),
                    'estimated_monthly_cost': self._get_baseline_cost(resource.get('resource_type', '')),
                    'pricing_tier': 'Standard',
                    'assumptions': 'Baseline estimate'
                })
        
        return result
    
    def _get_baseline_estimates(self, resources: List[Dict]) -> List[Dict]:
        """Get baseline cost estimates without AI"""
        
        estimates = []
        
        for resource in resources:
            resource_type = resource.get('resource_type', 'Unknown')
            cost = self._get_baseline_cost(resource_type)
            
            estimates.append({
                'resource_name': resource.get('resource_name', 'Unnamed'),
                'resource_type': resource_type,
                'estimated_monthly_cost': cost,
                'pricing_tier': 'Standard',
                'assumptions': 'Baseline estimate for standard tier'
            })
        
        return estimates
    
    def _get_baseline_cost(self, resource_type: str) -> float:
        """Get baseline cost for a resource type"""
        
        # Try exact match
        if resource_type in self.BASELINE_COSTS:
            return self.BASELINE_COSTS[resource_type]
        
        # Try partial match
        for key, cost in self.BASELINE_COSTS.items():
            if key.lower() in resource_type.lower() or resource_type.lower() in key.lower():
                return cost
        
        # Default cost for unknown resources
        return 50.0
    
    def _format_resources_for_prompt(self, resources: List[Dict]) -> str:
        """Format resources for AI prompt"""
        formatted = []
        for idx, resource in enumerate(resources, 1):
            formatted.append(f"{idx}. {resource.get('resource_name', 'Unnamed')} - {resource.get('resource_type', 'Unknown')}")
        return '\n'.join(formatted)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _create_empty_estimate(self) -> Dict[str, Any]:
        """Create empty cost estimate"""
        return {
            'total_monthly_cost': 0.0,
            'region': 'N/A',
            'resources': [],
            'currency': 'USD',
            'estimate_date': self._get_timestamp(),
            'disclaimer': 'No resources to estimate'
        }
    
    def _create_error_estimate(self, error_msg: str) -> Dict[str, Any]:
        """Create error cost estimate"""
        return {
            'total_monthly_cost': 0.0,
            'region': 'N/A',
            'resources': [],
            'currency': 'USD',
            'estimate_date': self._get_timestamp(),
            'error': error_msg,
            'disclaimer': f'Cost estimation failed: {error_msg}'
        }
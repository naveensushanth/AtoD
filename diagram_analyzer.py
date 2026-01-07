"""
Azure Architecture Diagram Analyzer - Core Analysis Module
Modified for Azure OpenAI with Vision capabilities
"""

from openai import AzureOpenAI
from PIL import Image
import json
import io
import base64
from typing import Dict, List, Any
import re


class DiagramAnalyzer:
    """
    Analyzer class for extracting Azure resources from architecture diagrams
    using Azure OpenAI GPT-4 Vision.
    """
    
    def __init__(self, api_key: str, azure_endpoint: str, deployment_name: str, api_version: str = "2024-02-15-preview"):
        """
        Initialize the DiagramAnalyzer with Azure OpenAI credentials.
        
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
    
    def analyze_diagram(self, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze an Azure architecture diagram and extract resources.
        
        Args:
            image (PIL.Image.Image): The architecture diagram image to analyze
            
        Returns:
            dict: Analysis results containing resources, patterns, and metadata
        """
        try:
            # Convert image to base64
            base64_image = self._image_to_base64(image)
            
            # Create detailed prompt
            prompt = self._create_analysis_prompt()
            
            # Call Azure OpenAI with vision
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Azure cloud architect analyzing architecture diagrams. You provide detailed, accurate analysis in JSON format."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            # Extract and parse the response
            result = self._parse_response(response.choices[0].message.content)
            
            # Add metadata
            result['metadata'] = {
                'success': True,
                'model': self.deployment_name,
                'timestamp': self._get_timestamp()
            }
            
            return result
            
        except json.JSONDecodeError as e:
            return self._create_error_response(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            return self._create_error_response(f"Analysis error: {str(e)}")
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string.
        
        Args:
            image (PIL.Image.Image): The image to convert
            
        Returns:
            str: Base64 encoded image
        """
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def _create_analysis_prompt(self) -> str:
        """
        Create a comprehensive prompt for analyzing Azure architecture diagrams.
        
        Returns:
            str: The prompt text
        """
        prompt = """
Analyze this Azure architecture diagram in detail and extract all information about Azure resources and their relationships.

Please identify:
1. **All Azure Resources**: Look for service icons, labels, and text
2. **Resource Types**: Specific Azure service names (e.g., App Service, Storage Account, SQL Database)
3. **Resource Names**: Any custom names or labels given to resources
4. **Categories**: Classify each resource (Compute, Storage, Database, Networking, Security, Analytics, AI/ML, DevOps, Integration, Identity, Monitoring, Other)
5. **Connections**: Identify which resources connect to which (arrows, lines, or implied relationships)
6. **Architecture Pattern**: Identify the overall pattern (e.g., Three-tier, Microservices, Hub-and-Spoke, Serverless, Event-driven, etc.)
7. **Summary**: Brief description of what this architecture does

**IMPORTANT**: Return ONLY valid JSON with no markdown formatting, no code blocks, no backticks. Just pure JSON.

Use this exact JSON structure:
{
  "architecture_pattern": "Name of the architecture pattern",
  "summary": "Brief summary of the architecture and its purpose",
  "confidence": "high or medium or low",
  "resources": [
    {
      "resource_name": "Name or identifier of the resource",
      "resource_type": "Specific Azure service type (e.g., Azure App Service, Azure SQL Database)",
      "category": "One of: Compute, Storage, Database, Networking, Security, Analytics, AI/ML, DevOps, Integration, Identity, Monitoring, Other",
      "description": "Brief description of what this resource does in the architecture",
      "connections": ["List of resource names this connects to"]
    }
  ]
}

Common Azure Categories:
- **Compute**: Virtual Machines, App Service, Functions, Container Instances, Kubernetes Service, Batch
- **Storage**: Blob Storage, File Storage, Queue Storage, Table Storage, Data Lake
- **Database**: SQL Database, Cosmos DB, MySQL, PostgreSQL, Redis Cache
- **Networking**: Virtual Network, Load Balancer, Application Gateway, VPN Gateway, Traffic Manager, Front Door, CDN
- **Security**: Key Vault, Security Center, Active Directory, Azure Firewall
- **Analytics**: Synapse Analytics, Data Factory, Stream Analytics, HDInsight, Databricks
- **AI/ML**: Cognitive Services, Machine Learning, Bot Service
- **DevOps**: DevOps, Pipelines, Repos, Artifacts
- **Integration**: Logic Apps, Service Bus, Event Grid, Event Hubs, API Management
- **Identity**: Active Directory, AD B2C, AD Domain Services
- **Monitoring**: Monitor, Application Insights, Log Analytics
- **Other**: Any services not fitting above categories

Be thorough and identify every visible Azure resource in the diagram.
"""
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the AI model's response and extract JSON.
        
        Args:
            response_text (str): Raw response text from the AI model
            
        Returns:
            dict: Parsed JSON response
        """
        # Remove markdown code blocks if present
        cleaned_text = re.sub(r'```json\s*|\s*```', '', response_text)
        cleaned_text = cleaned_text.strip()
        
        # Parse JSON
        result = json.loads(cleaned_text)
        
        # Validate structure
        if 'resources' not in result:
            result['resources'] = []
        if 'architecture_pattern' not in result:
            result['architecture_pattern'] = 'Not identified'
        if 'summary' not in result:
            result['summary'] = 'No summary available'
        if 'confidence' not in result:
            result['confidence'] = 'medium'
        
        return result
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            error_message (str): The error message
            
        Returns:
            dict: Error response structure
        """
        return {
            'metadata': {
                'success': False,
                'error': error_message,
                'timestamp': self._get_timestamp()
            },
            'resources': [],
            'architecture_pattern': 'Error',
            'summary': error_message,
            'confidence': 'N/A'
        }
    
    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO format.
        
        Returns:
            str: ISO formatted timestamp
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_resources_by_category(self, result: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """
        Group resources by their category.
        
        Args:
            result (dict): The analysis result containing resources
            
        Returns:
            dict: Dictionary with categories as keys and lists of resources as values
        """
        categories = {}
        
        for resource in result.get('resources', []):
            category = resource.get('category', 'Other')
            
            if category not in categories:
                categories[category] = []
            
            categories[category].append(resource)
        
        # Sort categories alphabetically
        return dict(sorted(categories.items()))
    
    def get_resource_statistics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate statistics about the analyzed resources.
        
        Args:
            result (dict): The analysis result
            
        Returns:
            dict: Statistics including counts, categories, connections
        """
        resources = result.get('resources', [])
        
        stats = {
            'total_resources': len(resources),
            'total_categories': len(set(r.get('category', 'Other') for r in resources)),
            'total_connections': sum(len(r.get('connections', [])) for r in resources),
            'resources_by_category': {},
            'most_connected_resource': None,
            'confidence': result.get('confidence', 'N/A')
        }
        
        # Count resources by category
        for resource in resources:
            category = resource.get('category', 'Other')
            stats['resources_by_category'][category] = stats['resources_by_category'].get(category, 0) + 1
        
        # Find most connected resource
        if resources:
            most_connected = max(resources, key=lambda r: len(r.get('connections', [])))
            stats['most_connected_resource'] = {
                'name': most_connected.get('resource_name', 'Unknown'),
                'connections': len(most_connected.get('connections', []))
            }
        
        return stats
    
    def export_to_dict(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export the analysis result as a clean dictionary.
        
        Args:
            result (dict): The analysis result
            
        Returns:
            dict: Cleaned and formatted result
        """
        return {
            'architecture_pattern': result.get('architecture_pattern', 'Not identified'),
            'summary': result.get('summary', 'No summary available'),
            'confidence': result.get('confidence', 'N/A'),
            'resources': result.get('resources', []),
            'statistics': self.get_resource_statistics(result),
            'metadata': result.get('metadata', {})
        }
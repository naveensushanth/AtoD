"""
Azure Architecture Diagram Analyzer - Core Analysis Module
This module provides the DiagramAnalyzer class for analyzing Azure architecture diagrams
using Google's Gemini AI model.
"""

import google.generativeai as genai
from PIL import Image
import json
import io
from typing import Dict, List, Any
import re


class DiagramAnalyzer:
    """
    Analyzer class for extracting Azure resources from architecture diagrams
    using Google's Gemini AI model.
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize the DiagramAnalyzer with API credentials.
        
        Args:
            api_key (str): Google Gemini API key
            model_name (str): Name of the Gemini model to use
        """
        self.api_key = api_key
        
        # Map user-friendly names to actual model identifiers
        model_mapping = {
            "gemini-1.5-flash": "gemini-1.5-flash-latest",
            "gemini-1.5-pro": "gemini-1.5-pro-latest",
            "gemini-1.5-flash-latest": "gemini-1.5-flash-latest",
            "gemini-1.5-pro-latest": "gemini-1.5-pro-latest"
        }
        
        self.model_name = model_mapping.get(model_name, "gemini-1.5-flash-latest")
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)
    
    def analyze_diagram(self, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze an Azure architecture diagram and extract resources.
        
        Args:
            image (PIL.Image.Image): The architecture diagram image to analyze
            
        Returns:
            dict: Analysis results containing resources, patterns, and metadata
        """
        try:
            # Create detailed prompt for Gemini
            prompt = self._create_analysis_prompt()
            
            # Generate content using Gemini
            response = self.model.generate_content([prompt, image])
            
            # Extract and parse the JSON response
            result = self._parse_response(response.text)
            
            # Add metadata
            result['metadata'] = {
                'success': True,
                'model': self.model_name,
                'timestamp': self._get_timestamp()
            }
            
            return result
            
        except json.JSONDecodeError as e:
            return self._create_error_response(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            return self._create_error_response(f"Analysis error: {str(e)}")
    
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
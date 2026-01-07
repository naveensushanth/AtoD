"""
GitHub Agent Module
Pushes generated Terraform code to GitHub repository
Uses AI to generate commit messages and handle repository operations
"""

import os
import base64
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from openai import AzureOpenAI


class GitHubAgent:
    """AI-powered GitHub integration agent"""
    
    def __init__(self, api_key: str, azure_endpoint: str, deployment_name: str, 
                 api_version: str = "2024-02-15-preview"):
        """
        Initialize GitHub Agent with Azure OpenAI credentials.
        
        Args:
            api_key: Azure OpenAI API key
            azure_endpoint: Azure OpenAI endpoint URL
            deployment_name: Name of the deployed model
            api_version: API version to use
        """
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint
        )
        self.deployment_name = deployment_name
        
    def generate_commit_message(self, terraform_code: Dict[str, str], 
                               cost_estimate: Optional[Dict] = None) -> str:
        """
        Generate intelligent commit message using AI
        
        Args:
            terraform_code: Dictionary containing terraform files
            cost_estimate: Optional cost estimation data
            
        Returns:
            Generated commit message
        """
        prompt = f"""
Generate a professional git commit message for Terraform infrastructure code.

**Terraform Resources:**
{self._extract_resources_summary(terraform_code)}

**Cost Estimate:**
{self._format_cost_estimate(cost_estimate) if cost_estimate else "Not provided"}

**Requirements:**
1. Use conventional commit format
2. Include brief summary of resources
3. Mention estimated monthly cost if available
4. Keep it concise (max 3 lines)

Example format:
feat(infra): deploy azure app service and sql database
- Added main.tf with 5 resources
- Estimated monthly cost: $250

Generate the commit message now:
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert DevOps engineer. Generate concise, professional git commit messages."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=200,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            # Fallback commit message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return f"chore(infra): update terraform configuration [{timestamp}]"
    
    def push_to_github(self, 
                      github_token: str,
                      repo_owner: str,
                      repo_name: str,
                      terraform_code: Dict[str, str],
                      branch: str = "main",
                      directory: str = "terraform",
                      cost_estimate: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Push Terraform code to GitHub repository
        
        Args:
            github_token: GitHub personal access token
            repo_owner: GitHub username or organization
            repo_name: Repository name
            terraform_code: Dictionary with main.tf, variables.tf, outputs.tf
            branch: Target branch (default: main)
            directory: Directory path in repo (default: terraform)
            cost_estimate: Optional cost estimation data
            
        Returns:
            Dictionary with push result and metadata
        """
        try:
            # Generate AI commit message
            commit_message = self.generate_commit_message(terraform_code, cost_estimate)
            
            # Get current branch SHA
            branch_sha = self._get_branch_sha(github_token, repo_owner, repo_name, branch)
            if not branch_sha:
                return {"success": False, "error": "Failed to get branch SHA"}
            
            # Get current tree
            tree_sha = self._get_tree_sha(github_token, repo_owner, repo_name, branch_sha)
            if not tree_sha:
                return {"success": False, "error": "Failed to get tree SHA"}
            
            # Create blobs for each file
            file_mapping = {
                f"{directory}/main.tf": terraform_code.get("main_tf", ""),
                f"{directory}/variables.tf": terraform_code.get("variables_tf", ""),
                f"{directory}/outputs.tf": terraform_code.get("outputs_tf", "")
            }
            
            # Add cost estimate as comment if available
            if cost_estimate:
                file_mapping[f"{directory}/COST_ESTIMATE.md"] = self._generate_cost_markdown(cost_estimate)
            
            tree_items = []
            for file_path, content in file_mapping.items():
                blob_sha = self._create_blob(github_token, repo_owner, repo_name, content)
                if blob_sha:
                    tree_items.append({
                        "path": file_path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_sha
                    })
            
            if not tree_items:
                return {"success": False, "error": "Failed to create blobs"}
            
            # Create new tree
            new_tree_sha = self._create_tree(github_token, repo_owner, repo_name, tree_sha, tree_items)
            if not new_tree_sha:
                return {"success": False, "error": "Failed to create tree"}
            
            # Create commit
            new_commit_sha = self._create_commit(
                github_token, repo_owner, repo_name, 
                commit_message, new_tree_sha, branch_sha
            )
            if not new_commit_sha:
                return {"success": False, "error": "Failed to create commit"}
            
            # Update branch reference
            update_success = self._update_branch(
                github_token, repo_owner, repo_name, branch, new_commit_sha
            )
            
            if update_success:
                return {
                    "success": True,
                    "commit_sha": new_commit_sha,
                    "commit_message": commit_message,
                    "branch": branch,
                    "files_pushed": list(file_mapping.keys()),
                    "repository_url": f"https://github.com/{repo_owner}/{repo_name}",
                    "commit_url": f"https://github.com/{repo_owner}/{repo_name}/commit/{new_commit_sha}"
                }
            else:
                return {"success": False, "error": "Failed to update branch"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_branch_sha(self, token: str, owner: str, repo: str, branch: str) -> Optional[str]:
        """Get the SHA of the latest commit on the branch"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()["object"]["sha"]
        return None
    
    def _get_tree_sha(self, token: str, owner: str, repo: str, commit_sha: str) -> Optional[str]:
        """Get the tree SHA from a commit"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/commits/{commit_sha}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()["tree"]["sha"]
        return None
    
    def _create_blob(self, token: str, owner: str, repo: str, content: str) -> Optional[str]:
        """Create a blob for file content"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "content": content,
            "encoding": "utf-8"
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()["sha"]
        return None
    
    def _create_tree(self, token: str, owner: str, repo: str, 
                     base_tree: str, tree_items: list) -> Optional[str]:
        """Create a new tree with file changes"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "base_tree": base_tree,
            "tree": tree_items
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()["sha"]
        return None
    
    def _create_commit(self, token: str, owner: str, repo: str, 
                      message: str, tree_sha: str, parent_sha: str) -> Optional[str]:
        """Create a new commit"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/commits"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "message": message,
            "tree": tree_sha,
            "parents": [parent_sha]
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return response.json()["sha"]
        return None
    
    def _update_branch(self, token: str, owner: str, repo: str, 
                      branch: str, commit_sha: str) -> bool:
        """Update branch reference to point to new commit"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "sha": commit_sha,
            "force": False
        }
        
        response = requests.patch(url, headers=headers, json=data)
        return response.status_code == 200
    
    def _extract_resources_summary(self, terraform_code: Dict[str, str]) -> str:
        """Extract resource summary from Terraform code"""
        main_tf = terraform_code.get("main_tf", "")
        
        # Count resource blocks
        resource_count = main_tf.count('resource "')
        
        # Extract resource types
        import re
        resources = re.findall(r'resource "(\w+)"', main_tf)
        
        if resources:
            unique_resources = list(set(resources))
            return f"{resource_count} resources: {', '.join(unique_resources[:5])}"
        return "No resources found"
    
    def _format_cost_estimate(self, cost_estimate: Dict) -> str:
        """Format cost estimate for prompt"""
        if not cost_estimate:
            return "Not available"
        
        total = cost_estimate.get("total_monthly_cost", 0)
        currency = cost_estimate.get("currency", "USD")
        
        return f"{currency} {total:.2f}/month"
    
    def _generate_cost_markdown(self, cost_estimate: Dict) -> str:
        """Generate cost estimate markdown file"""
        total = cost_estimate.get("total_monthly_cost", 0)
        currency = cost_estimate.get("currency", "USD")
        resources = cost_estimate.get("resources", [])
        region = cost_estimate.get("region", "N/A")
        estimate_date = cost_estimate.get("estimate_date", datetime.now().isoformat())
        disclaimer = cost_estimate.get("disclaimer", "Estimates are approximate.")
        
        md_content = f"""# Azure Cost Estimation Report

**Generated:** {estimate_date}  
**Region:** {region}  
**Currency:** {currency}

## 💰 Cost Summary

| Metric | Amount |
|--------|--------|
| **Monthly Cost** | ${total:.2f} |
| **Annual Cost** | ${total * 12:.2f} |
| **Number of Resources** | {len(resources)} |

## 📊 Resource Breakdown

"""
        
        # Sort resources by cost (highest first)
        sorted_resources = sorted(resources, key=lambda x: x.get("estimated_monthly_cost", 0), reverse=True)
        
        for resource in sorted_resources:
            name = resource.get("resource_name", "Unknown")
            cost = resource.get("estimated_monthly_cost", 0)
            resource_type = resource.get("resource_type", "Unknown")
            tier = resource.get("pricing_tier", "Standard")
            assumptions = resource.get("assumptions", "Standard configuration")
            percentage = (cost / total * 100) if total > 0 else 0
            
            md_content += f"""### {name}

- **Type:** {resource_type}
- **Pricing Tier:** {tier}
- **Monthly Cost:** ${cost:.2f} ({percentage:.1f}% of total)
- **Annual Cost:** ${cost * 12:.2f}
- **Assumptions:** {assumptions}

"""
        
        # Add cost optimization tips for high-cost resources
        high_cost_resources = [r for r in resources if r.get("estimated_monthly_cost", 0) > 100]
        
        if high_cost_resources:
            md_content += f"""## 💡 Cost Optimization Opportunities

⚠️ **{len(high_cost_resources)} resource(s) identified with monthly cost > $100**

Consider these optimization strategies:

1. **Right-size resources** - Review SKU/tier selections for over-provisioned resources
2. **Reserved Instances** - Save up to 72% with 1-3 year commitments for predictable workloads
3. **Auto-shutdown** - Implement auto-shutdown for non-production VMs during off-hours
4. **Auto-scaling** - Configure auto-scaling to scale down during low-traffic periods
5. **Azure Hybrid Benefit** - Use existing licenses to reduce costs
6. **Storage optimization** - Review storage tiers and delete unused data
7. **Network optimization** - Optimize data transfer patterns to reduce egress costs

"""
        
        md_content += f"""---

## ⚠️ Disclaimer

{disclaimer}

**Important Notes:**
- Costs are estimated based on standard pricing and typical usage patterns
- Actual costs may vary based on:
  - Actual usage and consumption patterns
  - Data transfer volumes
  - Storage amounts and types
  - Compute hours and intensity
  - Regional pricing variations
  - Azure pricing changes
  - Additional features and configurations

**Recommendations:**
- Use [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) for detailed quotes
- Set up [Azure Cost Management](https://azure.microsoft.com/services/cost-management/) alerts
- Review [Azure Cost Optimization Guide](https://docs.microsoft.com/azure/cost-management-billing/)
- Monitor actual costs after deployment and adjust as needed
"""
        
        return md_content